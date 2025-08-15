"""Data models for sensor information and readings."""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SensorReading:
    """A single sensor reading with timestamp and value."""

    timestamp: datetime
    value: float

    def __post_init__(self) -> None:
        """Validate the reading after initialization."""
        if not isinstance(self.value, (int, float)):
            raise ValueError(f"Sensor value must be numeric, got {type(self.value)}")
        self.value = float(self.value)


@dataclass
class SensorInfo:
    """Information about a sensor including its unit and metadata."""

    name: str
    unit: str | None = None
    color: str | None = None

    def __post_init__(self) -> None:
        """Extract unit from sensor name if not provided."""
        if self.unit is None:
            self.unit = self.extract_unit_from_name(self.name)

    @staticmethod
    def extract_unit_from_name(name: str) -> str | None:
        """Extract unit from sensor name (e.g., 'CPU Temperature [°C]' -> '°C')."""
        match = re.search(r'\[([^\]]+)\]', name)
        return match.group(1) if match else None

    @property
    def display_name(self) -> str:
        """Get display name without unit suffix."""
        if self.unit:
            pattern = r'\s*\[' + re.escape(self.unit) + r'\]'
            return re.sub(pattern, '', self.name).strip()
        return self.name


@dataclass
class Sensor:
    """A sensor with its metadata and historical readings."""

    info: SensorInfo
    readings: deque[SensorReading] = field(default_factory=lambda: deque(maxlen=3600))
    max_readings: int = 3600

    def __post_init__(self) -> None:
        """Initialize the sensor after creation."""
        self.readings = deque(maxlen=self.max_readings)

    def add_reading(self, timestamp: datetime, value: Any) -> None:
        """Add a new reading to the sensor."""
        try:
            # Handle missing or invalid values
            if value is None or value == '' or (isinstance(value, str) and value.strip() == ''):
                return

            # Convert string values to float
            if isinstance(value, str):
                value = value.strip()
                if value.lower() in ('yes', 'no'):
                    value = 1.0 if value.lower() == 'yes' else 0.0
                else:
                    value = float(value)

            reading = SensorReading(timestamp=timestamp, value=value)
            self.readings.append(reading)

        except (ValueError, TypeError):
            # Skip invalid readings silently
            pass

    @property
    def latest_value(self) -> float | None:
        """Get the most recent sensor value."""
        if not self.readings:
            return None
        latest_reading = max(self.readings, key=lambda r: r.timestamp)
        return latest_reading.value

    @property
    def latest_timestamp(self) -> datetime | None:
        """Get the most recent timestamp."""
        if not self.readings:
            return None
        return max(reading.timestamp for reading in self.readings)

    @property
    def values(self) -> list[float]:
        """Get all sensor values as a list."""
        return [reading.value for reading in self.readings]

    @property
    def timestamps(self) -> list[datetime]:
        """Get all timestamps as a list."""
        return [reading.timestamp for reading in self.readings]

    def get_readings_in_window(self, seconds: int) -> list[SensorReading]:
        """Get readings within the last N seconds."""
        if not self.readings:
            return []

        cutoff_time = self.latest_timestamp
        if cutoff_time is None:
            return []

        cutoff_time = cutoff_time.replace(microsecond=0)  # Remove microseconds for calculation
        cutoff_timestamp = cutoff_time.timestamp() - seconds

        return [
            reading for reading in self.readings
            if reading.timestamp.timestamp() >= cutoff_timestamp
        ]

    def clear_readings(self) -> None:
        """Clear all readings from the sensor."""
        self.readings.clear()


@dataclass
class SensorGroup:
    """A group of sensors with the same unit."""

    unit: str | None
    sensors: list[Sensor] = field(default_factory=list)

    def add_sensor(self, sensor: Sensor) -> None:
        """Add a sensor to the group."""
        if sensor.info.unit == self.unit:
            self.sensors.append(sensor)
        else:
            raise ValueError(f"Sensor unit '{sensor.info.unit}' doesn't match group unit '{self.unit}'")

    @property
    def sensor_names(self) -> list[str]:
        """Get names of all sensors in the group."""
        return [sensor.info.name for sensor in self.sensors]

    @property
    def display_names(self) -> list[str]:
        """Get display names of all sensors in the group."""
        return [sensor.info.display_name for sensor in self.sensors]
