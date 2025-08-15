"""Tests for statistics calculation functionality."""

from datetime import datetime, timedelta

from hwinfo_tui.data.sensors import Sensor, SensorInfo, SensorReading
from hwinfo_tui.utils.stats import (
    SensorStats,
    StatsCalculator,
    calculate_data_rate,
    format_time_window,
)


class TestSensorStats:
    """Test SensorStats dataclass."""

    def test_stats_creation(self):
        """Test creating sensor statistics."""
        stats = SensorStats(
            sensor_name="CPU Temperature [°C]",
            unit="°C",
            last=45.6,
            min_value=42.0,
            max_value=48.0,
            avg_value=45.0,
            p95_value=47.0,
            sample_count=100,
        )

        assert stats.sensor_name == "CPU Temperature [°C]"
        assert stats.unit == "°C"
        assert stats.last == 45.6  # Should be rounded to 2 decimal places
        assert stats.sample_count == 100

    def test_value_rounding(self):
        """Test automatic value rounding."""
        stats = SensorStats(
            sensor_name="Test",
            unit="°C",
            last=45.123456,
            min_value=42.987654,
            max_value=48.555555,
            avg_value=45.111111,
            p95_value=47.444444,
            sample_count=10,
        )

        assert stats.last == 45.12
        assert stats.min_value == 42.99
        assert stats.max_value == 48.56
        assert stats.avg_value == 45.11
        assert stats.p95_value == 47.44

    def test_formatted_values(self):
        """Test formatted value output."""
        stats = SensorStats(
            sensor_name="Test",
            unit="°C",
            last=45.123,
            min_value=None,
            max_value=1000.0,
            avg_value=0.01,  # Use 0.01 instead of 0.001 to avoid rounding issues
            p95_value=99.9,
            sample_count=10,
        )

        assert stats.formatted_last == "45.12"
        assert stats.formatted_min == "N/A"
        assert stats.formatted_max == "1000.0"
        assert stats.formatted_avg == "0.010"  # Expect 0.010 instead of 0.0010
        assert stats.formatted_p95 == "99.90"

    def test_display_unit(self):
        """Test display unit property."""
        stats_with_unit = SensorStats("Test", "°C", 45.0, 40.0, 50.0, 45.0, 48.0, 10)
        assert stats_with_unit.display_unit == "°C"

        stats_no_unit = SensorStats("Test", None, 45.0, 40.0, 50.0, 45.0, 48.0, 10)
        assert stats_no_unit.display_unit == ""


