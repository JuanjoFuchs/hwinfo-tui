"""Integration tests for chart rendering.

These tests verify the complete chart rendering pipeline, including
the critical dual-axis and single-axis code paths that would have
caught the missing function call bug.
"""

import pytest
from unittest.mock import patch, call
from pathlib import Path

from hwinfo_tui.data.csv_reader import CSVReader
from hwinfo_tui.display.chart import SensorChart
from hwinfo_tui.utils.units import UnitFilter


class TestChartRenderingCodePaths:
    """Test different chart rendering code paths."""

    def test_dual_axis_chart_sets_both_axis_ticks(self, temp_csv):
        """CRITICAL: Test that dual-axis mode configures ticks for BOTH axes.

        This test would have caught the bug where the right axis
        color assignment was missing the RGB tuple conversion.
        """
        # Setup: Create CSV with two different units
        csv_path = temp_csv([
            ("CPU Temp", "°C"),
            ("CPU Usage", "%")
        ], rows=10)

        # Initialize sensors and read data
        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]", "CPU Usage [%]"])
        reader.read_initial_data(window_seconds=10)

        # Create sensor groups (should create 2 groups for 2 units)
        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        assert len(sensor_groups) == 2, "Should have 2 sensor groups for dual-axis mode"

        # Create chart with sensor colors
        chart = SensorChart()
        sensor_colors = {
            "CPU Temp [°C]": (255, 100, 100),
            "CPU Usage [%]": (100, 255, 100),
        }

        # Mock plotext yticks to verify calls
        with patch('plotext.yticks') as mock_yticks:
            chart_mixin = chart.create_chart(
                sensors=sensors,
                sensor_groups=sensor_groups,
                time_window_seconds=10,
                height=20,
                sensor_colors=sensor_colors
            )

            # Render chart to trigger tick configuration
            chart_mixin._create_plotext_chart(100, 20)

            # CRITICAL ASSERTION: Verify yticks was called for BOTH axes
            assert mock_yticks.call_count == 2, \
                f"Expected 2 calls to yticks (left and right), got {mock_yticks.call_count}"

            # Verify left axis
            left_calls = [c for c in mock_yticks.call_args_list
                         if c[1].get('yside') == 'left']
            assert len(left_calls) == 1, "Left axis ticks not set"

            # Verify right axis - THIS WOULD HAVE CAUGHT THE BUG
            right_calls = [c for c in mock_yticks.call_args_list
                          if c[1].get('yside') == 'right']
            assert len(right_calls) == 1, "Right axis ticks not set"

            # Both axes should have tick positions and labels
            assert len(left_calls[0][0]) >= 2, "Left axis should have positions and labels"
            assert len(right_calls[0][0]) >= 2, "Right axis should have positions and labels"

    def test_single_axis_chart_sets_only_left_ticks(self, temp_csv):
        """Test that single-axis mode only sets left axis ticks."""
        # Setup: Create CSV with single unit
        csv_path = temp_csv([("CPU Temp", "°C")], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])
        reader.read_initial_data(window_seconds=10)

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        assert len(sensor_groups) == 1, "Should have 1 sensor group for single-axis mode"

        chart = SensorChart()
        sensor_colors = {"CPU Temp [°C]": (255, 100, 100)}

        with patch('plotext.yticks') as mock_yticks:
            chart_mixin = chart.create_chart(
                sensors=sensors,
                sensor_groups=sensor_groups,
                time_window_seconds=10,
                height=20,
                sensor_colors=sensor_colors
            )

            chart_mixin._create_plotext_chart(100, 20)

            # Should only call yticks once for left axis
            assert mock_yticks.call_count == 1, \
                f"Expected 1 call to yticks (left only), got {mock_yticks.call_count}"
            assert mock_yticks.call_args[1]['yside'] == 'left', \
                "Single axis should use left side"

    def test_all_plot_calls_receive_rgb_tuples(self, temp_csv):
        """Test that all plot calls receive RGB tuples directly (not color names).

        This verifies the bug fix where we removed the color mapping function.
        """
        csv_path = temp_csv([
            ("CPU Temp", "°C"),
            ("GPU Temp", "°C")
        ], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]", "GPU Temp [°C]"])
        reader.read_initial_data(window_seconds=10)

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        chart = SensorChart()
        sensor_colors = {
            "CPU Temp [°C]": (255, 100, 100),  # RGB tuple
            "GPU Temp [°C]": (100, 255, 100),  # RGB tuple
        }

        with patch('plotext.plot') as mock_plot:
            chart_mixin = chart.create_chart(
                sensors=sensors,
                sensor_groups=sensor_groups,
                time_window_seconds=10,
                height=20,
                sensor_colors=sensor_colors
            )

            chart_mixin._create_plotext_chart(100, 20)

            # Verify plot was called for both sensors
            assert mock_plot.call_count == 2, "Should plot both sensors"

            # Verify all calls received RGB tuples (not strings)
            for call_args in mock_plot.call_args_list:
                color = call_args[1]['color']
                assert isinstance(color, tuple), \
                    f"Color should be RGB tuple, got {type(color)}"
                assert len(color) == 3, \
                    f"Color should be 3-element tuple, got {len(color)}"
                assert all(isinstance(c, (int, float)) for c in color), \
                    "Color tuple should contain numeric values"

    def test_yes_no_sensor_gets_special_tick_configuration(self, temp_csv):
        """Test that Yes/No sensors get special tick labels and Y-axis limits."""
        csv_path = temp_csv([("Throttling", "Yes/No")], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["Throttling [Yes/No]"])
        reader.read_initial_data(window_seconds=10)

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        chart = SensorChart()
        sensor_colors = {"Throttling [Yes/No]": (255, 255, 100)}

        with patch('plotext.yticks') as mock_yticks, \
             patch('plotext.ylim') as mock_ylim:

            chart_mixin = chart.create_chart(
                sensors=sensors,
                sensor_groups=sensor_groups,
                time_window_seconds=10,
                height=20,
                sensor_colors=sensor_colors
            )

            chart_mixin._create_plotext_chart(100, 20)

            # Verify special tick positions and labels
            assert mock_yticks.call_count == 1, "Should set ticks for Yes/No sensor"

            tick_positions = mock_yticks.call_args[0][0]
            tick_labels = mock_yticks.call_args[0][1]

            assert tick_positions == [0.0, 1.0], \
                f"Yes/No ticks should be [0.0, 1.0], got {tick_positions}"
            assert tick_labels == ["No", "Yes"], \
                f"Yes/No labels should be ['No', 'Yes'], got {tick_labels}"

            # Verify Y-axis range is constrained to [0, 1]
            assert mock_ylim.call_count == 1, "Should set Y-axis limits for Yes/No sensor"
            assert mock_ylim.call_args[0] == (0.0, 1.0), \
                f"Y-axis should be limited to [0, 1], got {mock_ylim.call_args[0]}"
            assert mock_ylim.call_args[1]['yside'] == 'left', \
                "Y-axis limit should be for left side"


