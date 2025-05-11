"""Sensor platform for MHD BA integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .config_flow import generate_unique_id
from .const import (
    CONF_DIRECTION,
    CONF_FILTER_LINES,
    CONF_MAX_DEPARTURES,
    CONF_STOP_ID,
    DIRECTION_ALL,
    DIRECTION_HERE,
    DOMAIN,
)
from .coordinator import MhdBaDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class MhdBaSensorEntityDescription(SensorEntityDescription):
    """Class describing MHD BA sensor entities."""


SENSOR_TYPES: tuple[MhdBaSensorEntityDescription, ...] = (
    MhdBaSensorEntityDescription(
        key="departures",
        name="Departures",
        icon="mdi:bus-clock",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the MHD BA sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        MhdBaDeparturesSensor(
            coordinator=coordinator,
            entity_description=description,
            entry=entry,
            max_departures=entry.data.get(CONF_MAX_DEPARTURES, 10),
            filter_lines=entry.data.get(CONF_FILTER_LINES, []),
        )
        for description in SENSOR_TYPES
    )


class MhdBaDeparturesSensor(
    CoordinatorEntity[MhdBaDataUpdateCoordinator], SensorEntity
):
    """Representation of a MHD BA departures sensor."""

    entity_description: MhdBaSensorEntityDescription

    def __init__(
        self,
        coordinator: MhdBaDataUpdateCoordinator,
        entity_description: MhdBaSensorEntityDescription,
        entry: ConfigEntry,
        max_departures: int,
        filter_lines: list[str],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = entity_description

        # Get direction from entry data
        self._direction = entry.data.get(CONF_DIRECTION, DIRECTION_ALL)

        # Generate unique ID using the same function as in config_flow
        stop_id = entry.data.get(CONF_STOP_ID)
        base_unique_id = generate_unique_id(stop_id, filter_lines, self._direction)
        self._attr_unique_id = f"{base_unique_id}_{entity_description.key}"

        stop_name = (
            self.coordinator.data.get("stop_name")
            if self.coordinator.data
            and self.coordinator.data.get("stop_name") is not None
            else stop_id
        )

        # Create a more descriptive name that includes filtered lines if any
        name = f"Bus Stop {stop_name} {entity_description.name}"
        if filter_lines:
            name += f" (Lines: {', '.join(filter_lines)})"

        # Add direction to the name if it's not "all"
        if self._direction != DIRECTION_ALL:
            direction_name = (
                "direction here"
                if self._direction == DIRECTION_HERE
                else "direction there"
            )
            name += f" {direction_name}"

        self._attr_name = name

        self._stop_id = self.coordinator.stop_id
        self._max_departures = max_departures
        self._filter_lines = filter_lines

    def _calculate_departure_time(
        self, planned_timestamp: int, delay_minutes: int
    ) -> int:
        """Calculate the actual departure time considering delay.

        Args:
            planned_timestamp: The planned departure timestamp in seconds
            delay_minutes: The delay in minutes

        Returns:
            The calculated departure time in seconds

        """
        return int(planned_timestamp) + (int(delay_minutes) * 60)

    def _calculate_time_until_departure(self, departure_calculated: int) -> int | None:
        """Calculate the time remaining until departure.

        Args:
            departure_calculated: The calculated departure time in seconds

        Returns:
            Time until departure in seconds or None if invalid

        """
        if departure_calculated is None:
            return None

        current_timestamp = int(dt_util.utcnow().timestamp())
        return departure_calculated - current_timestamp

    @property
    def native_value(self) -> StateType:
        """Return the next departure info in format 'line -> destination in X min'."""
        if not self.coordinator.data or "departures" not in self.coordinator.data:
            return None

        # Apply both line and direction filtering
        filtered_departures = [
            departure
            for departure in self.coordinator.data["departures"]
            if self._should_include_departure(departure)
        ]

        # No departures available
        if not filtered_departures:
            return None

        # Get the next departure (first in the list)
        next_departure = filtered_departures[0]

        # Get required data for the formatted string
        line = (
            next_departure.get("timeTableTrip", {})
            .get("timeTableLine", {})
            .get("line", "Unknown")
        )
        destination = next_departure.get("timeTableTrip", {}).get(
            "destinationStopName", "Unknown"
        )

        # Calculate minutes until departure
        planned_timestamp = next_departure.get("plannedDepartureTimestamp")
        delay_minutes = next_departure.get("delayMinutes", 0)

        if not planned_timestamp:
            return f"{line} -> {destination}"

        # Calculate actual departure time considering delay
        departure_calculated = self._calculate_departure_time(
            planned_timestamp, delay_minutes
        )
        time_until_departure_seconds = self._calculate_time_until_departure(
            departure_calculated
        )

        if time_until_departure_seconds is None or time_until_departure_seconds <= 0:
            minutes_until_departure = 0
        else:
            minutes_until_departure = int(time_until_departure_seconds / 60)

        # Format the return value
        return f"{line} -> {destination} in {minutes_until_departure} min"

    def _should_include_departure(self, departure: dict[str, Any]) -> bool:
        """Check if departure should be included based on filter_lines and direction.

        Args:
            departure: The departure data

        Returns:
            True if the departure should be included, False otherwise

        """
        # First check line filter
        if self._filter_lines:
            line = (
                departure.get("timeTableTrip", {}).get("timeTableLine", {}).get("line")
            )
            if not line or line not in self._filter_lines:
                return False

        # Then check direction filter
        if self._direction != DIRECTION_ALL:
            departure_direction = departure.get("timeTableTrip", {}).get(
                "ezTripDirection"
            )

            # If direction is "here", only include arrivals
            if self._direction == DIRECTION_HERE and departure_direction != "here":
                return False

            # If direction is "there", only include departures
            if self._direction != DIRECTION_HERE and departure_direction == "here":
                return False

        return True

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes: dict[str, Any] = {
            "last_update": self.coordinator.data.get("last_update"),
            "departures": [],
            "stop_name": None,
            "stopping_lines": [],
            "max_departures": self._max_departures,
            "filter_lines": self._filter_lines,
            "direction": self.coordinator.direction,
        }

        if not self.coordinator.data:
            return attributes

        # Add the stop name if available
        if self.coordinator.data.get("stop_name"):
            attributes["stop_name"] = self.coordinator.data["stop_name"]

        # Add the stopping lines if available
        if self.coordinator.data.get("stopping_lines"):
            attributes["stopping_lines"] = self.coordinator.data["stopping_lines"]

        # Add departure information
        if "departures" in self.coordinator.data:
            attributes["departures"] = []

            # Filter departures using the _should_include_departure method
            filtered_departures = [
                departure
                for departure in self.coordinator.data["departures"]
                if self._should_include_departure(departure)
            ]

            # Apply max_departures limit
            for departure in filtered_departures[: self._max_departures]:
                planned_timestamp = departure.get("plannedDepartureTimestamp")
                delay_minutes = departure.get("delayMinutes", 0)

                # Calculate departure_calculated once to reuse
                departure_calculated = None
                time_until_calculated_departure = None
                if planned_timestamp:
                    departure_calculated = self._calculate_departure_time(
                        planned_timestamp, delay_minutes
                    )
                    time_until_calculated_departure = (
                        self._calculate_time_until_departure(departure_calculated)
                    )

                attributes["departures"].append(
                    {
                        "line": departure.get("timeTableTrip", {})
                        .get("timeTableLine", {})
                        .get("line", "Unknown"),
                        "planed_departure": planned_timestamp,
                        "planed_departure_formatted": dt_util.as_local(
                            datetime.fromtimestamp(
                                planned_timestamp or 0,
                                tz=dt_util.UTC,
                            )
                        ).strftime("%H:%M")
                        if planned_timestamp
                        else None,
                        "delay": delay_minutes,
                        "departute_calculated": departure_calculated,
                        "calculated_departure_formatted": dt_util.as_local(
                            datetime.fromtimestamp(
                                departure_calculated or 0,
                                tz=dt_util.UTC,
                            )
                        ).strftime("%H:%M")
                        if departure_calculated
                        else None,
                        "seconds_until_departure": time_until_calculated_departure
                        if departure_calculated
                        else None,
                        "minutes_until_departure": int(
                            time_until_calculated_departure / 60
                        )
                        if departure_calculated and time_until_calculated_departure
                        else None,
                        "destination": departure.get("timeTableTrip", {}).get(
                            "destinationStopName", "Unknown"
                        ),
                        "platform": departure.get("platformNumber", None),
                        "direction": departure.get("timeTableTrip", {}).get(
                            "ezTripDirection", None
                        ),
                    }
                )
        return attributes
