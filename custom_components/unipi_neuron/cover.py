"""Support for covers with unipi components."""
import logging

import voluptuous as vol

from homeassistant.components.cover import (
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    DEVICE_CLASSES_SCHEMA,
    ENTITY_ID_FORMAT,
    PLATFORM_SCHEMA,
    CoverEntity,
    CoverEntityFeature
)
from homeassistant.const import (
    CONF_DEVICE,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_ID,
    CONF_ENTITY_ID,
    CONF_ENTITY_PICTURE_TEMPLATE,
    CONF_FRIENDLY_NAME,
    CONF_ICON_TEMPLATE,
    CONF_NAME,
    EVENT_HOMEASSISTANT_START,
    MATCH_ALL,
    STATE_CLOSED,
    STATE_OPEN,
    STATE_OPENING,
    STATE_CLOSING
)
from homeassistant.core import callback
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.script import Script
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later
from datetime import datetime, timedelta

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)
_VALID_STATES = [STATE_OPEN, STATE_CLOSED, STATE_OPENING, STATE_CLOSING]

#oper states of blind motor drives
STATE_IDLE = "idle"
OPER_STATE_IDLE = STATE_IDLE
OPER_STATE_CLOSING = STATE_CLOSING
OPER_STATE_OPENING = STATE_OPENING
OPER_STATE_ERROR = "error"
STATE_OPENING_COOLDOWN = "open_wait"
STATE_CLOSING_COOLDOWN = "close_wait"
STATE_GENERIC_COOLDOWN = "generic_wait"

CONF_COVERS = "covers"
CONF_PORT_UP = "port_up"
CONF_PORT_DOWN = "port_down"
CONF_FULL_CLOSE_TIME = "full_close_time"
CONF_FULL_OPEN_TIME = "full_open_time"
CONF_TILT_CHANGE_TIME = "tilt_change_time"
CONF_MIN_REVERSE_DIR_TIME = "min_reverse_dir_time"

TILT_FEATURES = (
    CoverEntityFeature.OPEN
    | CoverEntityFeature.CLOSE
    | CoverEntityFeature.STOP
    | CoverEntityFeature.SET_POSITION
    | CoverEntityFeature.OPEN_TILT
    | CoverEntityFeature.CLOSE_TILT
    | CoverEntityFeature.STOP_TILT
    | CoverEntityFeature.SET_TILT_POSITION
)

