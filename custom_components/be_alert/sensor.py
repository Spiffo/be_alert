"""BE Alert sensor platform."""
import logging
from typing import Any
import re

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry 
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_ENTITY_ID

from .const import DOMAIN, LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE
from .data import BeAlertFetcher

_LOGGER = logging.getLogger(__name__)


def _slug(name: str) -> str:
    """Create a slug suitable for unique_id and entity_id suffix."""
    if not name:
        return "unknown"
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities, discovery_info=None):
    """Set up BE Alert sensors from a config entry."""
    _LOGGER.warning(f"sensor.async_setup_entry: Started for entry {entry.entry_id}.")

    # The coordinator is set up in __init__.py, so we just retrieve it.
    entry_data = hass.data[DOMAIN][entry.entry_id]
    coordinator = entry_data["coordinator"]
    fetcher = entry_data["fetcher"]
    entities_to_add = []

    # Get the list of configured sensors from the options
    configured_sensors = entry.options.get("sensors", [])
    _LOGGER.warning(f"sensor.async_setup_entry: Found {len(configured_sensors)} sensor configurations in options: {configured_sensors}")

    # Proactively remove stale entities from the registry for this entry
    try:
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
                    desired_unique_ids.add(f"be_alert_{slug_eid}_alerting") # For binary sensor
        # Remove entities for this config entry that are no longer desired
        for ent in list(registry.entities.values()):
            if ent.config_entry_id != entry.entry_id:
                continue
            if ent.domain not in ("sensor", "binary_sensor"):
                continue
            if ent.unique_id not in desired_unique_ids:
                _LOGGER.debug("sensor.async_setup_entry: Removing stale entity %s (unique_id=%s)", ent.entity_id, ent.unique_id)
                registry.async_remove(ent.entity_id)
    except Exception as err:
        _LOGGER.debug("sensor.async_setup_entry: Failed to cleanup stale entities: %s", err)

    for sensor_config in configured_sensors:
        sensor_type = sensor_config.get("type")
        _LOGGER.warning(f"sensor.async_setup_entry: Processing sensor config: {sensor_config}")

        if sensor_type == "all":
            # Create the "All" sensor if not already present
            # The unique_id for the "All" sensor is 'be_alert_all'
            _LOGGER.warning("sensor.async_setup_entry: Preparing 'all' sensor.")
            entities_to_add.append(BeAlertAllSensor(fetcher, coordinator, entry.entry_id))

        elif sensor_type in (LOCATION_SOURCE_DEVICE, LOCATION_SOURCE_ZONE):
            entity_id = sensor_config.get(CONF_ENTITY_ID)
            if not entity_id:
                _LOGGER.warning(f"sensor.async_setup_entry: Skipping location sensor with no entity_id: {sensor_config}")
                continue

            state = hass.states.get(entity_id)
            friendly_name = state.name if state and state.name else entity_id.split(".")[-1]
            sensor_name = f"BE Alert {friendly_name}"
            sensor_unique_id = f"be_alert_{_slug(entity_id)}"
            _LOGGER.warning(f"sensor.async_setup_entry: Preparing location sensor. Name: '{sensor_name}', Unique ID: '{sensor_unique_id}' for entry {entry.entry_id}")
            entities_to_add.append(BeAlertLocationSensor(hass, fetcher, coordinator, entity_id, sensor_name, sensor_unique_id, entry.entry_id))

    if entities_to_add:
        _LOGGER.warning(f"sensor.async_setup_entry: Calling async_add_entities with {len(entities_to_add)} entities.")
        async_add_entities(entities_to_add, True)
    else:
        _LOGGER.warning("sensor.async_setup_entry: No entities to add.")


def _get_coordinates(hass: HomeAssistant, entity_id: str):
    """Get latitude and longitude for zone or device entity_id synchronously."""
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
            entry_type="service",
        )

class BeAlertAllSensor(BeAlertDevice, SensorEntity):
    """Sensor showing total number of active alerts and full list."""

    def __init__(self, fetcher: BeAlertFetcher, coordinator: DataUpdateCoordinator, entry_id: str):
        super().__init__(coordinator, entry_id)
        self._fetcher = fetcher

    @property
    def name(self) -> str:
        return "BE Alert All"
    @property
    def unique_id(self):
        return "be_alert_all"

    @property
    def state(self):
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
    """Sensor showing number of alerts that affect the configured zone/device."""

    def __init__(
        self,
        hass: HomeAssistant,
        fetcher: BeAlertFetcher,
        coordinator: DataUpdateCoordinator,
        source_entity_id: str,
        name: str,
        unique_id: str,
        entry_id: str,
    ):
        super().__init__(coordinator)
        self._fetcher: BeAlertFetcher = fetcher
        self._source_entity = source_entity_id
        self._name = name  # Store name for logging

        # Create a new device for each tracked location, linked to the main integration device
        slug = _slug(source_entity_id)
        state = hass.states.get(source_entity_id)
        device_name = state.name if state else source_entity_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, slug)},
            name=device_name,
            manufacturer="BE-Alert",
            model=f"Tracked {source_entity_id.split('.')[0]}",
            via_device=(DOMAIN, entry_id),
        )

        # These will be populated during the update
        self._lat: float | None = None
        self._lon: float | None = None
        self._matches: list[dict] = []
        self._source_has_coords: bool = False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs: dict[str, Any] = {"source": self._source_entity}
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
        coords = _get_coordinates(self.hass, self._source_entity)
        if coords:
            self._lat, self._lon = coords
            self._source_has_coords = True
        else:
            self._source_has_coords = False
            _LOGGER.debug("Could not get coordinates for %s, location sensor unavailable.", self._source_entity)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # First, get the most recent location
        self._update_location()
        # Then, find alerts for that location if source is available
        if self._source_has_coords:
            self._matches = self._fetcher.alerts_affecting_point(self._lon, self._lat)
        else:
            self._matches = []
        _LOGGER.debug("BE Alert: %s found %d active alerts (available=%s)", self._name, len(self._matches), self._source_has_coords)
        self.async_write_ha_state()


class BeAlertLocationSensor(BeAlertLocationEntity, SensorEntity):
    """Sensor showing number of alerts that affect the configured zone/device."""

    def __init__(
        self,
        hass: HomeAssistant,
        fetcher: BeAlertFetcher,
        coordinator: DataUpdateCoordinator,
        source_entity_id: str,
        name: str,
        unique_id: str,
        entry_id: str,
    ):
        super().__init__(hass, fetcher, coordinator, source_entity_id, name, unique_id, entry_id)
        self._attr_name = name
        self._attr_unique_id = unique_id

    @property
    def state(self):
        """Return the number of active alerts for the location."""
        return len(self._matches)