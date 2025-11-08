"""BE Alert sensor platform."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_registry import (
    async_get as async_get_entity_registry,
)
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    CoordinatorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_ENTITY_ID

from .const import DOMAIN, LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE, Any
from .binary_sensor import _create_location_entities
from .data import BeAlertFetcher
from .models import BeAlertLocationSensorConfig, _slug

_LOGGER = logging.getLogger(__name__)


async def _async_cleanup_stale_entities(
    hass: HomeAssistant, entry, configured_sensors: list[dict[str, Any]]
) -> None:
    """Remove stale entities from the registry for this entry."""
    registry = async_get_entity_registry(hass)
    desired_unique_ids = set()
    for s in configured_sensors:
        s_type = s.get("type")
        if s_type == "all":
            desired_unique_ids.add("be_alert_all")
        elif s_type in (LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE):
            eid = s.get(CONF_ENTITY_ID)
            if eid:
                slug_eid = _slug(eid)
                desired_unique_ids.add(f"be_alert_{slug_eid}")
                # For binary sensor
                desired_unique_ids.add(f"be_alert_{slug_eid}_alerting")

    # Remove entities for this config entry that are no longer desired
    for ent in list(registry.entities.values()):
        if ent.config_entry_id != entry.entry_id:
            continue
        if ent.domain not in ("sensor", "binary_sensor"):
            continue
        if ent.unique_id not in desired_unique_ids:
            _LOGGER.debug(
                "sensor.async_setup_entry: Removing stale entity %s "
                "(unique_id=%s)",
                ent.entity_id,
                ent.unique_id,
            )
            registry.async_remove(ent.entity_id)


def _create_entities_from_config(
    hass: HomeAssistant, entry, coordinator, fetcher, configured_sensors
) -> list[SensorEntity]:  # pylint: disable=R0914
    """Create sensor entities based on the integration's configuration."""
    entities_to_add: list[SensorEntity] = []

    for sensor_config in configured_sensors:
        sensor_type = sensor_config.get("type")
        _LOGGER.warning(
            "sensor.async_setup_entry: Processing sensor config: %s",
            sensor_config,
        )

        if sensor_type == "all":
            _LOGGER.warning(
                "sensor.async_setup_entry: Preparing the 'all' sensor."
            )
            entities_to_add.append(
                BeAlertAllSensor(fetcher, coordinator, entry.entry_id)
            )

        elif sensor_type in (LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE):
            # _create_location_entities returns both sensor and binary_sensor
            # Filter for SensorEntity here.
            location_entities = _create_location_entities(
                hass, entry, coordinator, fetcher, sensor_config
            )
            sensor_entities = [
                e for e in location_entities if isinstance(e, SensorEntity)
            ]
            entities_to_add.extend(sensor_entities)

    return entities_to_add


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Set up BE Alert sensors from a config entry."""
    _LOGGER.warning(
        "sensor.async_setup_entry: Started for entry %s.", entry.entry_id
    )

    entry_data = hass.data[DOMAIN][entry.entry_id]
    configured_sensors = entry.options.get("sensors", [])

    try:
        await _async_cleanup_stale_entities(hass, entry, configured_sensors)
    except (AttributeError, KeyError) as err:
        _LOGGER.debug(
            "sensor.async_setup_entry: Failed to cleanup stale entities: %s",
            err,
        )

    entities_to_add = _create_entities_from_config(
        hass,
        entry,
        entry_data["coordinator"],
        entry_data["fetcher"],
        configured_sensors,
    )

    if entities_to_add:
        _LOGGER.warning(
            "sensor.async_setup_entry: Calling async_add_entities with %d "
            "entities.",
            len(entities_to_add),
        )
        # Filter to only add SensorEntity instances in this platform setup
        sensor_entities = [
            e for e in entities_to_add if isinstance(e, SensorEntity)
        ]
        async_add_entities(sensor_entities, True)

    else:
        _LOGGER.warning("sensor.async_setup_entry: No entities to add.")


def _get_coordinates(hass: HomeAssistant, entity_id: str):
    """Get lat and long for zone or device entity_id synchronously."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if not state:
        return None
    if "latitude" in state.attributes and "longitude" in state.attributes:
        return state.attributes["latitude"], state.attributes["longitude"]
    return None


# ------------------- Global sensor (all alerts) -------------------


