#pragma once

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/core/helpers.h"

#include <string>
#include <vector>

namespace esphome {
namespace dtmf_tone {

class DtmfTone : public Component {
 public:
  void set_pin_low(uint8_t pin) { this->pin_low_ = pin; }
  void set_pin_high(int pin) {
    this->pin_high_ = pin;
    this->dual_ = pin >= 0;
  }
  void set_carrier_frequency(uint32_t hz) { this->carrier_hz_ = hz; }
  void set_sample_rate(uint32_t hz) { this->sample_rate_ = hz; }
  void set_amplitude_pct(uint8_t pct) { this->amplitude_pct_ = pct; }
  void set_voice_pct(uint16_t pct) { this->voice_pct_ = pct; }
  void set_high_pct(uint8_t pct) { this->high_pct_ = pct; }

  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::HARDWARE; }

  // tone_ms: dlugosc jednego symbolu, gap_ms: cisza miedzy symbolami.
  // Sekwencja: 0-9 * # A-D. Spacja jest ignorowana. Przecinek = pauza o dlugosci tonu.
  void play(const std::string &sequence, uint32_t tone_ms, uint32_t gap_ms);
  void stop();

  // Glos: 8-bit unsigned PCM (128 = cisza) o czestotliwosci rate_hz, wbudowany przy kompilacji.
  void add_wav(const std::string &name, const uint8_t *data, uint32_t len, uint32_t rate_hz);
  // preroll_ms: szum przed glosem (patrz on_sample).
  bool play_wav(const std::string &name, bool loop = false, uint32_t preroll_ms = 500);
  // Bias: w bezczynnosci wyjscie trzyma srodek skali (128) zamiast 0 - bez skoku DC przy starcie.
  void set_bias(bool enable);
  bool is_playing() const { return this->state_ != ST_IDLE; }
  void IRAM_ATTR on_sample();

 protected:
  void IRAM_ATTR write_pair(int duty_low, int duty_high);
  void IRAM_ATTR write_idle() {
    const int level = this->bias_ ? 128 : 0;
    this->write_pair(level, level);
  }
  bool IRAM_ATTR select_symbol(uint8_t pos);
  int IRAM_ATTR next_symbol(uint8_t from) const;

  uint8_t pin_low_{5};
  int pin_high_{-1};
  bool dual_{false};
  uint32_t carrier_hz_{200000};
  uint32_t sample_rate_{32000};
  uint32_t actual_rate_{32000};
  uint8_t amplitude_pct_{100};
  uint16_t voice_pct_{200};
  uint8_t high_pct_{80};

  struct Wav {
    std::string name;
    const uint8_t *data;
    uint32_t len;
    uint32_t rate;
  };
  std::vector<Wav> wavs_;
  const uint8_t *wav_data_{nullptr};
  uint32_t wav_len_{0};
  uint64_t wav_acc_{0};
  uint32_t wav_step_{0};
  volatile bool wav_loop_{false};
  volatile bool bias_{false};
  volatile uint32_t preroll_left_{0};
  uint32_t noise_state_{2463534242u};

  enum : uint8_t { ST_IDLE = 0, ST_TONE = 1, ST_GAP = 2, ST_WAV = 3 };
  volatile uint8_t state_{ST_IDLE};
  volatile bool timer_running_{false};

  char seq_[65]{};
  uint8_t seq_len_{0};
  uint8_t seq_pos_{0};
  uint16_t freq_lo_{0};
  uint16_t freq_hi_{0};
  uint32_t step_lo_{0};
  uint32_t step_hi_{0};
  uint32_t phase_lo_{0};
  uint32_t phase_hi_{0};
  uint32_t sample_pos_{0};
  uint32_t limit_{0};
  uint32_t tone_samples_{1};
  uint32_t gap_samples_{0};
  uint32_t ramp_samples_{0};

  void *timer_{nullptr};
  bool ledc_ready_{false};
};

template<typename... Ts> class PlayAction : public Action<Ts...>, public Parented<DtmfTone> {
 public:
  TEMPLATABLE_VALUE(std::string, sequence)
  TEMPLATABLE_VALUE(uint32_t, tone_length)
  TEMPLATABLE_VALUE(uint32_t, inter_digit_gap)

  void play(const Ts &...x) override {
    this->parent_->play(this->sequence_.value(x...), this->tone_length_.value(x...), this->inter_digit_gap_.value(x...));
  }
};

template<typename... Ts> class PlayWavAction : public Action<Ts...>, public Parented<DtmfTone> {
 public:
  TEMPLATABLE_VALUE(std::string, name)
  TEMPLATABLE_VALUE(bool, loop)
  TEMPLATABLE_VALUE(uint32_t, preroll_ms)

  void play(const Ts &...x) override {
    this->parent_->play_wav(this->name_.value(x...), this->loop_.value(x...), this->preroll_ms_.value(x...));
  }
};

template<typename... Ts> class BiasAction : public Action<Ts...>, public Parented<DtmfTone> {
 public:
  TEMPLATABLE_VALUE(bool, enable)

  void play(const Ts &...x) override { this->parent_->set_bias(this->enable_.value(x...)); }
};

template<typename... Ts> class StopAction : public Action<Ts...>, public Parented<DtmfTone> {
 public:
  void play(const Ts &...x) override { this->parent_->stop(); }
};

}  // namespace dtmf_tone
}  // namespace esphome