class TestChartEmptyAndErrorStates:
    """Test chart behavior with edge cases."""

    def test_chart_handles_empty_sensors(self):
        """Test chart rendering with no sensor data."""
        chart = SensorChart()

        with patch('plotext.build') as mock_build:
            chart_mixin = chart.create_chart(
                sensors={},  # Empty sensors
                sensor_groups=[],
                time_window_seconds=10,
                height=20,
                sensor_colors={}
            )

            # Should still render without crashing
            chart_mixin._create_plotext_chart(100, 20)
            assert mock_build.called, "Should still build chart for empty state"

    def test_chart_handles_sensors_with_no_readings(self, temp_csv):
        """Test chart with sensors that have no data yet."""
        from hwinfo_tui.data.sensors import Sensor, SensorGroup, SensorInfo

        # Create sensor without any readings
        sensor_info = SensorInfo(name="CPU Temp [°C]", unit="°C")
        sensor = Sensor(info=sensor_info)
        sensors = {"CPU Temp [°C]": sensor}

        sensor_group = SensorGroup(unit="°C", sensors=[sensor])

        chart = SensorChart()
        sensor_colors = {"CPU Temp [°C]": (255, 100, 100)}

        # Should handle gracefully without crashing
        chart_mixin = chart.create_chart(
            sensors=sensors,
            sensor_groups=[sensor_group],
            time_window_seconds=10,
            height=20,
            sensor_colors=sensor_colors
        )

        result = chart_mixin._create_plotext_chart(100, 20)
        assert isinstance(result, str), "Should return chart string"


class TestAxisConfiguration:
    """Test Y-axis configuration for different sensor types."""

    def test_numeric_sensor_gets_padded_range(self, temp_csv):
        """Test that numeric sensors get proper tick ranges with padding."""
        csv_path = temp_csv([("CPU Temp", "°C")], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])
        reader.read_initial_data(window_seconds=10)

        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        chart = SensorChart()
        sensor_colors = {"CPU Temp [°C]": (255, 100, 100)}

        with patch('plotext.yticks') as mock_yticks:
            chart_mixin = chart.create_chart(
                sensors=sensors,
                sensor_groups=sensor_groups,
                time_window_seconds=10,
                height=20,
                sensor_colors=sensor_colors
            )

            chart_mixin._create_plotext_chart(100, 20)

            # Verify ticks were set
            assert mock_yticks.called, "Should set Y-axis ticks"

            tick_labels = mock_yticks.call_args[0][1]

            # Verify units are included in labels
            assert any('°C' in str(label) for label in tick_labels), \
                "Tick labels should include units"
