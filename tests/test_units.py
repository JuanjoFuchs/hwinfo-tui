"""Tests for unit detection and filtering functionality."""

from hwinfo_tui.data.sensors import Sensor, SensorInfo
from hwinfo_tui.utils.units import (
    UnitFilter,
    suggest_sensor_names,
    validate_sensor_compatibility,
)


class TestUnitFilter:
    """Test UnitFilter class."""

    def test_extract_unit(self):
        """Test unit extraction from sensor names."""
        assert UnitFilter.extract_unit("CPU Temperature [°C]") == "°C"
        assert UnitFilter.extract_unit("Memory Usage [%]") == "%"
        assert UnitFilter.extract_unit("Power Draw [W]") == "W"
        assert UnitFilter.extract_unit("Clock Speed [MHz]") == "MHz"
        assert UnitFilter.extract_unit("No Unit Sensor") is None

    def test_unit_normalization(self):
        """Test unit normalization."""
        # Temperature
        assert UnitFilter.extract_unit("Temp [C]") == "°C"
        assert UnitFilter.extract_unit("Temp [Celsius]") == "°C"

        # Percentage
        assert UnitFilter.extract_unit("Usage [percent]") == "%"
        assert UnitFilter.extract_unit("Load [pct]") == "%"

        # Power
        assert UnitFilter.extract_unit("Power [Watts]") == "W"
        assert UnitFilter.extract_unit("Power [watts]") == "W"

        # Frequency
        assert UnitFilter.extract_unit("Clock [Mhz]") == "MHz"
        assert UnitFilter.extract_unit("Freq [Megahertz]") == "MHz"

    def test_filter_single_unit(self):
        """Test filtering with single unit."""
        unit_filter = UnitFilter(max_units=2)

        sensors = [
            "CPU Core 0 [°C]",
            "CPU Core 1 [°C]",
            "GPU Temperature [°C]"
        ]

        accepted, excluded = unit_filter.filter_sensors_by_unit(sensors)

        assert len(accepted) == 3
        assert len(excluded) == 0
        assert set(accepted) == set(sensors)

    def test_filter_two_units(self):
        """Test filtering with two different units."""
        unit_filter = UnitFilter(max_units=2)

        sensors = [
            "CPU Temperature [°C]",
            "CPU Usage [%]",
            "GPU Temperature [°C]",
            "Memory Usage [%]"
        ]

        accepted, excluded = unit_filter.filter_sensors_by_unit(sensors)

        assert len(accepted) == 4
        assert len(excluded) == 0

    def test_filter_too_many_units(self):
        """Test filtering with more than max allowed units."""
        unit_filter = UnitFilter(max_units=2)

        sensors = [
            "CPU Temperature [°C]",  # First unit - accepted
            "CPU Usage [%]",         # Second unit - accepted
            "Power Draw [W]",        # Third unit - should be excluded
            "Clock Speed [MHz]"      # Fourth unit - should be excluded
        ]

        accepted, excluded = unit_filter.filter_sensors_by_unit(sensors)

        assert len(accepted) == 2
        assert len(excluded) == 2
        assert "CPU Temperature [°C]" in accepted
        assert "CPU Usage [%]" in accepted

    def test_filter_with_no_unit_sensors(self):
        """Test filtering with sensors that have no units."""
        unit_filter = UnitFilter(max_units=2)

        sensors = [
            "CPU Temperature [°C]",
            "Some Sensor",  # No unit
            "Another Sensor"  # No unit
        ]

        accepted, excluded = unit_filter.filter_sensors_by_unit(sensors)

        # Should accept the temperature sensor and one no-unit sensor group
        assert len(accepted) == 3
        assert len(excluded) == 0

    def test_create_sensor_groups(self):
        """Test creating sensor groups."""
        unit_filter = UnitFilter()

        # Create test sensors
        temp_sensor1 = Sensor(SensorInfo("CPU Temp [°C]"))
        temp_sensor2 = Sensor(SensorInfo("GPU Temp [°C]"))
        usage_sensor = Sensor(SensorInfo("CPU Usage [%]"))

        sensors = {
            "CPU Temp [°C]": temp_sensor1,
            "GPU Temp [°C]": temp_sensor2,
            "CPU Usage [%]": usage_sensor
        }

        groups = unit_filter.create_sensor_groups(sensors)

        # Should have 2 groups: °C and %
        assert len(groups) == 2

        # Find temperature group
        temp_group = next((g for g in groups if g.unit == "°C"), None)
        assert temp_group is not None
        assert len(temp_group.sensors) == 2

        # Find usage group
        usage_group = next((g for g in groups if g.unit == "%"), None)
        assert usage_group is not None
        assert len(usage_group.sensors) == 1


class TestValidateSensorCompatibility:
    """Test validate_sensor_compatibility function."""

    def test_compatible_sensors(self):
        """Test with compatible sensors."""
        sensors = [
            "CPU Temperature [°C]",
            "GPU Temperature [°C]",
            "CPU Usage [%]"
        ]

        accepted, excluded, units = validate_sensor_compatibility(sensors)

        assert len(accepted) == 3
        assert len(excluded) == 0
        assert len(units) == 2
        assert "°C" in units
        assert "%" in units

    def test_incompatible_sensors(self):
        """Test with too many different units."""
        sensors = [
            "CPU Temperature [°C]",
            "CPU Usage [%]",
            "Power Draw [W]",  # Third unit - should be excluded
            "Clock Speed [MHz]"  # Fourth unit - should be excluded
        ]

        accepted, excluded, units = validate_sensor_compatibility(sensors, max_units=2)

        assert len(accepted) == 2
        assert len(excluded) == 2
        assert len(units) == 2


class TestSuggestSensorNames:
    """Test suggest_sensor_names function."""

    def test_exact_match(self):
        """Test exact match suggestions."""
        available = ["CPU Temperature [°C]", "GPU Temperature [°C]", "Memory Usage [%]"]
        suggestions = suggest_sensor_names(available, "CPU Temperature [°C]")

        assert "CPU Temperature [°C]" in suggestions
        assert suggestions[0] == "CPU Temperature [°C]"  # Exact match should be first

    def test_starts_with_match(self):
        """Test starts-with matching."""
        available = ["CPU Temperature [°C]", "GPU Temperature [°C]", "Memory Usage [%]"]
        suggestions = suggest_sensor_names(available, "CPU")

        assert "CPU Temperature [°C]" in suggestions

    def test_contains_match(self):
        """Test contains matching."""
        available = ["CPU Temperature [°C]", "GPU Temperature [°C]", "Memory Usage [%]"]
        suggestions = suggest_sensor_names(available, "Temperature")

        assert "CPU Temperature [°C]" in suggestions
        assert "GPU Temperature [°C]" in suggestions

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        available = ["CPU Temperature [°C]", "GPU Temperature [°C]", "Memory Usage [%]"]
        suggestions = suggest_sensor_names(available, "cpu temperature")

        assert "CPU Temperature [°C]" in suggestions

    def test_limit_suggestions(self):
        """Test suggestion limit."""
        available = [f"Sensor {i}" for i in range(10)]
        suggestions = suggest_sensor_names(available, "Sensor", limit=3)

        assert len(suggestions) <= 3