COVER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE): vol.Any("relay", "led", "ro"),
        vol.Required(CONF_PORT_UP): cv.matches_regex(r"^[1-3]_[0-1][0-9]|[1-8]"),
        vol.Required(CONF_PORT_DOWN): cv.matches_regex(r"^[1-3]_[0-1][0-9]|[1-8]"),
        vol.Required(CONF_FULL_CLOSE_TIME): cv.time_period_seconds,
        vol.Required(CONF_FULL_OPEN_TIME): cv.time_period_seconds,
        vol.Required(CONF_TILT_CHANGE_TIME): cv.time_period_seconds,
        vol.Required(CONF_MIN_REVERSE_DIR_TIME): cv.time_period_seconds,

        vol.Optional(CONF_ICON_TEMPLATE): cv.template,
        vol.Optional(CONF_ENTITY_PICTURE_TEMPLATE): cv.template,
        vol.Optional(CONF_DEVICE_CLASS): DEVICE_CLASSES_SCHEMA,
        vol.Optional(CONF_FRIENDLY_NAME): cv.string,
        vol.Optional(CONF_ENTITY_ID): cv.entity_ids,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_COVERS): cv.schema_with_slug_keys(COVER_SCHEMA),
    }
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Unipi cover."""
    _LOGGER.info("Setup platform Unipi Cover on %s", config)
    unipi_device_name = config[CONF_DEVICE_ID]
    covers = []

    for device, device_config in config[CONF_COVERS].items():
        friendly_name = device_config.get(CONF_FRIENDLY_NAME, device)
        icon_template = device_config.get(CONF_ICON_TEMPLATE)
        entity_picture_template = device_config.get(CONF_ENTITY_PICTURE_TEMPLATE)
        device_class = device_config.get(CONF_DEVICE_CLASS)

        name = device_config.get(CONF_NAME)
        port_up = device_config.get(CONF_PORT_UP)
        port_down = device_config.get(CONF_PORT_DOWN)
        unipi_device_class = device_config.get(CONF_DEVICE)

        full_close_time = device_config.get(CONF_FULL_CLOSE_TIME)
        full_open_time = device_config.get(CONF_FULL_OPEN_TIME)
        tilt_change_time = device_config.get(CONF_TILT_CHANGE_TIME)
        min_reverse_time = device_config.get(CONF_MIN_REVERSE_DIR_TIME)


        template_entity_ids = set()
        if icon_template is not None:
            temp_ids = icon_template.extract_entities()
            if str(temp_ids) != MATCH_ALL:
                template_entity_ids |= set(temp_ids)

        if entity_picture_template is not None:
            temp_ids = entity_picture_template.extract_entities()
            if str(temp_ids) != MATCH_ALL:
                template_entity_ids |= set(temp_ids)

        if not template_entity_ids:
            template_entity_ids = MATCH_ALL

        entity_ids = device_config.get(CONF_ENTITY_ID, template_entity_ids)

        covers.append(
            UnipiCover(
                hass.data[DOMAIN][unipi_device_name],
                name,
                port_up,
                port_down,
                unipi_device_class,
                friendly_name,
                tilt_change_time,
                full_open_time,
                full_close_time,
                device_class,
                icon_template,
                entity_picture_template,
                entity_ids,
            )
        )
    if not covers:
        _LOGGER.error("No covers added")
        return False

    async_add_entities(covers)
    return True


class UnipiCover(CoverEntity):
    """Representation of a shades."""

    def __init__(
        self,
        unipi_hub,
        name,
        port_up,
        port_down,
        unipi_device_class,
        friendly_name,
        tilt_change_time,
        full_open_time,
        full_close_time,
        device_class,
        icon_template,
        entity_picture_template,
        entity_ids,
    ):
        """Initialize the shades."""
        self._unipi_hub = unipi_hub
        self._port_up = port_up
        self._port_down = port_down
        self._device = unipi_device_class
        self._name = friendly_name
        self._tilt_change_time = tilt_change_time/timedelta(microseconds=1000)/1000
        self._full_open_time = int(full_open_time.seconds)
        self._full_close_time = int(full_close_time.seconds)

        #config state
        self._config_state = STATE_IDLE
        #confirmed state from nauron
        self._oper_state = None

        self._time_last_movement_start = 0

        self._stop_cover_timer = None

        self._friendly_name = friendly_name
        self._icon_template = icon_template
        self._device_class = device_class
        self._entity_picture_template = entity_picture_template

        self._icon = None
        self._entity_picture = None
        self._position = None
        self._tilt_value = None
        self._entities = entity_ids
        self._available = True

    async def async_added_to_hass(self):
        """Register callbacks."""

        signal = f"{DOMAIN}_{self._unipi_hub._name}_{self._device}_{self._port_up}"
        _LOGGER.debug("connecting %s", signal)
        async_dispatcher_connect(self.hass, signal, self._output_update_callback)

        signal = f"{DOMAIN}_{self._unipi_hub._name}_{self._device}_{self._port_down}"
        _LOGGER.debug("connecting %s", signal)
        async_dispatcher_connect(self.hass, signal, self._output_update_callback)


    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of this cover entity."""
        return f"{self._device}_{self._port_up}_at_{self._unipi_hub._name}"

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return self._position == 0

    @property
    def is_opening(self):
        """Return true if the cover is actively opening."""
        return self._oper_state == STATE_OPENING

    @property
    def is_closing(self):
        """Return true if the cover is actively closing."""
        return self._oper_state == STATE_CLOSING

    @property
    def current_cover_position(self):
        """Return current position of cover.

        None is unknown, 0 is closed, 100 is fully open.
        """
        return self._position

    @property
    def current_cover_tilt_position(self):
        """Return current position of cover tilt.

        None is unknown, 0 is closed, 100 is fully open.
        """
        return self._tilt_value

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._icon

    @property
    def entity_picture(self):
        """Return the entity picture to use in the frontend, if any."""
        return self._entity_picture

    @property
    def device_class(self):
        """Return the device class of the cover."""
        return self._device_class

    @property
    def supported_features(self):
        """Flag supported features."""
        return TILT_FEATURES

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def available(self) -> bool:
        """Return if the device is available."""
        return self._available

    async def async_open_cover(self, **kwargs):
        """Move the cover up."""
        _LOGGER.info("Command to open;  %s %s", self._oper_state, self._config_state)
        #if cover is closing (and want to open it) this translatest to stop it
        if (self._oper_state == STATE_CLOSING):
            await self._stop()
        elif ((self._oper_state == STATE_IDLE) and (self._config_state == STATE_IDLE)) or (self._config_state == STATE_OPENING_COOLDOWN):
            self._config_state = STATE_OPENING
            #just to be on the safe side also set down to 0
            await self._unipi_hub.evok_send(self._device, self._port_down, "0")
            await self._unipi_hub.evok_send(self._device, self._port_up, "1")
            _LOGGER.info("Cover OPENING %s", self._config_state)

    async def async_close_cover(self, **kwargs):
        """Move the cover down."""
        _LOGGER.info("Command to close;  %s %s", self._oper_state, self._config_state)
        #if cover is opening (and want to close it) this translatest to stop it
        if (self._oper_state == STATE_OPENING):
            await self._stop()
        elif ((self._oper_state == STATE_IDLE) and (self._config_state == STATE_IDLE)) or (self._config_state == STATE_CLOSING_COOLDOWN):
            self._config_state = STATE_CLOSING
            #just to be on the safe side also set up to 0
            await self._unipi_hub.evok_send(self._device, self._port_up, "0")
            await self._unipi_hub.evok_send(self._device, self._port_down, "1")
            _LOGGER.info("Cover CLOSING %s", self._config_state)


    @callback
    async def _stop_cover_timeout(self, _):
        await self._stop()

    async def async_stop_cover(self, **kwargs):
        await self._stop()

    async def _stop(self):
        self._cancel_any_pending_stop_cover_timers()
        if self._oper_state == STATE_OPENING:
            self._config_state = STATE_OPENING_COOLDOWN
            async_call_later(self.hass, 1, self._cooldown_sate)
        elif self._oper_state == STATE_CLOSING:
            self._config_state = STATE_CLOSING_COOLDOWN
            async_call_later(self.hass, 1, self._cooldown_sate)
        elif (self._oper_state == STATE_IDLE) and ((self._config_state == STATE_OPENING) or (self._config_state == STATE_CLOSING)):
            #this should not happen but it does (when??). Anyhow this is a generic WA :)
            _LOGGER.error("Cover oper state in IDLE but config state in %s", self._config_state)
            self._config_state = STATE_GENERIC_COOLDOWN
            async_call_later(self.hass, 1, self._cooldown_sate)

        await self._unipi_hub.evok_send(self._device, self._port_up, "0")
        await self._unipi_hub.evok_send(self._device, self._port_down, "0")


    async def _cooldown_sate(self, *_):
        #needs work!!!
        self._config_state = STATE_IDLE


    async def async_set_cover_position(self, **kwargs):
        """Set cover position."""
        """
        We don't actually have a detectors for cover postitions, so we do it
        based on time motor was running in specific direction. This is far from
        accurate. We use two automatic calibration points - closed and open positions;
        calibrated when the user has motor running in one direction more time than set
        in close_wait or open_wait congfig respectively
        """
        new_position = kwargs[ATTR_POSITION]

        #if we don't yet know the position of the cover, only 0 and 100 is excepted
        if (self._position == None):
            if new_position == 0:
                self._cancel_any_pending_stop_cover_timers()
                await self.async_close_cover()
                self._stop_cover_timer = async_call_later(self.hass, self._full_close_time, self._stop_cover_timeout)
            elif new_position == 100:
                self._cancel_any_pending_stop_cover_timers()
                await self.async_open_cover()
                self._stop_cover_timer = async_call_later(self.hass, self._full_open_time, self._stop_cover_timeout)
        else:
            position, tilt = current_state = self._get_position_and_tilt(self._oper_state, self._time_last_movement_start, datetime.now(), False)
            stop_timer = 0
            #if new position is 100 or 0, add additional time (1/10th), to "fix" any nonlinearity from previous movements
            #and to drive the motors also in case our internal thinks we are fully opened or closed
            if new_position == 100:
                new_position = 110
            if new_position == 0:
                new_position = -10

            if new_position > position:
                stop_timer = (new_position - position)*self._full_open_time/100
                self._cancel_any_pending_stop_cover_timers()
                await self.async_open_cover()
                self._stop_cover_timer = async_call_later(self.hass, stop_timer, self._stop_cover_timeout)
            if new_position < position:
                stop_timer = (position - new_position)*self._full_open_time/100
                self._cancel_any_pending_stop_cover_timers()
                await self.async_close_cover()
                self._stop_cover_timer = async_call_later(self.hass, stop_timer, self._stop_cover_timeout)

            _LOGGER.info("Setting cover %s to position %d; timeout %d", self._friendly_name, new_position, stop_timer)


    async def async_open_cover_tilt(self, **kwargs):
        """Tilt the cover open."""
        data = {ATTR_TILT_POSITION: 100}
        await self.async_set_cover_tilt_position(**data)



    async def async_close_cover_tilt(self, **kwargs):
        """Tilt the cover closed."""
        data = {ATTR_TILT_POSITION: 0}
        await self.async_set_cover_tilt_position(**data)



    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        new_tilt_value = kwargs[ATTR_TILT_POSITION]

        if (self._tilt_value == None):
            if new_tilt_value == 0:
                self._cancel_any_pending_stop_cover_timers()
                await self.async_close_cover()
                self._stop_cover_timer = async_call_later(self.hass, self._tilt_change_time, self._stop_cover_timeout)
            elif new_tilt_value == 100:
                self._cancel_any_pending_stop_cover_timers()
                await self.async_open_cover()
                self._stop_cover_timer = async_call_later(self.hass, self._tilt_change_time, self._stop_cover_timeout)
        else:
            position, tilt = current_state = self._get_position_and_tilt(self._oper_state, self._time_last_movement_start, datetime.now(), False)

            if new_tilt_value > tilt:
                stop_timer = (new_tilt_value - tilt)*self._tilt_change_time/100
                self._cancel_any_pending_stop_cover_timers()
                await self.async_open_cover()
                self._stop_cover_timer = async_call_later(self.hass, stop_timer, self._stop_cover_timeout)
            if new_tilt_value < tilt:
                stop_timer = (tilt - new_tilt_value)*self._tilt_change_time/100
                self._cancel_any_pending_stop_cover_timers()
                await self.async_close_cover()
                self._stop_cover_timer = async_call_later(self.hass, stop_timer, self._stop_cover_timeout)


        _LOGGER.info("Setting cover %s tilt to  %d", self._friendly_name, new_tilt_value)



    async def async_update(self):
        """Update the state from the template."""

        for property_name, template in (
            ("_icon", self._icon_template),
            ("_entity_picture", self._entity_picture_template),
        ):
            if template is None:
                continue

            try:
                value = template.async_render()
                if property_name == "_available":
                    value = value.lower() == "true"
                setattr(self, property_name, value)
            except TemplateError as ex:
                friendly_property_name = property_name[1:].replace("_", " ")
                if ex.args and ex.args[0].startswith(
                    "UndefinedError: 'None' has no attribute"
                ):
                    # Common during HA startup - so just a warning
                    _LOGGER.warning(
                        "Could not render %s template %s," " the state is unknown.",
                        friendly_property_name,
                        self._name,
                    )
                    return

                try:
                    setattr(self, property_name, getattr(super(), property_name))
                except AttributeError:
                    _LOGGER.error(
                        "Could not render %s template %s: %s",
                        friendly_property_name,
                        self._name,
                        ex,
                    )

    def _get_position_and_tilt(self, oper_state, start_time, stop_time, update = False):
        if start_time == 0 or oper_state not in (OPER_STATE_OPENING, OPER_STATE_CLOSING):
            return (self._position, self._tilt_value)

        if start_time > stop_time:
            _LOGGER.error("Posoition/tilt time error %s start: %d, stop: %d",
                        friendly_property_name,
                        start_time,
                        stop_time,
                    )
            return

        deltatime = (stop_time - start_time)/timedelta(microseconds=1000)
        print("Delatatime is", deltatime, " Tiltchaneg is", self._tilt_change_time)
        new_position_value = None
        new_tilt_value = None

        #tilt
        if oper_state == OPER_STATE_OPENING:
            if deltatime >= self._tilt_change_time*1000:
                new_tilt_value = 100
            else:
                tilt_change = deltatime*100/self._tilt_change_time/1000
                try:
                    new_tilt_value = self._tilt_value + tilt_change
                    if new_tilt_value > 100:
                        new_tilt_value = 100
                except:
                    pass

        if oper_state == OPER_STATE_CLOSING:
            if deltatime >= self._tilt_change_time*1000:
                new_tilt_value = 0
            else:
                tilt_change = deltatime*100/self._tilt_change_time/1000
                try:
                    new_tilt_value = self._tilt_value - tilt_change
                    if new_tilt_value < 0:
                        new_tilt_value = 0
                except:
                    pass


        #position
        if oper_state == OPER_STATE_OPENING:
            if deltatime >= self._full_open_time*1000:
                new_position_value = 100
            else:
                position_change = deltatime*100/(self._full_open_time*1000)
                try:
                    new_position_value = self._position + position_change
                    if new_position_value > 100:
                        new_position_value = 100
                except:
                    pass
        if oper_state == OPER_STATE_CLOSING:
            if deltatime >= self._full_close_time*1000:
                new_position_value = 0
            else:
                position_change = deltatime*100/(self._full_close_time*1000)
                try:
                    new_position_value = self._position - position_change
                    if new_position_value < 0:
                        new_position_value = 0
                except:
                    pass

        if update:
            try:
                self._position = new_position_value
                self._tilt_value = new_tilt_value
            except:
                pass

        return (new_position_value, new_tilt_value)

    def _cancel_any_pending_stop_cover_timers(self):
        """Cancel any pending updates to stop movement of blinds."""
        if self._stop_cover_timer:
            _LOGGER.debug("%s: canceled pending stop timer", self.entity_id)
            self._stop_cover_timer()
            self._stop_cover_timer = None


    def _output_update_callback(self):
        """Output signal state from neuron has changed"""
        motor_driver_up_state = self._unipi_hub.evok_state_get(self._device, self._port_up) == 1
        motor_driver_down_state = self._unipi_hub.evok_state_get(self._device, self._port_down) == 1
        if not motor_driver_up_state and not motor_driver_down_state:
            new_oper_state = OPER_STATE_IDLE
        elif not motor_driver_up_state and motor_driver_down_state:
            new_oper_state = OPER_STATE_CLOSING
        elif motor_driver_up_state and not motor_driver_down_state:
            new_oper_state = OPER_STATE_OPENING
        else:
            new_oper_state = OPER_STATE_ERROR
            _LOGGER.error(
                        "Detected signals on both motor drivers for",
                        friendly_property_name,
                        self._name,
                    )
        _LOGGER.info("Cover oper state %s", self._oper_state)

        if new_oper_state != self._oper_state:
            if new_oper_state == OPER_STATE_IDLE:
                 #update position and tilt
                self._get_position_and_tilt(self._oper_state, self._time_last_movement_start, datetime.now(), True)
                # clear start time
                self._time_last_movement_start = 0

            self._oper_state = new_oper_state

            #start timer for either closing on opening
            if self._oper_state in (OPER_STATE_OPENING, OPER_STATE_CLOSING):
                self._time_last_movement_start = datetime.now()

            self.schedule_update_ha_state()


