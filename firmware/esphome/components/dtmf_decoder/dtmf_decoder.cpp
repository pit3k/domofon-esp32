#include "dtmf_decoder.h"
#include "esphome/core/log.h"
#include "esphome/core/hal.h"

#include <cmath>
#include <soc/soc_caps.h>

namespace esphome {
namespace dtmf_decoder {

static const char *const TAG = "dtmf_decoder";

// 4 czestotliwosci "wierszy" (grupa niska) i 4 "kolumn" (grupa wysoka)
static const float DTMF_FREQS[8] = {697.0f, 770.0f, 852.0f, 941.0f, 1209.0f, 1336.0f, 1477.0f, 1633.0f};
static const char DTMF_KEYS[4][4] = {
    {'1', '2', '3', 'A'},
    {'4', '5', '6', 'B'},
    {'7', '8', '9', 'C'},
    {'*', '0', '#', 'D'},
};

static constexpr size_t READ_BUF_BYTES = 1024;  // 256 probek x 4 B (format TYPE2)
static uint8_t s_read_buf[READ_BUF_BYTES];

void DTMFDecoder::setup() {
  for (int i = 0; i < 8; i++) {
    this->coeff_[i] = 2.0f * cosf(2.0f * static_cast<float>(M_PI) * DTMF_FREQS[i] / static_cast<float>(this->sample_rate_));
    this->s1_[i] = this->s2_[i] = 0.0f;
  }

  adc_continuous_handle_cfg_t hcfg = {};
  hcfg.max_store_buf_size = 8192;  // ~256 ms bufora przy 8 kHz (zapas na blokady petli/WiFi)
  hcfg.conv_frame_size = READ_BUF_BYTES;
  esp_err_t err = adc_continuous_new_handle(&hcfg, &this->handle_);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "adc_continuous_new_handle failed: %s", esp_err_to_name(err));
    this->mark_failed();
    return;
  }

  adc_digi_pattern_config_t pattern = {};
  pattern.atten = ADC_ATTEN_DB_12;  // zakres ok. 0..2,5 V na ESP32-C3
  pattern.channel = this->channel_;  // ESP32-C3: GPIOn == ADC1_CHn (n = 0..4)
  pattern.unit = ADC_UNIT_1;         // tylko ADC1 (ADC2 koliduje z WiFi)
  pattern.bit_width = SOC_ADC_DIGI_MAX_BITWIDTH;

  adc_continuous_config_t cfg = {};
  cfg.pattern_num = 1;
  cfg.adc_pattern = &pattern;
  cfg.sample_freq_hz = this->sample_rate_;
  cfg.conv_mode = ADC_CONV_SINGLE_UNIT_1;
  cfg.format = ADC_DIGI_OUTPUT_FORMAT_TYPE2;
  err = adc_continuous_config(this->handle_, &cfg);
  if (err != ESP_OK) {
    ESP_LOGE(TAG, "adc_continuous_config failed: %s", esp_err_to_name(err));
    this->mark_failed();
    return;
  }
  if (this->enabled_)
    this->set_enabled(true);
}

void DTMFDecoder::set_enabled(bool en) {
  this->enabled_ = en;
  if (this->handle_ == nullptr)
    return;  // przed setup() - zostanie zastosowane w setup()
  if (en && !this->running_) {
    // reset stanu
    for (int i = 0; i < 8; i++)
      this->s1_[i] = this->s2_[i] = 0.0f;
    this->n_ = 0;
    this->sum_ = this->sum_sq_ = 0;
    this->have_dc_ = false;
    this->candidate_ = this->current_ = 0;
    this->candidate_count_ = this->off_count_ = 0;
    this->stat_samples_ = 0;
    this->stat_start_ms_ = millis();
    this->stat_dropped_ = 0;
    this->stat_abs_ = 0;
    this->raw_logged_ = false;
    this->channel_warned_ = false;
    this->read_warned_ = false;
    this->stats_logged_ = false;
    this->reject_logs_ = 0;
    esp_err_t err = adc_continuous_start(this->handle_);
    if (err != ESP_OK) {
      ESP_LOGE(TAG, "adc_continuous_start failed: %s", esp_err_to_name(err));
      return;
    }
    this->running_ = true;
    ESP_LOGD(TAG, "Dekodowanie DTMF wlaczone");
  } else if (!en && this->running_) {
    adc_continuous_stop(this->handle_);
    this->running_ = false;
    ESP_LOGD(TAG, "Dekodowanie DTMF wylaczone");
  }
}

void DTMFDecoder::clear_sequence() {
  this->sequence_.clear();
#ifdef USE_TEXT_SENSOR
  if (this->sequence_sensor_ != nullptr)
    this->sequence_sensor_->publish_state("");
#endif
}

