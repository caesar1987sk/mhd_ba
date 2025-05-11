"""Helper functions for the MHD BA integration."""

from .const import DIRECTION_ALL, DIRECTION_HERE


def generate_name(stop_id: str, filter_lines: list[str], direction: str) -> str:
    """Generate a readable name for the entity based on stop ID, filtered lines, and direction.

    This function creates a consistent name used for both config entries and entities.
    """
    # Start with base name using stop_id
    name = f"Bus Stop {stop_id}"

    # Add filtered lines if present
    if filter_lines:
        name += f" (Lines: {', '.join(sorted(filter_lines))})"

    # Add direction info if not the default "all"
    if direction != DIRECTION_ALL:
        direction_label = (
            "direction here" if direction == DIRECTION_HERE else "direction there"
        )
        name += f" {direction_label}"

    return name


def generate_unique_id(stop_id: str, filter_lines: list[str], direction: str) -> str:
    """Generate a unique ID combining stop ID, filtered lines, and direction."""
    # Start with stop_id as base
    unique_id_parts = [stop_id]

    # Add sorted lines if present
    if filter_lines:
        # Sort to ensure consistent IDs regardless of input order
        sorted_lines = sorted(filter_lines)
        unique_id_parts.append("-".join(sorted_lines))

    # Add direction if it's not the default "all"
    if direction != DIRECTION_ALL:
        unique_id_parts.append(direction)

    return "_".join(unique_id_parts)
