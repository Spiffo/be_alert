"""BE Alert binary sensor platform."""
import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID

from .const import DOMAIN, LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE
from .sensor import BeAlertLocationEntity, _slug

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BE Alert binary sensors from a config entry."""
    _LOGGER.warning(
        "binary_sensor.async_setup_entry: Started for entry %s.",
        entry.entry_id)

    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    fetcher = entry_data["fetcher"]
    entities_to_add = []

    configured_sensors = entry.options.get("sensors", [])
    for sensor_config in configured_sensors:
        sensor_type = sensor_config.get("type")

        if sensor_type in (LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE):
            entity_id = sensor_config.get(CONF_ENTITY_ID)
            if not entity_id:
                continue

            state = hass.states.get(entity_id)
            if state and state.name:
                friendly_name = state.name
            else:
                friendly_name = entity_id.split(".")[-1]
            sensor_name = f"BE Alert {friendly_name} Alerting"
            sensor_unique_id = f"be_alert_{_slug(entity_id)}_alerting"

            _LOGGER.warning(
                "binary_sensor.async_setup_entry: Preparing location "
                "binary_sensor. Name: '%s', Unique ID: '%s'",
                sensor_name, sensor_unique_id
            )
            entities_to_add.append(
                BeAlertLocationBinarySensor(
                    hass, fetcher, coordinator, entity_id, sensor_name,
                    sensor_unique_id, entry.entry_id)
            )

    async_add_entities(entities_to_add, True)


class BeAlertLocationBinarySensor(BeAlertLocationEntity, BinarySensorEntity):
    """Binary sensor showing if alerts affect the configured zone/device."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(
        self,
        hass: HomeAssistant,
        fetcher,
        coordinator,
        source_entity_id: str,
        name: str,
        unique_id: str,
        entry_id: str,
    ):
        super().__init__(hass, fetcher, coordinator, source_entity_id, name,
                         unique_id, entry_id)
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def is_on(self) -> bool:
        """Return true if there are active alerts for the location."""
        return len(self._matches) > 0