void DTMFDecoder::loop() {
  const uint32_t now = millis();
  if (!this->sequence_.empty() && this->sequence_timeout_ms_ > 0 &&
      now - this->last_digit_ms_ > this->sequence_timeout_ms_) {
    ESP_LOGI(TAG, "Sekwencja zakonczona: %s", this->sequence_.c_str());
    this->sequence_.clear();  // stan sensora zostaje (ostatnia pelna sekwencja)
  }

  if (!this->running_)
    return;

  // Odczyt wszystkiego, co DMA zebralo od ostatniego wywolania (nieblokujaco).
  for (int guard = 0; guard < 16; guard++) {
    uint32_t len = 0;
    esp_err_t err = adc_continuous_read(this->handle_, s_read_buf, READ_BUF_BYTES, &len, 0);
    if (err != ESP_OK || len == 0) {
      if (err != ESP_OK && err != ESP_ERR_TIMEOUT && !this->read_warned_) {
        this->read_warned_ = true;
        ESP_LOGW(TAG, "adc_continuous_read: %s", esp_err_to_name(err));
      }
      break;
    }
    for (uint32_t i = 0; i + SOC_ADC_DIGI_RESULT_BYTES <= len; i += SOC_ADC_DIGI_RESULT_BYTES) {
      const adc_digi_output_data_t *p = reinterpret_cast<const adc_digi_output_data_t *>(&s_read_buf[i]);
      if (!this->raw_logged_) {
        this->raw_logged_ = true;
        ESP_LOGI(TAG, "ADC slowo 0x%08x data=%u ch=%u unit=%u (oczekiwany kanal %u)", p->val, p->type2.data,
                 p->type2.channel, p->type2.unit, this->channel_);
      }
      // Jeden kanal w tabeli. Na ESP32-C3 tag kanalu w DMA bywa 0, wiec odrzucanie
      // po numerze kanalu gubi wszystkie probki i dekoder milczy.
      if (p->type2.unit != 0) {
        this->stat_dropped_++;
        continue;
      }
      if (p->type2.channel != this->channel_ && !this->channel_warned_) {
        this->channel_warned_ = true;
        ESP_LOGW(TAG, "tag kanalu %u zamiast %u — probka idzie do Goertzela", p->type2.channel, this->channel_);
      }
      this->process_sample_(static_cast<float>(p->type2.data));
    }
  }

  if (!this->stats_logged_ && now - this->stat_start_ms_ >= 2000) {
    this->stats_logged_ = true;
    if (this->stat_samples_ == 0) {
      ESP_LOGW(TAG, "ADC: brak probek przez 2 s (odrzucone slowa: %u)", this->stat_dropped_);
    } else {
      const float rate = this->stat_samples_ * 1000.0f / static_cast<float>(now - this->stat_start_ms_);
      ESP_LOGI(TAG, "ADC: %.0f Hz, |x|~%.1f LSB, odrzucone slowa: %u", rate,
               this->stat_abs_ / static_cast<float>(this->stat_samples_), this->stat_dropped_);
    }
  }

  if (now - this->stat_start_ms_ >= 10000) {
    this->measured_rate_ = this->stat_samples_ * 1000.0f / static_cast<float>(now - this->stat_start_ms_);
    if (this->debug_)
      ESP_LOGD(TAG, "Rzeczywista czestotliwosc probkowania: %.0f Hz", this->measured_rate_);
    this->stat_samples_ = 0;
    this->stat_start_ms_ = now;
  }
}

void DTMFDecoder::process_sample_(float raw) {
  this->stat_samples_++;
  this->stat_abs_ += fabsf(raw - (this->have_dc_ ? this->dc_ : raw));
  if (!this->have_dc_) {
    this->dc_ = raw;
    this->have_dc_ = true;
  }
  // usuniecie skladowej stalej (polaryzacja ~1,65 V) - srednia z poprzedniego bloku
  const float x = raw - this->dc_;
  this->sum_ += x;
  this->sum_sq_ += x * x;
  for (int i = 0; i < 8; i++) {
    const float s0 = x + this->coeff_[i] * this->s1_[i] - this->s2_[i];
    this->s2_[i] = this->s1_[i];
    this->s1_[i] = s0;
  }
  if (++this->n_ >= this->block_size_)
    this->evaluate_block_();
}

