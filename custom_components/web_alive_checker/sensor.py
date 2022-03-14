from datetime import timedelta, date, datetime
import logging
import time
import math

import aiohttp
import asyncio

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.components.sensor import ENTITY_ID_FORMAT, PLATFORM_SCHEMA
from homeassistant.const import (
    CONF_SENSORS, CONF_NAME, CONF_TYPE,
    DEVICE_CLASS_POWER, DEVICE_CLASS_TIMESTAMP,
)
from homeassistant.helpers.entity import Entity, async_generate_entity_id
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
from homeassistant.util.json import load_json
from homeassistant.helpers.event import async_track_point_in_utc_time


_LOGGER = logging.getLogger(__name__)

SENSOR_TYPE_STATE = 'state'
SENSOR_TYPES = {
    SENSOR_TYPE_STATE : [DEVICE_CLASS_POWER, 'SENSOR_TYPE_STATE', '']
}

DEFAULT_SENSOR_TYPES = list(SENSOR_TYPES.keys())

CONF_URL = 'url'
CONF_INTERVAL = 'interval'
CONF_EXPECTED_STATUS = 'expected_status'

SENSOR_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default=''): cv.string,
    vol.Required(CONF_URL, default=''): cv.string,
    vol.Required(CONF_INTERVAL, default=300): cv.positive_int,
    vol.Required(CONF_EXPECTED_STATUS, default=200): cv.positive_int
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_SENSORS): cv.schema_with_slug_keys(SENSOR_SCHEMA),
})

async def test_http_status_code(url, expected):
    to = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=to) as session:
        try:
            async with session.get(url) as resp:
                await resp.text()
                return expected == resp.status
        except:
            _LOGGER.info("exception occurred!!")
            return False

test_history = {}
async def get_test_http_status_code_value(url, expected):
    newKeyStr = time.strftime('%y%m%d%H%M%S', time.localtime())
    newKey = math.floor(int(newKeyStr) / 10)
    keys_to_remove = []

    if newKey not in test_history.keys():
        for eachKey in test_history.keys():
            if eachKey != newKey:
                keys_to_remove.append(eachKey)

        for eachKey in keys_to_remove:
            test_history.pop(eachKey)

        test_history[newKey] = await test_http_status_code(url, expected)

    return test_history[newKey]

sensor_icons = {
    SENSOR_TYPE_STATE : 'mdi:web',
}

class DataStore:
    def __init__(self, hass, sensors, interval):
        self._hass = hass
        self._sensors = sensors
        self._interval = interval

    def get_next_interval(self):
        now = dt_util.utcnow()
        interval = now + timedelta(seconds=self._interval)
        return interval

    @callback
    async def point_in_time_listener(self, now):
        """Get the latest data and update state."""
        for sensor in self._sensors:
            await sensor._update_internal_state()
            sensor.async_schedule_update_ha_state(True)
        async_track_point_in_utc_time(
            self._hass, self.point_in_time_listener, self.get_next_interval())


data_stores = []
async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Anniversary sensor."""
    if hass.config.time_zone is None:
        _LOGGER.error("Timezone is not set in Home Assistant configuration")
        return False

    for device, device_config in config[CONF_SENSORS].items():
        url = device_config.get(CONF_URL)
        expected_status = device_config.get(CONF_EXPECTED_STATUS)
        interval = device_config.get(CONF_INTERVAL)

        result = await test_http_status_code(url, expected_status)

        # https://stackoverflow.com/questions/29867405/python-asyncio-return-vs-set-result

        _LOGGER.info("current values : {}".format(result))

        sensors = []
        sensor = WebAliveCheckSensor(hass, device, url, expected_status, True, interval)
        sensors.append(sensor)

        data_store = DataStore(hass, sensors, interval)
        data_stores.append(data_store)

        async_track_point_in_utc_time(
            hass, data_store.point_in_time_listener, data_store.get_next_interval())

    async_add_entities(sensors, True)


class WebAliveCheckSensor(Entity):
    def __init__(self, hass, name, url, expected_code, initial_value, interval):
        self.hass = hass
        self.entity_id = async_generate_entity_id(ENTITY_ID_FORMAT, "{}_{}".format(name, SENSOR_TYPE_STATE), hass=hass)
        self._name = name
        self._url = url
        self._expected_code = expected_code
        self._sensor_type = SENSOR_TYPE_STATE
        self._interval = interval
        self._extra_state_attributes = { }
        self._attr_state = initial_value
        self._attr_name = "{} {}".format(name, SENSOR_TYPES[self._sensor_type][1])
        self._attr_unit_of_measurement = SENSOR_TYPES[self._sensor_type][2]
        _LOGGER.info("WebAliveCheckSensor created name : {}, url {}, expected_code {}, interval {}".format(name, url, expected_code, interval))

    @property
    def name(self):
        if self._sensor_type in SENSOR_TYPES:
            return "{} {}".format(self._name, SENSOR_TYPES[self._sensor_type][2])
        else:
            return "{} {}".format(self._name, self._sensor_type)

    @property
    def state(self):
        return self._attr_state

    @property
    def icon(self):
        if self._sensor_type in sensor_icons:
            return sensor_icons[self._sensor_type]
        return ""

    @property
    def extra_state_attributes(self):
        return self._extra_state_attributes

    #@property
    #def should_poll(self):
    #    _LOGGER.info("Returning false for should_poll")
    #    return False

    #How to update state
    #https://developers.home-assistant.io/docs/core/entity/
    async def _update_internal_state(self):
        try:
            self._attr_state = await get_test_http_status_code_value(self._url, self._expected_code)
            _LOGGER.info("status updated")
        except:
            _LOGGER.error("Exception occured!!")
        return self._attr_state

