"""Init for BE Alert integration."""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
import homeassistant.helpers.config_validation as cv
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
_LOGGER.warning("BE Alert __init__.py loaded")

# Define an empty schema because this integration is configured via the UI
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Legacy YAML setup (not used, return True)."""
    _LOGGER.warning("BE Alert async_setup called")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BE Alert from a config entry."""
    _LOGGER.warning(
        "__init__.async_setup_entry: Setting up entry %s with options: %s",
        entry.entry_id, entry.options
    )

    hass.data.setdefault(DOMAIN, {})

    # Create a new coordinator for this config entry.
    # This ensures that on every reload, we get a fresh coordinator with the correct settings.
    from .data import BeAlertFetcher

    session = async_get_clientsession(hass)
    fetcher = BeAlertFetcher(session)

    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    _LOGGER.warning(
        "__init__.async_setup_entry: Using scan_interval of %s minutes.",
        scan_interval)
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=fetcher.async_update,
        update_interval=timedelta(minutes=scan_interval),
    )
    await coordinator.async_config_entry_first_refresh()
    _LOGGER.warning(
        "__init__.async_setup_entry: Coordinator initial refresh complete."
    )

    # Store the coordinator and fetcher scoped to this config entry
    hass.data[DOMAIN][entry.entry_id] = {"coordinator": coordinator, "fetcher": fetcher}

    # Register the update service if it doesn't exist yet
    if not hass.services.has_service(DOMAIN, "update"):
        async def async_update_service(service_call):
            """Handle the service call to update all BE Alert coordinators."""
            _LOGGER.info(
                "BE Alert update service called, refreshing all coordinators."
            )
            for entry_data in hass.data[DOMAIN].values():
                await entry_data["coordinator"].async_request_refresh()
        hass.services.async_register(DOMAIN, "update", async_update_service)

    # Listen for option changes
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Forward setup to the sensor platform (Standard correct format)
    _LOGGER.warning(
        "__init__.async_setup_entry: Forwarding setup to sensor and "
        "binary_sensor platforms."
    )
    await hass.config_entries.async_forward_entry_setups(
        entry, ["sensor", "binary_sensor"])

    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    _LOGGER.warning(
        "__init__.async_update_options: Options updated, reloading integration."
    )
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a BE Alert config entry."""
    _LOGGER.warning(f"Unloading BE Alert entry {entry.entry_id}")
    platforms = ["sensor", "binary_sensor"]
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # If this was the last entry, also remove the service
        if not hass.config_entries.async_entries(DOMAIN):
            hass.services.async_remove(DOMAIN, "update")
            _LOGGER.info("Last BE Alert entry unloaded, removing service.")
    else:
        _LOGGER.warning(f"Failed to unload entry {entry.entry_id}")

    return unload_ok