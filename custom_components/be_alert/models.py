"""Models for the BE Alert integration."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
    from .data import BeAlertFetcher


@dataclass
class BeAlertLocationSensorConfig:
    """Configuration for a location-based sensor."""

    hass: HomeAssistant
    fetcher: BeAlertFetcher
    coordinator: DataUpdateCoordinator
    source_entity_id: str
    name: str
    unique_id: str
    entry_id: str


def _slug(name: str) -> str:
    """Create a slug suitable for unique_id and entity_id suffix."""
    if not name:
        return "unknown"
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", name.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"
