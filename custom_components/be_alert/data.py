"""BE Alert data coordinator and fetcher with logging."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
import aiohttp
import shapely.geometry
import shapely.errors

from homeassistant.util import dt as ha_dt

from .const import FEED_URL, FEED_PARAMS

_LOGGER = logging.getLogger(__name__)


def _parse_alert_item(item: dict[str, Any]) -> dict[str, Any]:
    """Parse a single alert item from the feed into a structured dict."""
    polygons = []
    for area in item.get("area", []):
        for coordset in area.get("coordinates", []):
            if coordset.get("type") == "LineString":
                points = [
                    (p["x"], p["y"]) for p in coordset.get("coordinates", [])
                ]
                if len(points) >= 3:
                    try:
                        polygons.append(shapely.geometry.Polygon(points))
                    except (shapely.errors.ShapelyError, ValueError):
                        _LOGGER.warning(
                            "BeAlertFetcher: invalid polygon points, skipping",
                            exc_info=True,
                        )
    return {
        "title": item.get("title"),
        "link": item.get("link"),
        "category": item.get("category"),
        "pubDate": item.get("pubDate"),
        "startDate": item.get("startDate"),
        "expirationDate": item.get("expirationDate"),
        "description": item.get("description"),
        "polygons": polygons,
    }


class BeAlertFetcher:
    """Fetch BE Alert feed and parse polygons with logging."""

    def __init__(self, session: aiohttp.ClientSession):
        self._session = session
        self.alerts: list[dict] = []
        self.last_checked: str | None = None

    async def async_update(self) -> None:
        """Fetch feed and parse polygons; update last_checked time."""
        _LOGGER.warning("BeAlertFetcher.async_update: starting fetch")
        self.last_checked = ha_dt.now().isoformat()

        try:
            async with self._session.get(
                f"{FEED_URL}?{FEED_PARAMS}",
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.error("BeAlertFetcher.async_update: fetch failed: %s", err)
            self.alerts = []
            return

        self.alerts = [
            _parse_alert_item(item) for item in data.get("items", [])
        ]
        _LOGGER.warning(
            "BeAlertFetcher.async_update: finished fetch, %d alerts parsed",
            len(self.alerts),
        )

    def alerts_affecting_point(
        self, lon: float | None, lat: float | None
    ) -> list[dict]:
        """Return list of alerts whose polygons contain the given point."""
        if lat is None or lon is None:
            return []
        point = shapely.geometry.Point(lon, lat)
        matches: list[dict] = []
        for alert in self.alerts:
            for poly in alert.get("polygons", []):
                try:
                    if poly.contains(point):
                        matches.append(alert)
                        break
                except (shapely.errors.ShapelyError, ValueError):
                    _LOGGER.warning(
                        "BeAlertFetcher: polygon contains() failed",
                        exc_info=True,
                    )
        return matches
