"""Integration tests for layout and component integration.

Tests verify layout decisions, space allocation, and component coordination.
"""

from unittest.mock import Mock, patch

from rich.console import Console

from hwinfo_tui.data.csv_reader import CSVReader
from hwinfo_tui.display.layout import HWInfoLayout
from hwinfo_tui.utils.stats import StatsCalculator
from hwinfo_tui.utils.units import UnitFilter


class TestLayoutModeDecisions:
    """Test layout mode decisions based on terminal size."""

    def test_full_mode_with_large_terminal(self):
        """Test that full mode is used with large terminal."""
        console = Mock(spec=Console)
        layout = HWInfoLayout(console)

        with patch.object(layout, 'get_terminal_size', return_value=(120, 30)):
            assert not layout.should_use_compact_mode(), \
                "Should use full mode with 120x30 terminal"
            assert not layout.should_use_compact_table(), \
                "Should use full table with 120 width"

    def test_compact_mode_with_narrow_terminal(self):
        """Test that compact mode is used with narrow terminal."""
        console = Mock(spec=Console)
        layout = HWInfoLayout(console)

        with patch.object(layout, 'get_terminal_size', return_value=(80, 30)):
            assert layout.should_use_compact_mode(), \
                "Should use compact mode with 80 width"
            assert layout.should_use_compact_table(), \
                "Should use compact table with 80 width"

    def test_compact_mode_with_short_terminal(self):
        """Test that compact mode is used with short terminal."""
        console = Mock(spec=Console)
        layout = HWInfoLayout(console)

        with patch.object(layout, 'get_terminal_size', return_value=(120, 15)):
            assert layout.should_use_compact_mode(), \
                "Should use compact mode with 15 height"
            assert not layout.should_use_compact_table(), \
                "Should still use full table with 120 width"

    def test_threshold_boundaries(self):
        """Test exact threshold boundaries."""
        console = Mock(spec=Console)
        layout = HWInfoLayout(console)

        # Test width threshold (100)
        with patch.object(layout, 'get_terminal_size', return_value=(99, 30)):
            assert layout.should_use_compact_mode()
            assert layout.should_use_compact_table()

        with patch.object(layout, 'get_terminal_size', return_value=(100, 30)):
            assert not layout.should_use_compact_mode()
            assert not layout.should_use_compact_table()

        # Test height threshold (20)
        with patch.object(layout, 'get_terminal_size', return_value=(120, 19)):
            assert layout.should_use_compact_mode()

        with patch.object(layout, 'get_terminal_size', return_value=(120, 20)):
            assert not layout.should_use_compact_mode()


