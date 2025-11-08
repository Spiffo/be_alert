"""BE Alert binary sensor platform."""

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID

from .const import DOMAIN, LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE
from .models import (
    BeAlertLocationSensorConfig,
    _slug,
)
from .sensor import BeAlertLocationEntity, BeAlertLocationSensor

_LOGGER = logging.getLogger(__name__)


def _create_location_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    coordinator,
    fetcher,
    sensor_config: dict[str, Any],
) -> list[BeAlertLocationEntity]:
    """Create location-based sensor and binary_sensor entities."""
    entities: list[BeAlertLocationEntity] = []
    entity_id = sensor_config.get(CONF_ENTITY_ID)
    if not entity_id:
        return []

    state = hass.states.get(entity_id)
    friendly_name = (
        state.name if state and state.name else entity_id.split(".")[-1]
    )

    # Create config for the sensor
    sensor_name = f"BE Alert {friendly_name}"
    sensor_unique_id = f"be_alert_{_slug(entity_id)}"
    config = BeAlertLocationSensorConfig(
        hass=hass,
        fetcher=fetcher,
        coordinator=coordinator,
        source_entity_id=entity_id,
        name=sensor_name,
        unique_id=sensor_unique_id,
        entry_id=entry.entry_id,
    )
    entities.append(BeAlertLocationSensor(config))
    entities.append(BeAlertLocationBinarySensor(config))
    return entities


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
        # base config
        binary_sensor_name = f"{config.name} Alerting"
        super().__init__(
            config, binary_sensor_name, f"{config.unique_id}_alerting"
        )

    @property
    def is_on(self) -> bool:
        """Return true if there are active alerts for the location."""
        return len(self._matches) > 0
