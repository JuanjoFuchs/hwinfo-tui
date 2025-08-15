"""Tests for sensor data models and functionality."""

from datetime import datetime, timedelta

import pytest

from hwinfo_tui.data.sensors import Sensor, SensorGroup, SensorInfo, SensorReading


class TestSensorInfo:
    """Test SensorInfo class."""

    def test_unit_extraction(self):
        """Test unit extraction from sensor names."""
        # Test with unit
        sensor = SensorInfo("CPU Temperature [°C]")
        assert sensor.unit == "°C"

        # Test without unit
        sensor = SensorInfo("CPU Usage")
        assert sensor.unit is None

        # Test with different unit formats
        sensor = SensorInfo("Memory Usage [%]")
        assert sensor.unit == "%"

        sensor = SensorInfo("Power Consumption [W]")
        assert sensor.unit == "W"

    def test_display_name(self):
        """Test display name generation."""
        sensor = SensorInfo("CPU Temperature [°C]")
        assert sensor.display_name == "CPU Temperature"

        sensor = SensorInfo("CPU Usage")
        assert sensor.display_name == "CPU Usage"

    def test_static_unit_extraction(self):
        """Test static unit extraction method."""
        assert SensorInfo.extract_unit_from_name("CPU Temp [°C]") == "°C"
        assert SensorInfo.extract_unit_from_name("Memory [MB]") == "MB"
        assert SensorInfo.extract_unit_from_name("No Unit") is None


class TestSensorReading:
    """Test SensorReading class."""

    def test_valid_reading(self):
        """Test creating valid sensor readings."""
        timestamp = datetime.now()
        reading = SensorReading(timestamp, 42.5)

        assert reading.timestamp == timestamp
        assert reading.value == 42.5

    def test_value_conversion(self):
        """Test automatic value conversion to float."""
        timestamp = datetime.now()

        # Integer conversion
        reading = SensorReading(timestamp, 42)
        assert reading.value == 42.0
        assert isinstance(reading.value, float)

    def test_invalid_value(self):
        """Test invalid value handling."""
        timestamp = datetime.now()

        with pytest.raises(ValueError):
            SensorReading(timestamp, "not a number")


class TestSensor:
    """Test Sensor class."""

    def test_sensor_initialization(self):
        """Test sensor initialization."""
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        assert sensor.info == info
        assert len(sensor.readings) == 0
        assert sensor.latest_value is None
        assert sensor.latest_timestamp is None

    def test_add_reading(self):
        """Test adding readings to sensor."""
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        timestamp = datetime.now()
        sensor.add_reading(timestamp, 45.6)

        assert len(sensor.readings) == 1
        assert sensor.latest_value == 45.6
        assert sensor.latest_timestamp == timestamp

    def test_add_invalid_reading(self):
        """Test adding invalid readings."""
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        timestamp = datetime.now()

        # None values should be ignored
        sensor.add_reading(timestamp, None)
        assert len(sensor.readings) == 0

        # Empty string should be ignored
        sensor.add_reading(timestamp, "")
        assert len(sensor.readings) == 0

        # Invalid string should be ignored
        sensor.add_reading(timestamp, "invalid")
        assert len(sensor.readings) == 0

    def test_yes_no_conversion(self):
        """Test Yes/No string conversion."""
        info = SensorInfo("Thermal Throttling [Yes/No]")
        sensor = Sensor(info)

        timestamp = datetime.now()

        sensor.add_reading(timestamp, "Yes")
        assert sensor.latest_value == 1.0

        sensor.add_reading(timestamp, "No")
        assert sensor.latest_value == 0.0

    def test_get_readings_in_window(self):
        """Test getting readings within time window."""
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        now = datetime.now()

        # Add readings over 10 seconds
        for i in range(10):
            timestamp = now - timedelta(seconds=i)
            sensor.add_reading(timestamp, float(i))

        # Get readings from last 5 seconds
        recent_readings = sensor.get_readings_in_window(5)

        # Should have readings from last 5 seconds (plus the current one)
        assert len(recent_readings) <= 6

    def test_values_property(self):
        """Test values property."""
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        timestamp = datetime.now()
        sensor.add_reading(timestamp, 45.0)
        sensor.add_reading(timestamp, 50.0)

        assert sensor.values == [45.0, 50.0]

    def test_clear_readings(self):
        """Test clearing sensor readings."""
        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        timestamp = datetime.now()
        sensor.add_reading(timestamp, 45.0)
        sensor.add_reading(timestamp, 50.0)

        assert len(sensor.readings) == 2

        sensor.clear_readings()
        assert len(sensor.readings) == 0
        assert sensor.latest_value is None


class TestSensorGroup:
    """Test SensorGroup class."""

    def test_group_initialization(self):
        """Test sensor group initialization."""
        group = SensorGroup(unit="°C")

        assert group.unit == "°C"
        assert len(group.sensors) == 0

    def test_add_compatible_sensor(self):
        """Test adding compatible sensor to group."""
        group = SensorGroup(unit="°C")

        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        group.add_sensor(sensor)

        assert len(group.sensors) == 1
        assert sensor in group.sensors

    def test_add_incompatible_sensor(self):
        """Test adding incompatible sensor to group."""
        group = SensorGroup(unit="°C")

        info = SensorInfo("CPU Usage [%]")
        sensor = Sensor(info)

        with pytest.raises(ValueError):
            group.add_sensor(sensor)

    def test_sensor_names_property(self):
        """Test sensor names property."""
        group = SensorGroup(unit="°C")

        info1 = SensorInfo("CPU Temperature [°C]")
        sensor1 = Sensor(info1)

        info2 = SensorInfo("GPU Temperature [°C]")
        sensor2 = Sensor(info2)

        group.add_sensor(sensor1)
        group.add_sensor(sensor2)

        names = group.sensor_names
        assert "CPU Temperature [°C]" in names
        assert "GPU Temperature [°C]" in names

    def test_display_names_property(self):
        """Test display names property."""
        group = SensorGroup(unit="°C")

        info = SensorInfo("CPU Temperature [°C]")
        sensor = Sensor(info)

        group.add_sensor(sensor)

        display_names = group.display_names
        assert "CPU Temperature" in display_names
