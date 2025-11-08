"""Entity helper functions for the BE Alert integration."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from .sensor import BeAlertLocationEntity, BeAlertLocationSensor
    from .binary_sensor import BeAlertLocationBinarySensor

from homeassistant.const import CONF_ENTITY_ID
from .models import BeAlertLocationSensorConfig, _slug


def _create_location_entities(
    hass: "HomeAssistant",
    entry: "ConfigEntry",
    coordinator,
    fetcher,
    sensor_config: dict[str, Any],
) -> list["BeAlertLocationEntity"]:
    """Create location-based sensor and binary_sensor entities."""
    # Defer imports to prevent circular dependencies at runtime
    from .sensor import BeAlertLocationSensor  # noqa: F811
    from .binary_sensor import BeAlertLocationBinarySensor  # noqa: F811

    entities: list[BeAlertLocationEntity] = []
    entity_id = sensor_config.get(CONF_ENTITY_ID)
    if not entity_id:
        return []

    state = hass.states.get(entity_id)
    friendly_name = (
        state.name if state and state.name else entity_id.split(".")[-1]
    )

    sensor_name = f"BE Alert {friendly_name}"
    sensor_unique_id = f"be_alert_{_slug(entity_id)}"
    config = BeAlertLocationSensorConfig(
        hass,
        fetcher,
        coordinator,
        entity_id,
        sensor_name,
        sensor_unique_id,
        entry.entry_id,
    )
    entities.append(BeAlertLocationSensor(config))
    entities.append(BeAlertLocationBinarySensor(config))
    return entities
