#pragma once

#include "esphome/core/component.h"
#include "esphome/core/automation.h"
#include "esphome/core/defines.h"
#ifdef USE_TEXT_SENSOR
#include "esphome/components/text_sensor/text_sensor.h"
#endif

#include <esp_adc/adc_continuous.h>
#include <string>

namespace esphome {
namespace dtmf_decoder {

// Programowy dekoder DTMF: ADC1 w trybie ciaglym (DMA) + algorytm Goertzela.
class DTMFDecoder : public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void set_channel(uint8_t ch) { this->channel_ = ch; }
  void set_sample_rate(uint32_t sr) { this->sample_rate_ = sr; }
  void set_block_size(uint16_t n) { this->block_size_ = n; }
  void set_min_amplitude(float a) { this->min_amplitude_ = a; }
  void set_max_twist_db(float db) { this->max_twist_db_ = db; }
  void set_min_group_ratio_db(float db) { this->min_group_ratio_db_ = db; }
  void set_min_tone_energy_ratio(float r) { this->min_tone_energy_ratio_ = r; }
  void set_min_on_blocks(uint8_t n) { this->min_on_blocks_ = n; }
  void set_min_off_blocks(uint8_t n) { this->min_off_blocks_ = n; }
  void set_sequence_timeout(uint32_t ms) { this->sequence_timeout_ms_ = ms; }
  void set_debug(bool d) { this->debug_ = d; }
#ifdef USE_TEXT_SENSOR
  void set_digit_text_sensor(text_sensor::TextSensor *s) { this->digit_sensor_ = s; }
  void set_sequence_text_sensor(text_sensor::TextSensor *s) { this->sequence_sensor_ = s; }
#endif

  // Wlaczanie/wylaczanie dekodowania (np. tylko gdy off-hook wlaczony lub
  // wyciszenie podczas wlasnego nadawania DTMF).
  void set_enabled(bool en);
  bool is_enabled() const { return this->enabled_; }
  void clear_sequence();

  void add_on_digit_callback(std::function<void(const std::string &)> &&cb) { this->digit_callback_.add(std::move(cb)); }

 protected:
  void process_sample_(float x);
  void evaluate_block_();
  void handle_detection_(char digit);

  adc_continuous_handle_t handle_{nullptr};
  uint8_t channel_{1};
  uint32_t sample_rate_{8000};
  uint16_t block_size_{205};
  float min_amplitude_{25.0f};
  float max_twist_db_{8.0f};
  float min_group_ratio_db_{6.0f};
  float min_tone_energy_ratio_{0.4f};
  uint8_t min_on_blocks_{2};
  uint8_t min_off_blocks_{2};
  uint32_t sequence_timeout_ms_{3000};
  bool debug_{false};
  bool enabled_{true};
  bool running_{false};

  // Goertzel
  float coeff_[8];
  float s1_[8];
  float s2_[8];
  float sum_{0}, sum_sq_{0};
  float dc_{0};
  bool have_dc_{false};
  uint16_t n_{0};

  // Debounce
  char candidate_{0};
  uint8_t candidate_count_{0};
  char current_{0};
  uint8_t off_count_{0};

  std::string sequence_;
  uint32_t last_digit_ms_{0};

  // Statystyki (rzeczywista czestotliwosc probkowania)
  uint32_t stat_samples_{0};
  uint32_t stat_start_ms_{0};
  float measured_rate_{0};

#ifdef USE_TEXT_SENSOR
  text_sensor::TextSensor *digit_sensor_{nullptr};
  text_sensor::TextSensor *sequence_sensor_{nullptr};
#endif
  CallbackManager<void(const std::string &)> digit_callback_;
};

class DigitTrigger : public Trigger<std::string> {
 public:
  explicit DigitTrigger(DTMFDecoder *parent) {
    parent->add_on_digit_callback([this](const std::string &d) { this->trigger(d); });
  }
};

template<typename... Ts> class EnableAction : public Action<Ts...>, public Parented<DTMFDecoder> {
 public:
  void play(const Ts &...x) override { this->parent_->set_enabled(true); }
};
template<typename... Ts> class DisableAction : public Action<Ts...>, public Parented<DTMFDecoder> {
 public:
  void play(const Ts &...x) override { this->parent_->set_enabled(false); }
};
template<typename... Ts> class ClearSequenceAction : public Action<Ts...>, public Parented<DTMFDecoder> {
 public:
  void play(const Ts &...x) override { this->parent_->clear_sequence(); }
};

}  // namespace dtmf_decoder
}  // namespace esphome
