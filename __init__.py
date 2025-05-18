"""Integration for MHD BA bus departures."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_DIRECTION, CONF_STOP_ID, DEFAULT_DIRECTION, DOMAIN
from .coordinator import MhdBaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MHD BA from a config entry."""
    stop_id = entry.data[CONF_STOP_ID]
    direction = entry.data.get(CONF_DIRECTION, DEFAULT_DIRECTION)
    session = async_get_clientsession(hass)

    coordinator = MhdBaDataUpdateCoordinator(hass, session, stop_id, direction)

    # Fetch initial data to validate connection
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady(f"Failed to initialize MHD BA for stop ID {stop_id}")

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the MHD BA component."""
    # Just to make sure the component is setup properly
    hass.data.setdefault(DOMAIN, {})
    return True
