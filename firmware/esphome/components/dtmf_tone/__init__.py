import hashlib
import inspect
import io
import json
import math
import struct
import urllib.error
import urllib.parse
import urllib.request
import wave

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import automation
from esphome.const import CONF_FILE, CONF_ID, CONF_NAME
from esphome.core import CORE

CODEOWNERS = ["@pit3k"]
MULTI_CONF = True

ns = cg.esphome_ns.namespace("dtmf_tone")
DtmfTone = ns.class_("DtmfTone", cg.Component)
PlayWavAction = ns.class_("PlayWavAction", automation.Action)
PlayAction = ns.class_("PlayAction", automation.Action)
StopAction = ns.class_("StopAction", automation.Action)
BiasAction = ns.class_("BiasAction", automation.Action)
CONF_PREROLL = "preroll_ms"
CONF_ENABLE = "enable"

CONF_PIN_LOW = "pin_low"
CONF_PIN_HIGH = "pin_high"
CONF_CARRIER = "carrier_frequency"
CONF_SAMPLE_RATE = "sample_rate"
CONF_AMPLITUDE = "amplitude"
CONF_HIGH = "high_tone_level"
CONF_SEQUENCE = "sequence"
CONF_TONE_LENGTH = "tone_length"
CONF_GAP = "inter_digit_gap"
CONF_LOOP = "loop"
CONF_TTS = "tts"
CONF_TONE = "tone"
CONF_TEXT = "text"
CONF_ENGINE = "engine"
CONF_LANGUAGE = "language"
CONF_VOICE = "voice"
CONF_FREQUENCY = "frequency"
CONF_ON_TIME = "on_time"
CONF_OFF_TIME = "off_time"
CONF_HOME_ASSISTANT = "home_assistant"
CONF_HA_URL = "url"
CONF_HA_TOKEN = "token"
CONF_WAVS = "wavs"
CONF_WAV_SAMPLE_RATE = "wav_sample_rate"
CONF_RAW_DATA_ID = "raw_data_id"


def load_wav(path, target_rate):
    return convert_wav(io.BytesIO(open(path, "rb").read()), target_rate, str(path))


def convert_wav(fileobj, target_rate, label):
    """Zwraca bajty 8-bit unsigned mono @ target_rate (usrednianie przy decymacji)."""
    path = label
    try:
        with wave.open(fileobj, "rb") as w:
            channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(frames)
    except (wave.Error, EOFError) as err:
        raise cv.Invalid(f"Nieprawidlowy WAV {path}: {err}")
    if width not in (1, 2):
        raise cv.Invalid(f"{path}: wymagany PCM 8 lub 16 bit (jest {8 * width} bit)")
    if width == 2:
        samples = struct.unpack("<%dh" % (len(raw) // 2), raw)
    else:
        samples = [(b - 128) << 8 for b in raw]
    mono = [sum(samples[i : i + channels]) / channels for i in range(0, len(samples) - channels + 1, channels)]
    if not mono:
        raise cv.Invalid(f"{path}: pusty plik")
    out_len = max(1, int(len(mono) * target_rate / rate))
    ratio = rate / target_rate
    out = []
    for i in range(out_len):
        a = int(i * ratio)
        b = max(a + 1, min(len(mono), int((i + 1) * ratio)))
        out.append(sum(mono[a:b]) / (b - a))
    peak = max(max(abs(v) for v in out), 1)
    # Normalizacja do pelnej skali, zeby nagrania mialy podobna glosnosc.
    return [max(0, min(255, int(round(128 + v / peak * 127)))) for v in out]


def validate_wav_file(value):
    value = cv.string(value)
    path = CORE.relative_config_path(value)
    if not path.is_file():
        raise cv.Invalid(f"WAV file not found: {path}")
    return value


def synth_tone(frequency, on_s, off_s, rate):
    """Beep (sine with 20 ms fades) followed by silence; loops seamlessly."""
    n_on = int(on_s * rate)
    fade = max(1, rate // 50)
    out = []
    for i in range(n_on):
        env = min(1.0, i / fade, (n_on - 1 - i) / fade)
        out.append(int(round(128 + 127 * env * math.sin(2 * math.pi * frequency * i / rate))))
    return out + [128] * int(off_s * rate)


def ha_request(cfg, path, body=None):
    url = cfg[CONF_HA_URL].rstrip("/") + path
    headers = {"Authorization": "Bearer " + cfg[CONF_HA_TOKEN], "Content-Type": "application/json"}
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data, headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def tts_wav(ha, tts, rate):
    """Render text via Home Assistant TTS at compile time; cached so offline rebuilds still work."""
    key = json.dumps([tts, rate], sort_keys=True)
    cache = CORE.relative_build_path("dtmf_tone_tts")
    cache.mkdir(parents=True, exist_ok=True)
    cached = cache / (hashlib.sha1(key.encode()).hexdigest() + ".wav")
    try:
        options = {
            "preferred_format": "wav",
            "preferred_sample_rate": 16000,
            "preferred_sample_channels": 1,
            "preferred_sample_bytes": 2,
        }
        if tts.get(CONF_VOICE):
            options["voice"] = tts[CONF_VOICE]
        reply = ha_request(
            ha,
            "/api/tts_get_url",
            {
                "engine_id": tts[CONF_ENGINE],
                "message": tts[CONF_TEXT],
                "language": tts[CONF_LANGUAGE],
                "options": options,
            },
        )
        # HA returns its own external base URL, which may not be reachable from here.
        audio_path = urllib.parse.urlparse(json.loads(reply)["url"]).path
        data = ha_request(ha, audio_path)
        cached.write_bytes(data)
    except (urllib.error.URLError, OSError, KeyError, ValueError) as err:
        if not cached.is_file():
            raise cv.Invalid(f"TTS request to Home Assistant failed and no cached copy exists: {err}")
        data = cached.read_bytes()
    return convert_wav(io.BytesIO(data), rate, f"TTS '{tts[CONF_TEXT]}'")


TTS_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_TEXT): cv.string,
        cv.Optional(CONF_ENGINE, default="tts.piper"): cv.string,
        cv.Optional(CONF_LANGUAGE, default="pl_PL"): cv.string,
        cv.Optional(CONF_VOICE): cv.string,
    }
)