class TestStatsCalculator:
    """Test StatsCalculator class."""

    def test_empty_sensor(self):
        """Test statistics calculation for empty sensor."""
        calculator = StatsCalculator()
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        stats = calculator.calculate_sensor_stats(sensor)

        assert stats.sensor_name == "CPU Temperature [°C]"
        assert stats.unit == "°C"
        assert stats.last is None
        assert stats.min_value is None
        assert stats.max_value is None
        assert stats.avg_value is None
        assert stats.p95_value is None
        assert stats.sample_count == 0

    def test_single_reading(self):
        """Test statistics calculation for sensor with single reading."""
        calculator = StatsCalculator(time_window_seconds=300)
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        timestamp = datetime.now()
        sensor.add_reading(timestamp, 45.0)

        stats = calculator.calculate_sensor_stats(sensor)

        assert stats.last == 45.0
        assert stats.min_value == 45.0
        assert stats.max_value == 45.0
        assert stats.avg_value == 45.0
        assert stats.p95_value == 45.0
        assert stats.sample_count == 1

    def test_multiple_readings(self):
        """Test statistics calculation for sensor with multiple readings."""
        calculator = StatsCalculator(time_window_seconds=300)
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        now = datetime.now()
        values = [40.0, 42.0, 45.0, 48.0, 50.0]

        for i, value in enumerate(values):
            timestamp = now - timedelta(seconds=i)
            sensor.add_reading(timestamp, value)

        stats = calculator.calculate_sensor_stats(sensor)

        assert stats.last == 50.0  # Last added reading (i=4, value=50.0)
        assert stats.min_value == 40.0
        assert stats.max_value == 50.0
        assert stats.avg_value == 45.0
        assert stats.sample_count == 5

    def test_time_window_filtering(self):
        """Test that statistics respect time window."""
        calculator = StatsCalculator(time_window_seconds=60)  # 1 minute window
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        now = datetime.now()

        # Add readings: some within window, some outside
        sensor.add_reading(now - timedelta(seconds=30), 45.0)  # Within window
        sensor.add_reading(now - timedelta(seconds=90), 100.0)  # Outside window
        sensor.add_reading(now - timedelta(seconds=10), 50.0)  # Within window

        stats = calculator.calculate_sensor_stats(sensor)

        # Should only include readings within the 60-second window
        assert stats.sample_count == 2
        assert stats.min_value == 45.0
        assert stats.max_value == 50.0

    def test_percentile_calculation(self):
        """Test percentile calculation."""
        calculator = StatsCalculator()

        # Test with known values
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

        # 95th percentile of 1-10 should be 9.55
        p95 = calculator._calculate_percentile(values, 95)
        assert abs(p95 - 9.55) < 0.01

        # 50th percentile (median) should be 5.5
        p50 = calculator._calculate_percentile(values, 50)
        assert abs(p50 - 5.5) < 0.01

    def test_percentile_edge_cases(self):
        """Test percentile calculation edge cases."""
        calculator = StatsCalculator()

        # Empty list
        assert calculator._calculate_percentile([], 95) is None

        # Single value
        assert calculator._calculate_percentile([42.0], 95) == 42.0

        # Two values
        result = calculator._calculate_percentile([40.0, 50.0], 50)
        assert result == 45.0  # Should interpolate

    def test_color_for_temperature(self):
        """Test color coding for temperature values."""
        calculator = StatsCalculator()

        temp_stats = SensorStats(
            "CPU Temp [°C]", "°C", 45.0, 40.0, 50.0, 45.0, 48.0, 10
        )

        # Normal temperature
        assert calculator.get_color_for_value(temp_stats, 70.0) == "green"

        # Warning temperature
        assert calculator.get_color_for_value(temp_stats, 80.0) == "yellow"

        # Critical temperature
        assert calculator.get_color_for_value(temp_stats, 90.0) == "red"

    def test_color_for_percentage(self):
        """Test color coding for percentage values."""
        calculator = StatsCalculator()

        usage_stats = SensorStats(
            "CPU Usage [%]", "%", 45.0, 40.0, 50.0, 45.0, 48.0, 10
        )

        # Normal usage
        assert calculator.get_color_for_value(usage_stats, 70.0) == "green"

        # Warning usage
        assert calculator.get_color_for_value(usage_stats, 85.0) == "yellow"

        # Critical usage
        assert calculator.get_color_for_value(usage_stats, 95.0) == "red"

    def test_threshold_status(self):
        """Test threshold status calculation."""
        calculator = StatsCalculator()

        # Normal status
        normal_stats = SensorStats(
            "CPU Temp [°C]", "°C", 70.0, 65.0, 75.0, 70.0, 73.0, 10
        )
        assert calculator.get_threshold_status(normal_stats) == "normal"

        # Warning status
        warning_stats = SensorStats(
            "CPU Temp [°C]", "°C", 80.0, 75.0, 85.0, 80.0, 83.0, 10
        )
        assert calculator.get_threshold_status(warning_stats) == "warning"

        # Critical status
        critical_stats = SensorStats(
            "CPU Temp [°C]", "°C", 90.0, 85.0, 95.0, 90.0, 93.0, 10
        )
        assert calculator.get_threshold_status(critical_stats) == "critical"

        # Unknown status (no data)
        unknown_stats = SensorStats(
            "CPU Temp [°C]", "°C", None, None, None, None, None, 0
        )
        assert calculator.get_threshold_status(unknown_stats) == "unknown"


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_time_window(self):
        """Test time window formatting."""
        assert format_time_window(30) == "30s"
        assert format_time_window(60) == "1m"
        assert format_time_window(90) == "1m"
        assert format_time_window(3600) == "1h"
        assert format_time_window(3660) == "1h 1m"

    def test_calculate_data_rate(self):
        """Test data rate calculation."""
        now = datetime.now()

        # Create readings 1 second apart
        readings = [
            SensorReading(now - timedelta(seconds=2), 10.0),
            SensorReading(now - timedelta(seconds=1), 20.0),
            SensorReading(now, 30.0),
        ]

        # Should be 1 reading per second (2 intervals over 2 seconds)
        rate = calculate_data_rate(readings)
        assert abs(rate - 1.0) < 0.1

        # Test with empty list
        assert calculate_data_rate([]) == 0.0

        # Test with single reading
        assert calculate_data_rate([readings[0]]) == 0.0