class BeAlertDevice(CoordinatorEntity):
    """Base class for BE Alert entities linked to the main device."""

    def __init__(self, coordinator: DataUpdateCoordinator, entry_id: str):
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="BE Alert",
            manufacturer="BE-Alert",
            model="Alert Feed",
            entry_type=DeviceEntryType.SERVICE,
        )


class BeAlertAllSensor(BeAlertDevice, SensorEntity):
    """Sensor showing total number of active alerts and full list."""

    def __init__(
        self,
        fetcher: BeAlertFetcher,
        coordinator: DataUpdateCoordinator,
        entry_id: str,
    ):
        super().__init__(coordinator, entry_id)
        self._fetcher = fetcher

    @property
    def name(self) -> str:
        return "BE Alert All"

    @property
    def unique_id(self):
        return "be_alert_all"

    @property
    def native_value(self):
        return len(self._fetcher.alerts)

    @property
    def extra_state_attributes(self):
        attrs: dict[str, Any] = {
            "alerts": [
                {
                    "title": a["title"],
                    "link": a["link"],
                    "category": a["category"],
                    "pubDate": a["pubDate"],
                    "startDate": a["startDate"],
                    "expirationDate": a["expirationDate"],
                    "description": a["description"],
                }
                for a in self._fetcher.alerts
            ],
            "last_checked": self._fetcher.last_checked,
        }
        return attrs


# ------------------- Per-location sensor (zone/device) -------------------


class BeAlertLocationEntity(CoordinatorEntity):
    """Sensor showing number of alerts that affect the configured
    zone/device."""

    _attr_has_entity_name = True

    def __init__(
        self,
        config: BeAlertLocationSensorConfig,
        name: str | None = None,
        unique_id: str | None = None,
    ):
        """Initialize the location entity."""  # noqa: R0913
        super().__init__(config.coordinator)
        self.config = config

        self._attr_name = name or config.name
        self._attr_unique_id = unique_id or config.unique_id

        # Create a new device for each tracked location, linked to the main
        # integration device
        slug = _slug(config.source_entity_id)
        state = self.config.hass.states.get(config.source_entity_id)
        device_name = state.name if state else config.source_entity_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, slug)},
            name=device_name,
            manufacturer="BE-Alert",
            model=f"Tracked {config.source_entity_id.split('.', 1)[0]}",
            via_device=(DOMAIN, config.entry_id),
        )

        # These will be populated during the update
        self._lat: float | None = None
        self._lon: float | None = None
        self._matches: list[dict] = []
        self._source_has_coords: bool = False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs: dict[str, Any] = {"source": self.config.source_entity_id}
        if self._matches:
            attrs["alerts"] = [
                {
                    "title": a["title"],
                    "link": a["link"],
                    "category": a["category"],
                    "pubDate": a["pubDate"],
                    "startDate": a["startDate"],
                    "expirationDate": a["expirationDate"],
                    "description": a["description"],
                }
                for a in self._matches
            ]
        return attrs

    @property
    def available(self) -> bool:
        """Entity availability depends on source entity having coordinates."""
        return self._source_has_coords

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._update_location()

    def _update_location(self) -> None:
        """Fetch the latest coordinates from the source entity."""
        coords = _get_coordinates(
            self.config.hass, self.config.source_entity_id
        )
        if coords:
            self._lat, self._lon = coords
            self._source_has_coords = True
        else:
            self._source_has_coords = False
            _LOGGER.debug(
                "Could not get coordinates for %s, location sensor "
                "unavailable.",
                self.config.source_entity_id,
            )

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # First, get the most recent location
        self._update_location()
        # Then, find alerts for that location if source is available
        if self._source_has_coords:
            self._matches = self.config.fetcher.alerts_affecting_point(
                self._lon, self._lat
            )
        else:
            self._matches = []
        _LOGGER.debug(
            "BE Alert: %s found %d active alerts (available=%s)",  # type: ignore
            self.name,
            len(self._matches),
            self._source_has_coords,
        )
        self.async_write_ha_state()


class BeAlertLocationSensor(BeAlertLocationEntity, SensorEntity):
    """Sensor showing number of alerts that affect the
    configured zone/device."""

    def __init__(self, config: BeAlertLocationSensorConfig):
        """Initialize the location sensor."""
        super().__init__(config, config.name, config.unique_id)

    @property
    def native_value(self):
        """Return the number of active alerts for the location."""
        return len(self._matches)