TONE_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_FREQUENCY, default=425): cv.int_range(min=50, max=3500),
        cv.Optional(CONF_ON_TIME, default="1s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_OFF_TIME, default="4s"): cv.positive_time_period_milliseconds,
    }
)

HA_SCHEMA = cv.Schema(
    {
        cv.Required(CONF_HA_URL): cv.string,
        cv.Required(CONF_HA_TOKEN): cv.string,
    }
)

WAV_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.Required(CONF_NAME): cv.string_strict,
            cv.Optional(CONF_FILE): validate_wav_file,
            cv.Optional(CONF_TTS): TTS_SCHEMA,
            cv.Optional(CONF_TONE): TONE_SCHEMA,
            cv.GenerateID(CONF_RAW_DATA_ID): cv.declare_id(cg.uint8),
        }
    ),
    cv.has_exactly_one_key(CONF_FILE, CONF_TTS, CONF_TONE),
)

def gpio_num(value):
    if isinstance(value, str):
        text = value.strip().upper()
        if text.startswith("GPIO"):
            value = text[4:]
    return cv.int_range(min=0, max=21)(value)


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(DtmfTone),
        cv.Required(CONF_PIN_LOW): gpio_num,
        cv.Optional(CONF_PIN_HIGH): gpio_num,
        cv.Optional(CONF_CARRIER, default=200000): cv.int_range(min=20000, max=300000),
        cv.Optional(CONF_SAMPLE_RATE, default=32000): cv.int_range(min=8000, max=48000),
        cv.Optional(CONF_AMPLITUDE, default="100%"): cv.percentage,
        cv.Optional(CONF_HIGH, default="80%"): cv.percentage,
        cv.Optional(CONF_WAV_SAMPLE_RATE, default=8000): cv.int_range(min=4000, max=16000),
        cv.Optional(CONF_HOME_ASSISTANT): HA_SCHEMA,
        cv.Optional(CONF_WAVS, default=[]): cv.ensure_list(WAV_SCHEMA),
    }
).extend(cv.COMPONENT_SCHEMA)


def _final_validate(config):
    for wav in config[CONF_WAVS]:
        if CONF_TTS in wav and CONF_HOME_ASSISTANT not in config:
            raise cv.Invalid(f"wav '{wav[CONF_NAME]}' uses tts: which requires home_assistant: {{url, token}}")
    return config


CONFIG_SCHEMA = cv.All(CONFIG_SCHEMA, _final_validate)


