"""Platform for light integration."""
import logging

import voluptuous as vol

# Import the device class from the component that you want to support
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    PLATFORM_SCHEMA,
    LightEntity,
    LightEntityFeature,
    ColorMode
)

from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_NAME,
    CONF_PORT,
    CONF_MODE
)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

CONF_PWM_MODE = "pwm_mode"

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): vol.Any("relay", "led", "ro", "do"),
        vol.Required(CONF_PORT): cv.matches_regex(r"^(?:UART_)?([1-9]|1[0-5])_([0-1]?[0-9])(_0[0-9])?$"),
        vol.Required(CONF_MODE): vol.Any("on_off", "pwm"),
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [DEVICE_SCHEMA]),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Unipi Lights."""
    _LOGGER.info("Setup platform Unipi Neuron light on %s", config)
    unipi_device_name = config[CONF_DEVICE_ID]
    lights = []
    for light in config[CONF_DEVICES]:
        lights.append(
            UnipiLight(
                hass.data[DOMAIN][unipi_device_name],
                light[CONF_NAME],
                light[CONF_PORT],
                light[CONF_DEVICE],
                light[CONF_MODE],
            )
        )

    async_add_entities(lights)
    return


class UnipiLight(LightEntity):
    """Representation of an Light attached to UniPi product relay or digital output."""

    def __init__(self, unipi_hub, name, port, device, mode):
        """Initialize UniPi Light."""
        self._unipi_hub = unipi_hub
        self._name = name
        self._port = port
        self._device = device
        self._state = None
        self._dimmable = False
        self._brightness = None
        self._attr_supported_features = LightEntityFeature(0)
        if mode == "pwm":
            self._dimmable = True
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        else:
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}

    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        signal = f"{DOMAIN}_{self._unipi_hub._name}_{self._device}_{self._port}"
        _LOGGER.debug("connecting %s", signal)
        async_dispatcher_connect(self.hass, signal, self._update_callback)

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of this light entity."""
        return f"{self._device}_{self._port}_at_{self._unipi_hub._name}"

    @property
    def brightness(self):
        """Return the brightness of the light.
        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        _LOGGER.info("Get status of light %s", self._name)

        if self._dimmable:
            if self._brightness == 0:
                return False
            else:
                return True
        else:
            return self._state

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on.
        """
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]
        else:
            brightness = self._brightness
            if brightness == 0 or brightness == None:
                brightness = 255

        if self._dimmable:
            _LOGGER.info("Turn on light %s. Set britness to %d ", self._name, brightness)
            #await self._unipi_hub.evok_send(self._device, self._port, str(round(brightness / 255 * 100)))
            dict_to_send = {}
            dict_to_send["pwm_duty"] = str(round(brightness / 255 * 100))
            self._brightness = brightness
            await self._unipi_hub.evok_send(self._device, self._port, dict_to_send)
        else:
            _LOGGER.info("Turn on light %s", self._name)
            await self._unipi_hub.evok_send(self._device, self._port, "1")

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        if self._dimmable:
            _LOGGER.info("Turn off light %s. Set britness to %d ", self._name, 0)
            dict_to_send = {}
            dict_to_send["pwm_duty"] = "0"
            await self._unipi_hub.evok_send(self._device, self._port, dict_to_send)
            self._brightness = 0
        else:
            _LOGGER.info("Turn off light %s", self._name)
            await self._unipi_hub.evok_send(self._device, self._port, "0")

    # def async_update(self):
    #     """Fetch new state data for this light.
    #     This is the only method that should fetch new data for Home Assistant.
    #     """
    #     _LOGGER.info("Update light %s", self._name)
    #     self._state = self._unipi_hub.evok_state_get(self._device, self._port) == 1

    def _update_callback(self):
        """State has changed"""
        self._state = self._unipi_hub.evok_state_get(self._device, self._port) == 1
        self.schedule_update_ha_state()

