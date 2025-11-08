"""BE Alert binary sensor platform."""

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE
from .models import BeAlertLocationSensorConfig
from .sensor import BeAlertLocationEntity
from .entity_helpers import _create_location_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BE Alert binary sensors from a config entry."""
    _LOGGER.warning(
        "binary_sensor.async_setup_entry: Started for entry %s.",
        entry.entry_id,
    )

    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    fetcher = entry_data["fetcher"]
    entities_to_add: list[BinarySensorEntity] = []

    configured_sensors = entry.options.get("sensors", [])
    for sensor_config in configured_sensors:
        sensor_type = sensor_config.get("type")

        if sensor_type in (LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE):
            # _create_location_entities returns both sensor and binary_sensor
            # Filter for BinarySensorEntity here.
            location_entities = _create_location_entities(
                hass, entry, coordinator, fetcher, sensor_config
            )
            binary_sensor_entities = [
                e
                for e in location_entities
                if isinstance(e, BinarySensorEntity)
            ]
            entities_to_add.extend(binary_sensor_entities)

    async_add_entities(entities_to_add, True)


class BeAlertLocationBinarySensor(BeAlertLocationEntity, BinarySensorEntity):
    """Binary sensor showing if alerts affect the configured zone/device."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, config: BeAlertLocationSensorConfig):
        """Initialize the location binary sensor."""
        # The unique ID and name for the binary sensor are derived from the
        super().__init__(config, "Alerting", f"{config.unique_id}_alerting")

    @property
    def is_on(self) -> bool:
        """Return true if there are active alerts for the location."""
        return len(self._matches) > 0