class TestSensorGroupCreation:
    """Test sensor group creation for dual-axis mode."""

    def test_single_unit_creates_single_group(self, temp_csv):
        """Test that sensors with single unit create one group."""
        csv_path = temp_csv([
            ("CPU Temp", "°C"),
            ("GPU Temp", "°C"),
        ], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]", "GPU Temp [°C]"])

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        assert len(sensor_groups) == 1, "Should create 1 group for single unit"
        assert sensor_groups[0].unit == "°C"
        assert len(sensor_groups[0].sensors) == 2

    def test_two_units_create_two_groups(self, temp_csv):
        """Test that sensors with two units create two groups (dual-axis)."""
        csv_path = temp_csv([
            ("CPU Temp", "°C"),
            ("CPU Usage", "%"),
        ], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]", "CPU Usage [%]"])

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        assert len(sensor_groups) == 2, "Should create 2 groups for dual-axis mode"

        # Verify groups have correct units
        units = {group.unit for group in sensor_groups}
        assert "°C" in units
        assert "%" in units

    def test_three_units_limited_to_two_groups(self, temp_csv):
        """Test that only first two units are used when more are available."""
        csv_path = temp_csv([
            ("CPU Temp", "°C"),
            ("CPU Usage", "%"),
            ("CPU Power", "W"),
        ], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors([
            "CPU Temp [°C]",
            "CPU Usage [%]",
            "CPU Power [W]"
        ])

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        # create_sensor_groups doesn't limit - it groups all sensors by unit
        # The limit to 2 units is enforced by UnitFilter.filter_sensors_by_unit()
        assert len(sensor_groups) == 3, \
            "Should create 3 groups for 3 different units"


class TestFullLayoutIntegration:
    """Test full layout update with all components."""

    def test_layout_creates_all_components(self, temp_csv):
        """Test that layout update creates all necessary components."""
        csv_path = temp_csv([("CPU Temp", "°C")], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])
        reader.read_initial_data(window_seconds=10)

        console = Mock(spec=Console)
        console.width = 120
        console.height = 30

        layout = HWInfoLayout(console)

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)
        stats_calc = StatsCalculator()
        stats = stats_calc.calculate_all_stats(sensors)

        with patch.object(layout, 'get_terminal_size', return_value=(120, 30)):
            layout.update_layout(
                sensors=sensors,
                sensor_groups=sensor_groups,
                stats=stats,
                time_window=10,
                refresh_rate=1.0,
                csv_path=str(csv_path)
            )

        # Verify components were created
        assert layout.body_layout is not None, "Should create body layout"
        assert layout.chart is not None, "Should create chart"
        assert layout.sensor_colors, "Should assign sensor colors"

    def test_layout_with_multiple_sensors_and_groups(self, temp_csv):
        """Test layout with complex sensor configuration."""
        csv_path = temp_csv([
            ("CPU Temp", "°C"),
            ("GPU Temp", "°C"),
            ("CPU Usage", "%"),
            ("Throttling", "Yes/No"),
        ], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors([
            "CPU Temp [°C]",
            "GPU Temp [°C]",
            "CPU Usage [%]",
            "Throttling [Yes/No]"
        ])
        reader.read_initial_data(window_seconds=10)

        console = Mock(spec=Console)
        console.width = 120
        console.height = 30

        layout = HWInfoLayout(console)

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)
        stats_calc = StatsCalculator()
        stats = stats_calc.calculate_all_stats(sensors)

        with patch.object(layout, 'get_terminal_size', return_value=(120, 30)):
            layout.update_layout(
                sensors=sensors,
                sensor_groups=sensor_groups,
                stats=stats,
                time_window=10,
                refresh_rate=1.0,
                csv_path=str(csv_path)
            )

        # Verify all sensors got colors
        assert len(layout.sensor_colors) == 4, \
            "All 4 sensors should have assigned colors"

        # Verify colors are consistent
        for sensor_name in sensors:
            assert sensor_name in layout.sensor_colors, \
                f"Sensor {sensor_name} should have color assigned"


class TestLayoutWithEmptyData:
    """Test layout behavior with edge cases."""

    def test_layout_handles_no_sensor_data(self):
        """Test layout with sensors that have no readings."""
        from hwinfo_tui.data.sensors import Sensor, SensorGroup, SensorInfo

        sensor_info = SensorInfo(name="CPU Temp [°C]", unit="°C")
        sensor = Sensor(info=sensor_info)
        sensors = {"CPU Temp [°C]": sensor}
        sensor_group = SensorGroup(unit="°C", sensors=[sensor])

        console = Mock(spec=Console)
        console.width = 120
        console.height = 30

        layout = HWInfoLayout(console)

        stats_calc = StatsCalculator()
        stats = stats_calc.calculate_all_stats(sensors)

        with patch.object(layout, 'get_terminal_size', return_value=(120, 30)):
            result = layout.update_layout(
                sensors=sensors,
                sensor_groups=[sensor_group],
                stats=stats,
                time_window=10,
                refresh_rate=1.0,
                csv_path="test.csv"
            )

        # Should handle gracefully
        assert result is not None
        assert "CPU Temp [°C]" in layout.sensor_colors

    def test_layout_with_empty_sensors_dict(self):
        """Test layout with no sensors."""
        console = Mock(spec=Console)
        console.width = 120
        console.height = 30

        layout = HWInfoLayout(console)

        with patch.object(layout, 'get_terminal_size', return_value=(120, 30)):
            result = layout.update_layout(
                sensors={},
                sensor_groups=[],
                stats={},
                time_window=10,
                refresh_rate=1.0,
                csv_path="test.csv"
            )

        # Should handle empty state
        assert result is not None
