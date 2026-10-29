"""Programowy dekoder DTMF dla ESP32-C3 (ADC1 continuous/DMA + Goertzel).

Uzycie:
external_components:
  - source: { type: local, path: components }
dtmf_decoder:
  id: dtmf
  pin: GPIO1
"""
from esphome import automation, pins
import esphome.codegen as cg
from esphome.components import text_sensor
from esphome.components.esp32 import include_builtin_idf_component
import esphome.config_validation as cv
from esphome.const import CONF_ID, CONF_NUMBER, CONF_PIN, CONF_TRIGGER_ID

CODEOWNERS = []
DEPENDENCIES = ["esp32"]
AUTO_LOAD = ["text_sensor"]

CONF_SAMPLE_RATE = "sample_rate"
CONF_BLOCK_SIZE = "block_size"
CONF_MIN_AMPLITUDE = "min_amplitude"
CONF_MAX_TWIST = "max_twist"
CONF_MIN_GROUP_RATIO = "min_group_ratio"
CONF_MIN_TONE_ENERGY_RATIO = "min_tone_energy_ratio"
CONF_MIN_ON_BLOCKS = "min_on_blocks"
CONF_MIN_OFF_BLOCKS = "min_off_blocks"
CONF_SEQUENCE_TIMEOUT = "sequence_timeout"
CONF_DEBUG = "debug"
CONF_ENABLED = "enabled"
CONF_LAST_DIGIT = "last_digit"
CONF_SEQUENCE = "sequence"
CONF_ON_DIGIT = "on_digit"

dtmf_ns = cg.esphome_ns.namespace("dtmf_decoder")
DTMFDecoder = dtmf_ns.class_("DTMFDecoder", cg.Component)
DigitTrigger = dtmf_ns.class_("DigitTrigger", automation.Trigger.template(cg.std_string))
EnableAction = dtmf_ns.class_("EnableAction", automation.Action)
DisableAction = dtmf_ns.class_("DisableAction", automation.Action)
ClearSequenceAction = dtmf_ns.class_("ClearSequenceAction", automation.Action)


def _validate_adc1_pin(value):
    # ESP32-C3: ADC1 = GPIO0..GPIO4 (ADC2/GPIO5 nie dziala razem z WiFi)
    num = value[CONF_NUMBER]
    if not 0 <= num <= 4:
        raise cv.Invalid("Na ESP32-C3 uzyj pinu ADC1: GPIO0..GPIO4")
    return value


def _db(value):
    if isinstance(value, str) and value.lower().endswith("db"):
        value = value[:-2]
    return cv.float_range(min=0, max=40)(value)


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(DTMFDecoder),
            cv.Required(CONF_PIN): cv.All(pins.internal_gpio_input_pin_schema, _validate_adc1_pin),
            cv.Optional(CONF_SAMPLE_RATE, default=8000): cv.int_range(min=4000, max=20000),
            cv.Optional(CONF_BLOCK_SIZE, default=205): cv.int_range(min=64, max=1024),
            cv.Optional(CONF_MIN_AMPLITUDE, default=25.0): cv.float_range(min=1, max=2000),
            cv.Optional(CONF_MAX_TWIST, default="8dB"): _db,
            cv.Optional(CONF_MIN_GROUP_RATIO, default="6dB"): _db,
            cv.Optional(CONF_MIN_TONE_ENERGY_RATIO, default=0.4): cv.float_range(min=0.0, max=1.0),
            cv.Optional(CONF_MIN_ON_BLOCKS, default=2): cv.int_range(min=1, max=20),
            cv.Optional(CONF_MIN_OFF_BLOCKS, default=2): cv.int_range(min=1, max=20),
            cv.Optional(CONF_SEQUENCE_TIMEOUT, default="3s"): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_ENABLED, default=True): cv.boolean,
            cv.Optional(CONF_DEBUG, default=False): cv.boolean,
            cv.Optional(CONF_LAST_DIGIT): text_sensor.text_sensor_schema(icon="mdi:dialpad"),
            cv.Optional(CONF_SEQUENCE): text_sensor.text_sensor_schema(icon="mdi:dialpad"),
            cv.Optional(CONF_ON_DIGIT): automation.validate_automation(
                {cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(DigitTrigger)}
            ),
        }
    ).extend(cv.COMPONENT_SCHEMA),
    cv.only_on_esp32,
)


async def to_code(config):
    include_builtin_idf_component("esp_adc")
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    cg.add(var.set_channel(config[CONF_PIN][CONF_NUMBER]))
    cg.add(var.set_sample_rate(config[CONF_SAMPLE_RATE]))
    cg.add(var.set_block_size(config[CONF_BLOCK_SIZE]))
    cg.add(var.set_min_amplitude(config[CONF_MIN_AMPLITUDE]))
    cg.add(var.set_max_twist_db(config[CONF_MAX_TWIST]))
    cg.add(var.set_min_group_ratio_db(config[CONF_MIN_GROUP_RATIO]))
    cg.add(var.set_min_tone_energy_ratio(config[CONF_MIN_TONE_ENERGY_RATIO]))
    cg.add(var.set_min_on_blocks(config[CONF_MIN_ON_BLOCKS]))
    cg.add(var.set_min_off_blocks(config[CONF_MIN_OFF_BLOCKS]))
    cg.add(var.set_sequence_timeout(config[CONF_SEQUENCE_TIMEOUT]))
    cg.add(var.set_debug(config[CONF_DEBUG]))
    if not config[CONF_ENABLED]:
        cg.add(var.set_enabled(False))

    if conf := config.get(CONF_LAST_DIGIT):
        sens = await text_sensor.new_text_sensor(conf)
        cg.add(var.set_digit_text_sensor(sens))
    if conf := config.get(CONF_SEQUENCE):
        sens = await text_sensor.new_text_sensor(conf)
        cg.add(var.set_sequence_text_sensor(sens))
    for conf in config.get(CONF_ON_DIGIT, []):
        trig = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trig, [(cg.std_string, "x")], conf)


ACTION_SCHEMA = automation.maybe_simple_id({cv.GenerateID(): cv.use_id(DTMFDecoder)})


@automation.register_action("dtmf_decoder.enable", EnableAction, ACTION_SCHEMA, synchronous=True)
@automation.register_action("dtmf_decoder.disable", DisableAction, ACTION_SCHEMA, synchronous=True)
@automation.register_action("dtmf_decoder.clear_sequence", ClearSequenceAction, ACTION_SCHEMA, synchronous=True)
async def dtmf_action_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var