async def to_code(config):
    # ESPHome excludes unused IDF drivers. driver/gptimer.h and driver/ledc.h
    # live in these components and are not linked unless requested.
    try:
        from esphome.components.esp32 import include_builtin_idf_component
    except ImportError:
        include_builtin_idf_component = None
    if include_builtin_idf_component is not None:
        include_builtin_idf_component("esp_driver_gptimer")
        include_builtin_idf_component("esp_driver_ledc")

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_pin_low(config[CONF_PIN_LOW]))
    if CONF_PIN_HIGH in config:
        cg.add(var.set_pin_high(config[CONF_PIN_HIGH]))
    else:
        cg.add(var.set_pin_high(-1))
    cg.add(var.set_carrier_frequency(config[CONF_CARRIER]))
    cg.add(var.set_sample_rate(config[CONF_SAMPLE_RATE]))
    cg.add(var.set_amplitude_pct(int(round(config[CONF_AMPLITUDE] * 100))))
    cg.add(var.set_high_pct(int(round(config[CONF_HIGH] * 100))))
    rate = config[CONF_WAV_SAMPLE_RATE]
    for wav in config[CONF_WAVS]:
        if CONF_FILE in wav:
            data = load_wav(CORE.relative_config_path(wav[CONF_FILE]), rate)
        elif CONF_TTS in wav:
            data = tts_wav(config[CONF_HOME_ASSISTANT], wav[CONF_TTS], rate)
        else:
            tone = wav[CONF_TONE]
            data = synth_tone(
                tone[CONF_FREQUENCY], tone[CONF_ON_TIME].total_seconds, tone[CONF_OFF_TIME].total_seconds, rate
            )
        arr = cg.progmem_array(wav[CONF_RAW_DATA_ID], data)
        cg.add(var.add_wav(wav[CONF_NAME], arr, len(data), rate))


PLAY_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.use_id(DtmfTone),
        cv.Required(CONF_SEQUENCE): cv.templatable(cv.string),
        cv.Optional(CONF_TONE_LENGTH, default="200ms"): cv.templatable(
            cv.positive_time_period_milliseconds
        ),
        cv.Optional(CONF_GAP, default="80ms"): cv.templatable(cv.positive_time_period_milliseconds),
    }
)

PLAY_WAV_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.use_id(DtmfTone),
        cv.Required(CONF_NAME): cv.templatable(cv.string),
        cv.Optional(CONF_LOOP, default=False): cv.templatable(cv.boolean),
        cv.Optional(CONF_PREROLL, default="500ms"): cv.templatable(cv.positive_time_period_milliseconds),
    }
)

BIAS_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.use_id(DtmfTone),
        cv.Required(CONF_ENABLE): cv.templatable(cv.boolean),
    }
)

STOP_SCHEMA = automation.maybe_simple_id(
    {
        cv.GenerateID(): cv.use_id(DtmfTone),
    }
)


def _register_action(name, action_type, schema):
    kwargs = {}
    if "synchronous" in inspect.signature(automation.register_action).parameters:
        kwargs["synchronous"] = True
    return automation.register_action(name, action_type, schema, **kwargs)


@_register_action("dtmf_tone.play", PlayAction, PLAY_SCHEMA)
async def play_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_sequence(await cg.templatable(config[CONF_SEQUENCE], args, cg.std_string)))
    cg.add(var.set_tone_length(await cg.templatable(config[CONF_TONE_LENGTH], args, cg.uint32)))
    cg.add(var.set_inter_digit_gap(await cg.templatable(config[CONF_GAP], args, cg.uint32)))
    return var


@_register_action("dtmf_tone.stop", StopAction, STOP_SCHEMA)
async def stop_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var


@_register_action("dtmf_tone.play_wav", PlayWavAction, PLAY_WAV_SCHEMA)
async def play_wav_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_name(await cg.templatable(config[CONF_NAME], args, cg.std_string)))
    cg.add(var.set_loop(await cg.templatable(config[CONF_LOOP], args, cg.bool_)))
    cg.add(var.set_preroll_ms(await cg.templatable(config[CONF_PREROLL], args, cg.uint32)))
    return var


@_register_action("dtmf_tone.bias", BiasAction, BIAS_SCHEMA)
async def bias_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    cg.add(var.set_enable(await cg.templatable(config[CONF_ENABLE], args, cg.bool_)))
    return var
