"""Statistics calculation utilities for sensor data."""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..data.sensors import Sensor, SensorReading


@dataclass
class SensorStats:
    """Statistics for a single sensor."""
    
    sensor_name: str
    unit: Optional[str]
    last: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    avg_value: Optional[float]
    p95_value: Optional[float]
    sample_count: int
    
    def __post_init__(self) -> None:
        """Format values after initialization."""
        # Round float values to appropriate precision
        if self.last is not None:
            self.last = round(self.last, 2)
        if self.min_value is not None:
            self.min_value = round(self.min_value, 2)
        if self.max_value is not None:
            self.max_value = round(self.max_value, 2)
        if self.avg_value is not None:
            self.avg_value = round(self.avg_value, 2)
        if self.p95_value is not None:
            self.p95_value = round(self.p95_value, 2)
    
    @property
    def formatted_last(self) -> str:
        """Get formatted last value."""
        if self.last is None:
            return "N/A"
        return self._format_value(self.last)
    
    @property
    def formatted_min(self) -> str:
        """Get formatted minimum value."""
        if self.min_value is None:
            return "N/A"
        return self._format_value(self.min_value)
    
    @property
    def formatted_max(self) -> str:
        """Get formatted maximum value."""
        if self.max_value is None:
            return "N/A"
        return self._format_value(self.max_value)
    
    @property
    def formatted_avg(self) -> str:
        """Get formatted average value."""
        if self.avg_value is None:
            return "N/A"
        return self._format_value(self.avg_value)
    
    @property
    def formatted_p95(self) -> str:
        """Get formatted 95th percentile value."""
        if self.p95_value is None:
            return "N/A"
        return self._format_value(self.p95_value)
    
    def _format_value(self, value: float) -> str:
        """Format a value based on its magnitude."""
        # Handle special cases
        if value == 0.0:
            return "0"
        
        abs_value = abs(value)
        
        # Very small values - show more precision
        if abs_value < 0.01:
            return f"{value:.4f}"
        # Small values - show 3 decimal places
        elif abs_value < 1.0:
            return f"{value:.3f}"
        # Medium values - show 2 decimal places
        elif abs_value < 100.0:
            return f"{value:.2f}"
        # Large values - show 1 decimal place
        elif abs_value < 10000.0:
            return f"{value:.1f}"
        # Very large values - show as integer
        else:
            return f"{int(value)}"
    
    @property
    def display_unit(self) -> str:
        """Get display unit or empty string."""
        return self.unit or ""


class StatsCalculator:
    """Calculator for sensor statistics."""
    
    def __init__(self, time_window_seconds: int = 300) -> None:
        """Initialize the statistics calculator."""
        self.time_window_seconds = time_window_seconds
    
    def calculate_sensor_stats(self, sensor: Sensor) -> SensorStats:
        """Calculate statistics for a single sensor."""
        # Get readings within the time window
        readings = sensor.get_readings_in_window(self.time_window_seconds)
        
        if not readings:
            return SensorStats(
                sensor_name=sensor.info.name,
                unit=sensor.info.unit,
                last=None,
                min_value=None,
                max_value=None,
                avg_value=None,
                p95_value=None,
                sample_count=0
            )
        
        values = [r.value for r in readings]
        
        # Calculate basic statistics
        last = readings[-1].value if readings else None
        min_value = min(values)
        max_value = max(values)
        avg_value = statistics.mean(values)
        
        # Calculate 95th percentile
        p95_value = self._calculate_percentile(values, 95)
        
        return SensorStats(
            sensor_name=sensor.info.name,
            unit=sensor.info.unit,
            last=last,
            min_value=min_value,
            max_value=max_value,
            avg_value=avg_value,
            p95_value=p95_value,
            sample_count=len(values)
        )
    
    def calculate_all_stats(self, sensors: Dict[str, Sensor]) -> Dict[str, SensorStats]:
        """Calculate statistics for all sensors."""
        stats = {}
        
        for name, sensor in sensors.items():
            stats[name] = self.calculate_sensor_stats(sensor)
        
        return stats
    
    def _calculate_percentile(self, values: List[float], percentile: float) -> Optional[float]:
        """Calculate the specified percentile of values."""
        if not values:
            return None
        
        if len(values) == 1:
            return values[0]
        
        # Sort values
        sorted_values = sorted(values)
        
        # Calculate index
        index = (percentile / 100.0) * (len(sorted_values) - 1)
        
        # Handle exact index
        if index == int(index):
            return sorted_values[int(index)]
        
        # Interpolate between values
        lower_index = int(index)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)
        
        if lower_index == upper_index:
            return sorted_values[lower_index]
        
        # Linear interpolation
        fraction = index - lower_index
        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
        
        return lower_value + fraction * (upper_value - lower_value)
    
    def get_color_for_value(self, stats: SensorStats, value: Optional[float]) -> str:
        """Get color coding for a value based on thresholds."""
        if value is None:
            return "white"
        
        unit = stats.unit
        
        # Temperature thresholds
        if unit in ["°C", "C"]:
            if value >= 85:
                return "red"
            elif value >= 75:
                return "yellow"
            else:
                return "green"
        
        # Percentage thresholds
        elif unit == "%":
            if value >= 90:
                return "red"
            elif value >= 80:
                return "yellow"
            else:
                return "green"
        
        # Power thresholds (rough guidelines)
        elif unit == "W":
            if value >= 200:
                return "red"
            elif value >= 100:
                return "yellow"
            else:
                return "green"
        
        # Voltage thresholds (very rough guidelines)
        elif unit == "V":
            if value >= 1.5 or value <= 0.8:
                return "yellow"
            else:
                return "green"
        
        # Default color
        else:
            return "white"
    
    def get_threshold_status(self, stats: SensorStats) -> str:
        """Get threshold status for a sensor."""
        if stats.last is None:
            return "unknown"
        
        color = self.get_color_for_value(stats, stats.last)
        
        if color == "red":
            return "critical"
        elif color == "yellow":
            return "warning"
        else:
            return "normal"


def format_time_window(seconds: int) -> str:
    """Format time window duration for display."""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {minutes}m"


def calculate_data_rate(readings: List[SensorReading]) -> float:
    """Calculate data rate (readings per second) for a list of readings."""
    if len(readings) < 2:
        return 0.0
    
    time_span = (readings[-1].timestamp - readings[0].timestamp).total_seconds()
    
    if time_span <= 0:
        return 0.0
    
    return (len(readings) - 1) / time_span