void DTMFDecoder::evaluate_block_() {
  const float n = static_cast<float>(this->n_);
  float power[8];
  for (int i = 0; i < 8; i++) {
    // |X(k)|^2 ; energia tonu w bloku = 2*P/N (dla sinusa o amplitudzie A: A^2*N/2)
    float p = this->s1_[i] * this->s1_[i] + this->s2_[i] * this->s2_[i] - this->coeff_[i] * this->s1_[i] * this->s2_[i];
    power[i] = p < 0 ? 0 : 2.0f * p / n;
    this->s1_[i] = this->s2_[i] = 0.0f;
  }
  const float mean = this->sum_ / n;
  const float energy = this->sum_sq_ - this->sum_ * this->sum_ / n;  // energia bez DC
  this->dc_ += mean;  // aktualizacja estymaty DC
  this->sum_ = this->sum_sq_ = 0;
  this->n_ = 0;

  int r = 0, c = 4;
  for (int i = 1; i < 4; i++)
    if (power[i] > power[r])
      r = i;
  for (int i = 5; i < 8; i++)
    if (power[i] > power[c])
      c = i;

  // amplituda (w jednostkach ADC) = sqrt(2 * energia / N)
  const float amp_r = sqrtf(2.0f * power[r] / n);
  const float amp_c = sqrtf(2.0f * power[c] / n);

  char digit = 0;
  const char *reason = nullptr;
  do {
    if (amp_r < this->min_amplitude_ || amp_c < this->min_amplitude_) {
      reason = "za slaby";
      break;
    }
    const float twist_db = 10.0f * log10f(power[c] / power[r]);
    if (fabsf(twist_db) > this->max_twist_db_) {
      reason = "twist";
      break;
    }
    const float grp = powf(10.0f, this->min_group_ratio_db_ / 10.0f);
    bool ok = true;
    for (int i = 0; i < 4; i++)
      if (i != r && power[i] * grp > power[r])
        ok = false;
    for (int i = 4; i < 8; i++)
      if (i != c && power[i] * grp > power[c])
        ok = false;
    if (!ok) {
      reason = "sasiednie tony";
      break;
    }
    if (energy <= 0 || (power[r] + power[c]) < this->min_tone_energy_ratio_ * energy) {
      reason = "szum/mowa";
      break;
    }
    digit = DTMF_KEYS[r][c - 4];
  } while (false);

  if (this->debug_ && amp_r >= this->min_amplitude_ * 0.5f && amp_c >= this->min_amplitude_ * 0.5f) {
    ESP_LOGD(TAG, "blok: %.0fHz A=%.0f, %.0fHz A=%.0f, ton/calosc=%.2f -> %c %s", DTMF_FREQS[r], amp_r,
             DTMF_FREQS[c], amp_c, energy > 0 ? (power[r] + power[c]) / energy : 0.0f, digit ? digit : '-',
             reason ? reason : "");
  } else if (digit == 0 && reason != nullptr && amp_r >= this->min_amplitude_ && amp_c >= this->min_amplitude_ &&
             this->reject_logs_ < 4) {
    this->reject_logs_++;
    ESP_LOGI(TAG, "odrzut (%s): %.0fHz A=%.0f, %.0fHz A=%.0f", reason, DTMF_FREQS[r], amp_r, DTMF_FREQS[c], amp_c);
  }
  this->handle_detection_(digit);
}

void DTMFDecoder::handle_detection_(char digit) {
  if (digit != 0) {
    this->off_count_ = 0;
    if (digit == this->candidate_) {
      if (this->candidate_count_ < 255)
        this->candidate_count_++;
    } else {
      this->candidate_ = digit;
      this->candidate_count_ = 1;
    }
    if (this->candidate_count_ >= this->min_on_blocks_ && this->current_ != digit) {
      this->current_ = digit;
      const std::string d(1, digit);
      this->last_digit_ms_ = millis();
      this->sequence_ += digit;
      ESP_LOGI(TAG, "Wykryto DTMF: %c (sekwencja: %s)", digit, this->sequence_.c_str());
#ifdef USE_TEXT_SENSOR
      if (this->digit_sensor_ != nullptr)
        this->digit_sensor_->publish_state(d);
      if (this->sequence_sensor_ != nullptr)
        this->sequence_sensor_->publish_state(this->sequence_);
#endif
      this->digit_callback_.call(d);
    }
  } else {
    this->candidate_ = 0;
    this->candidate_count_ = 0;
    if (this->current_ != 0 && ++this->off_count_ >= this->min_off_blocks_) {
      this->current_ = 0;  // ton puszczony - ta sama cyfra moze zostac wykryta ponownie
      this->off_count_ = 0;
    }
  }
}

void DTMFDecoder::dump_config() {
  ESP_LOGCONFIG(TAG, "DTMF decoder (Goertzel, ADC1 continuous):");
  ESP_LOGCONFIG(TAG, "  ADC1 kanal: %u (GPIO%u), tlumienie 12 dB", this->channel_, this->channel_);
  ESP_LOGCONFIG(TAG, "  Probkowanie: %u Hz, blok: %u probek (%.1f ms)", (unsigned) this->sample_rate_,
                this->block_size_, this->block_size_ * 1000.0f / this->sample_rate_);
  ESP_LOGCONFIG(TAG, "  Min. amplituda: %.0f LSB, max twist: %.1f dB, odstep w grupie: %.1f dB, ton/calosc: %.2f",
                this->min_amplitude_, this->max_twist_db_, this->min_group_ratio_db_, this->min_tone_energy_ratio_);
  ESP_LOGCONFIG(TAG, "  Debounce: %u blokow wl. / %u blokow wyl.", this->min_on_blocks_, this->min_off_blocks_);
  if (this->is_failed())
    ESP_LOGE(TAG, "  Inicjalizacja ADC nie powiodla sie!");
}

}  // namespace dtmf_decoder
}  // namespace esphome
