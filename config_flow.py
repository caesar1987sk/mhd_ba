"""Config flow for MHD BA integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow, FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_TIMEOUT,
    CONF_FILTER_LINES,
    CONF_MAX_DEPARTURES,
    CONF_STOP_ID,
    DEFAULT_MAX_DEPARTURES,
    DOMAIN,
    STOP_INFO_API_ENDPOINT,
)

_LOGGER = logging.getLogger(__name__)


async def validate_stop_id(hass: HomeAssistant, stop_id: str) -> None:
    """Validate stop_id by calling the API."""
    session = async_get_clientsession(hass)

    try:
        async with session.get(
            url=f"{STOP_INFO_API_ENDPOINT}?ids={stop_id}", timeout=API_TIMEOUT
        ) as response:
            if response.status != 200:
                raise CannotConnect

            data = await response.json()

            if (
                not data.get("stops")
                or not data.get("stops")[0]
                or not data.get("stops")[0].get("stopID")
                or str(data.get("stops")[0].get("stopID")) != stop_id
            ):
                raise InvalidStopId

    except aiohttp.ClientError as err:
        _LOGGER.error("Error connecting to API: %s", err)
        raise CannotConnect from err


def parse_filter_lines(filter_lines: str) -> list[str]:
    """Parse the filter_lines input into a list of line numbers."""
    if not filter_lines:
        return []

    # Split by comma or semicolon
    lines = re.split(r"[,;]", filter_lines)
    # Strip whitespace and remove empty entries
    return [line.strip() for line in lines if line.strip()]


def generate_unique_id(stop_id: str, filter_lines: list[str]) -> str:
    """Generate a unique ID combining stop ID and filtered lines."""
    if not filter_lines:
        return stop_id

    # Sort to ensure consistent IDs regardless of input order
    sorted_lines = sorted(filter_lines)
    return f"{stop_id}_{'-'.join(sorted_lines)}"


class MhdBaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MHD BA."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                stop_id = user_input[CONF_STOP_ID]

                # Validate the stop ID with the API
                await validate_stop_id(self.hass, stop_id)

                # Parse filter lines
                filter_lines = []
                if user_input.get(CONF_FILTER_LINES):
                    filter_lines = parse_filter_lines(user_input[CONF_FILTER_LINES])
                    user_input[CONF_FILTER_LINES] = filter_lines

                # Generate unique ID combining stop_id and filter_lines
                unique_id = generate_unique_id(stop_id, filter_lines)

                # Check if this combination is already configured
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Create entry title based on stop ID and filtered lines
                title = f"Bus Stop {stop_id}"
                if filter_lines:
                    title += f" (Lines: {', '.join(filter_lines)})"

                return self.async_create_entry(
                    title=title,
                    data=user_input,
                )
            except AbortFlow:
                # Let the abort flow exception propagate to properly show "already configured" message
                raise
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidStopId:
                errors["base"] = "invalid_stop_id"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=config_entries.vol.Schema(
                {
                    config_entries.vol.Required(CONF_STOP_ID): str,
                    config_entries.vol.Required(
                        CONF_MAX_DEPARTURES, default=DEFAULT_MAX_DEPARTURES
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1000)),
                    config_entries.vol.Optional(
                        CONF_FILTER_LINES, description={"suggested_value": ""}
                    ): str,
                }
            ),
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidStopId(HomeAssistantError):
    """Error to indicate the stop ID is invalid."""
