"""Support for Unipi product line binary sensors."""
import logging

import voluptuous as vol

from homeassistant.components.binary_sensor import (
    DEVICE_CLASSES_SCHEMA,
    PLATFORM_SCHEMA,
    BinarySensorEntity,
)

from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_DEVICES,
    CONF_NAME,
    CONF_PORT
)

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): vol.Any("input", "di"),
        vol.Required(CONF_PORT): cv.matches_regex(r"^[1-9]_[0-1][0-9]$|^1[0-2]$|^[1-9]$"),
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_DEVICES): vol.All( cv.ensure_list, [DEVICE_SCHEMA])
    }
)

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up Binary Sensor for Unipi."""
    _LOGGER.info("Setup platform for Unipi Binary Sensor %s", config)
    unipi_device_name = config[CONF_DEVICE_ID]
    binary_sensors = []
    for sensor in config[CONF_DEVICES]:
        binary_sensors.append(
            UnipiBinarySensor(
                hass.data[DOMAIN][unipi_device_name],
                sensor[CONF_NAME],
                sensor[CONF_PORT],
                sensor[CONF_DEVICE],
            )
        )

    async_add_entities(binary_sensors)
    return


class UnipiBinarySensor(BinarySensorEntity):
    """Representation of binary sensors as digital input on Unipi Device."""

    def __init__(self, unipi_hub, name, port, device):
        """Initialize Unipi binary sensor."""
        self._unipi_hub = unipi_hub
        self._name = name
        self._port = port
        self._device = device
        self._state = None

    async def async_added_to_hass(self):
        """Register device notification."""
        #await self.async_initialize_device(self._ads_var, self._ads_hub.PLCTYPE_BOOL)
        signal = f"{DOMAIN}_{self._unipi_hub._name}_{self._device}_{self._port}"
        _LOGGER.debug("Binary Sensor: Connecting %s", signal)
        async_dispatcher_connect(self.hass, signal, self._update_callback)

    @property
    def is_on(self):
        """Return True if the entity is on."""
        return self._state

    @property
    def name(self):
        """Return the display name of this binary sensor."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of this binary sensor entity."""
        return f"{self._device}_{self._port}_at_{self._unipi_hub._name}"

    # @property
    # def device_class(self):
    #     """Return the device class."""
    #     return self._device

    # def update(self):
    #     """Fetch new state data for this binary sensor.
    #     This is the only method that should fetch new data for Home Assistant.
    #     """
    #     _LOGGER.info("Update binary sensor %s", self._name)
    #     self._state = self._unipi_hub.evok_state_get(self._device, self._port) == 1

    def _update_callback(self):
        """State has changed"""
        self._state = self._unipi_hub.evok_state_get(self._device, self._port) == 1
        self.schedule_update_ha_state()
