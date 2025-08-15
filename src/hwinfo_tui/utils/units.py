"""Unit detection and filtering utilities."""

from __future__ import annotations

import logging
import re

from ..data.sensors import Sensor, SensorGroup

logger = logging.getLogger(__name__)


class UnitFilter:
    """Handles unit detection and filtering logic for sensors."""

    def __init__(self, max_units: int = 2) -> None:
        """Initialize the unit filter."""
        self.max_units = max_units
        self.allowed_units: set[str | None] = set()
        self.excluded_sensors: list[tuple[str, str | None, str]] = []

    @staticmethod
    def extract_unit(sensor_name: str) -> str | None:
        """Extract unit from sensor name (e.g., 'CPU Temperature [°C]' -> '°C')."""
        # Look for unit in brackets
        match = re.search(r'\[([^\]]+)\]', sensor_name)
        if match:
            unit = match.group(1)
            # Clean up common unit representations
            unit = unit.strip()
            # Normalize some common units
            unit_mapping = {
                'C': '°C',
                'degC': '°C',
                'Celsius': '°C',
                'percent': '%',
                'pct': '%',
                'Watts': 'W',
                'watts': 'W',
                'Megahertz': 'MHz',
                'megahertz': 'MHz',
                'Mhz': 'MHz',
                'mhz': 'MHz',
                'Volts': 'V',
                'volts': 'V',
                'volt': 'V',
                'Amperes': 'A',
                'amperes': 'A',
                'amps': 'A',
                'Amp': 'A',
                'Gigabytes': 'GB',
                'gigabytes': 'GB',
                'gb': 'GB',
                'Megabytes': 'MB',
                'megabytes': 'MB',
                'mb': 'MB',
                'RPM': 'rpm',
                'revolutions per minute': 'rpm',
                'FPS': 'fps',
                'frames per second': 'fps',
                'milliseconds': 'ms',
                'ms': 'ms',
                'seconds': 's',
                'sec': 's',
            }
            return unit_mapping.get(unit, unit)
        return None

    def filter_sensors_by_unit(self, sensor_names: list[str]) -> tuple[list[str], list[str]]:
        """
        Filter sensors based on unit compatibility.

        Args:
            sensor_names: List of sensor names to filter

        Returns:
            Tuple of (accepted_sensors, excluded_sensors_with_reasons)
        """
        self.allowed_units.clear()
        self.excluded_sensors.clear()

        accepted_sensors: list[str] = []
        excluded_sensors_with_reasons: list[str] = []

        for sensor_name in sensor_names:
            unit = self.extract_unit(sensor_name)

            # First sensor is always accepted
            if not self.allowed_units:
                self.allowed_units.add(unit)
                accepted_sensors.append(sensor_name)
                continue

            # Check if this unit is already allowed
            if unit in self.allowed_units:
                accepted_sensors.append(sensor_name)
                continue

            # Check if we can add a new unit
            if len(self.allowed_units) < self.max_units:
                self.allowed_units.add(unit)
                accepted_sensors.append(sensor_name)
                continue

            # Exclude this sensor
            reason = self._create_exclusion_reason(unit)
            self.excluded_sensors.append((sensor_name, unit, reason))
            excluded_sensors_with_reasons.append(f"Excluded sensor '{sensor_name}' with unit [{unit}] - {reason}")

        return accepted_sensors, excluded_sensors_with_reasons

    def _create_exclusion_reason(self, excluded_unit: str | None) -> str:
        """Create a human-readable exclusion reason."""
        allowed_list = [f"[{unit}]" if unit else "[no unit]" for unit in self.allowed_units]

        if len(allowed_list) == 1:
            return f"chart limited to unit {allowed_list[0]}"
        else:
            return f"chart limited to units {' and '.join(allowed_list)}"

    def create_sensor_groups(self, sensors: dict[str, Sensor]) -> list[SensorGroup]:
        """Group sensors by their units."""
        unit_groups: dict[str | None, list[Sensor]] = {}

        for sensor in sensors.values():
            unit = sensor.info.unit
            if unit not in unit_groups:
                unit_groups[unit] = []
            unit_groups[unit].append(sensor)

        # Create SensorGroup objects
        groups = []
        for unit, sensor_list in unit_groups.items():
            group = SensorGroup(unit=unit)
            for sensor in sensor_list:
                group.add_sensor(sensor)
            groups.append(group)

        # Sort groups by unit for consistent display
        groups.sort(key=lambda g: g.unit or "")

        return groups

    def get_allowed_units(self) -> set[str | None]:
        """Get the set of allowed units."""
        return self.allowed_units.copy()

    def get_excluded_sensors(self) -> list[tuple[str, str | None, str]]:
        """Get list of excluded sensors with their reasons."""
        return self.excluded_sensors.copy()


def validate_sensor_compatibility(sensor_names: list[str], max_units: int = 2) -> tuple[list[str], list[str], set[str | None]]:
    """
    Validate sensor compatibility and return filtered results.

    Args:
        sensor_names: List of sensor names to validate
        max_units: Maximum number of different units allowed

    Returns:
        Tuple of (accepted_sensors, exclusion_messages, allowed_units)
    """
    unit_filter = UnitFilter(max_units=max_units)
    accepted, excluded_messages = unit_filter.filter_sensors_by_unit(sensor_names)
    allowed_units = unit_filter.get_allowed_units()

    return accepted, excluded_messages, allowed_units


def get_unit_display_info(units: set[str | None]) -> dict[str, str]:
    """Get display information for units."""
    unit_info = {}

    for unit in units:
        if unit is None:
            unit_info["no_unit"] = {
                "display": "No Unit",
                "short": "",
                "color": "white"
            }
        else:
            # Assign colors based on unit type
            color_map = {
                "°C": "red",
                "%": "green",
                "W": "yellow",
                "V": "blue",
                "A": "cyan",
                "MHz": "magenta",
                "MB": "bright_blue",
                "GB": "bright_blue",
                "rpm": "bright_green",
                "fps": "bright_yellow",
                "ms": "bright_red",
                "s": "bright_red"
            }

            unit_info[unit] = {
                "display": unit,
                "short": unit,
                "color": color_map.get(unit, "white")
            }

    return unit_info


def suggest_sensor_names(available_sensors: list[str], query: str, limit: int = 5) -> list[str]:
    """Suggest sensor names based on partial input."""
    query_lower = query.lower()
    suggestions = []

    # Exact matches first
    for sensor in available_sensors:
        if query_lower == sensor.lower():
            suggestions.append(sensor)

    # Starts with matches
    for sensor in available_sensors:
        if sensor.lower().startswith(query_lower) and sensor not in suggestions:
            suggestions.append(sensor)
            if len(suggestions) >= limit:
                break

    # Contains matches
    for sensor in available_sensors:
        if query_lower in sensor.lower() and sensor not in suggestions:
            suggestions.append(sensor)
            if len(suggestions) >= limit:
                break

    return suggestions
