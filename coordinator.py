"""Data update coordinator for MHD BA integration."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_TIMEOUT,
    DEFAULT_CITY_ID,
    DEFAULT_FILTER,
    DEFAULT_SCAN_INTERVAL,
    DEPARTURES_API_ENDPOINT,
    DOMAIN,
    STOP_INFO_API_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


class MhdBaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching MHD BA data."""

    def __init__(
        self, hass: HomeAssistant, session: aiohttp.ClientSession, stop_id: str
    ) -> None:
        """Initialize the coordinator."""
        self.session = session
        self.stop_id = stop_id
        self.stop_name: str | None = None
        self.stopping_lines: list[str] = []
        self.last_update: str = ""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via API."""
        try:
            # Fetch stop info if we don't have it yet
            if self.stop_name is None:
                await self._fetch_stop_info()

            return {
                "departures": await self._fetch_departures(),
                "stop_name": self.stop_name,
                "stopping_lines": self.stopping_lines,
                "last_update": self.last_update,
            }
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    async def _fetch_stop_info(self) -> None:
        """Fetch stop information from the MHD BA API."""
        url = f"{STOP_INFO_API_ENDPOINT}?ids={self.stop_id}"

        _LOGGER.debug("Fetching stop info for stop ID %s", self.stop_id)

        try:
            async with self.session.get(
                url,
                timeout=API_TIMEOUT,
            ) as response:
                if response.status != 200:
                    _LOGGER.error(
                        "Error fetching stop info: %s",
                        response.status,
                    )
                    return

                response_json = await response.json()

                if response_json.get("status") != "ok" or not response_json.get(
                    "stops"
                ):
                    _LOGGER.error("Invalid stop info response format")
                    return

                stop_data = response_json["stops"][0]
                self.stop_name = stop_data.get("stopName")
                self.stopping_lines = stop_data.get("ezLines", [])

                _LOGGER.debug(
                    "Fetched stop info - name: %s, lines: %s",
                    self.stop_name,
                    self.stopping_lines,
                )
        except aiohttp.ClientError as err:
            _LOGGER.error("Failed to fetch stop info: %s", err)

    async def _fetch_departures(self) -> dict[str, Any]:
        """Fetch departure data from the MHD BA API."""
        # Format current date and time in the required format
        now = dt_util.now()
        # Format as YYYY-MM-DD+HH:MM+TZTZ (no colon in timezone)
        formatted_date = now.strftime("%Y-%m-%d+%H:%M").replace(
            ":", "%3A"
        ) + now.strftime("%z").replace(":", "").replace("+", "%2B")

        payload = {
            "stopID": self.stop_id,
            "date": formatted_date,
            "filter": DEFAULT_FILTER,
            "cityID": DEFAULT_CITY_ID,
        }

        _LOGGER.debug(
            "Making request to MHD BA API for stop ID %s with date %s",
            self.stop_id,
            formatted_date,
        )

        url_encoded_data = "&".join([f"{k}={v}" for k, v in payload.items()])
        _LOGGER.debug("Request payload: %s", url_encoded_data)

        async with self.session.post(
            DEPARTURES_API_ENDPOINT,
            data=url_encoded_data,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as response:
            if response.status != 200:
                _LOGGER.error(
                    "Error fetching departures: %s",
                    response.status,
                )
                raise UpdateFailed(f"Invalid response from API: {response.status}")

            response_json = await response.json()

            # Check if we got a valid response with departures key
            if "departures" not in response_json:
                _LOGGER.error("Invalid response format, missing departures")
                return {[]}
            self.last_update = dt_util.now().strftime("%d.%m.%Y %H:%M:%S")
            return response_json["departures"]
