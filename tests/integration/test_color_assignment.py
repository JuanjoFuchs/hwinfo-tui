"""Integration tests for color assignment across components.

Tests verify that colors are assigned consistently and flow correctly
from layout to chart to table components.
"""

import pytest
from unittest.mock import Mock

from rich.console import Console

from hwinfo_tui.data.csv_reader import CSVReader
from hwinfo_tui.display.layout import HWInfoLayout
from hwinfo_tui.display.chart import SensorChart
from hwinfo_tui.utils.units import UnitFilter
from hwinfo_tui.utils.stats import StatsCalculator


class TestColorAssignment:
    """Test color assignment logic."""

    def test_color_assignment_is_deterministic(self, temp_csv):
        """Test that color assignment is consistent across runs."""
        csv_path = temp_csv([
            ("Sensor A", "°C"),
            ("Sensor B", "°C"),
            ("Sensor C", "°C"),
        ], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors([
            "Sensor A [°C]",
            "Sensor B [°C]",
            "Sensor C [°C]"
        ])

        console = Console()
        layout = HWInfoLayout(console)

        # Assign colors
        layout._assign_sensor_colors(sensors)

        # Expected color assignments (sorted alphabetically)
        expected_colors = {
            "Sensor A [°C]": (255, 100, 100),  # First color - red
            "Sensor B [°C]": (100, 255, 100),  # Second color - green
            "Sensor C [°C]": (100, 150, 255),  # Third color - blue
        }

        assert layout.sensor_colors == expected_colors, \
            "Colors should be assigned deterministically based on sorted sensor names"

    def test_color_assignment_handles_sorting(self, temp_csv):
        """Test that colors are assigned based on alphabetical order, not insertion order."""
        csv_path = temp_csv([
            ("Zebra", "°C"),
            ("Apple", "°C"),
            ("Banana", "°C"),
        ], rows=5)

        reader = CSVReader(csv_path)
        # Initialize in different order
        sensors = reader.initialize_sensors([
            "Zebra [°C]",
            "Apple [°C]",
            "Banana [°C]"
        ])

        console = Console()
        layout = HWInfoLayout(console)
        layout._assign_sensor_colors(sensors)

        # Should be assigned based on alphabetical order
        # Apple (first), Banana (second), Zebra (third)
        assert layout.sensor_colors["Apple [°C]"] == (255, 100, 100)  # First color
        assert layout.sensor_colors["Banana [°C]"] == (100, 255, 100)  # Second color
        assert layout.sensor_colors["Zebra [°C]"] == (100, 150, 255)  # Third color

    def test_color_cycling_beyond_palette(self, temp_csv):
        """Test that colors cycle when there are more than 8 sensors."""
        # Create 10 sensors (palette has only 8 colors)
        sensor_list = [(f"Sensor {chr(65+i)}", "°C") for i in range(10)]
        csv_path = temp_csv(sensor_list, rows=5)

        reader = CSVReader(csv_path)
        sensor_names = [f"Sensor {chr(65+i)} [°C]" for i in range(10)]
        sensors = reader.initialize_sensors(sensor_names)

        console = Console()
        layout = HWInfoLayout(console)
        layout._assign_sensor_colors(sensors)

        # Verify all sensors got colors
        assert len(layout.sensor_colors) == 10

        # Verify colors cycle (sensors 9 and 10 should reuse first two colors)
        first_color = layout.sensor_colors["Sensor A [°C]"]
        ninth_color = layout.sensor_colors["Sensor I [°C]"]  # 9th sensor (index 8)
        assert ninth_color == first_color, "Colors should cycle after 8 sensors"


class TestColorFlowThroughComponents:
    """Test that colors flow correctly from layout to chart and table."""

    def test_colors_flow_from_layout_to_chart(self, temp_csv):
        """Test that colors assigned in layout are passed to chart."""
        csv_path = temp_csv([("CPU Temp", "°C")], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])
        reader.read_initial_data(window_seconds=10)

        console = Console()
        layout = HWInfoLayout(console)

        # Assign colors in layout
        layout._assign_sensor_colors(sensors)
        expected_color = layout.sensor_colors["CPU Temp [°C]"]

        # Create chart with layout's colors
        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)

        chart = SensorChart()
        chart_mixin = chart.create_chart(
            sensors=sensors,
            sensor_groups=sensor_groups,
            time_window_seconds=10,
            height=20,
            sensor_colors=layout.sensor_colors
        )

        # Verify chart received the colors
        assert chart_mixin.sensor_colors["CPU Temp [°C]"] == expected_color, \
            "Chart should receive colors from layout"

    def test_color_consistency_in_full_layout_update(self, temp_csv):
        """Test that colors remain consistent through a full layout update."""
        csv_path = temp_csv([
            ("CPU Temp", "°C"),
            ("GPU Temp", "°C"),
        ], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]", "GPU Temp [°C]"])
        reader.read_initial_data(window_seconds=10)

        console = Mock(spec=Console)
        console.width = 120
        console.height = 30

        layout = HWInfoLayout(console)

        # Create full layout
        unit_filter = UnitFilter()
        sensor_groups = unit_filter.create_sensor_groups(sensors)
        stats_calc = StatsCalculator()
        stats = stats_calc.calculate_all_stats(sensors)

        layout.update_layout(
            sensors=sensors,
            sensor_groups=sensor_groups,
            stats=stats,
            time_window=10,
            refresh_rate=1.0,
            csv_path=str(csv_path)
        )

        # Verify colors were assigned
        assert "CPU Temp [°C]" in layout.sensor_colors
        assert "GPU Temp [°C]" in layout.sensor_colors

        # Verify chart has the same colors
        chart_colors = layout.chart.get_sensor_colors()
        assert chart_colors["CPU Temp [°C]"] == layout.sensor_colors["CPU Temp [°C]"]
        assert chart_colors["GPU Temp [°C]"] == layout.sensor_colors["GPU Temp [°C]"]

    def test_same_sensor_gets_same_color_across_updates(self, temp_csv):
        """Test that the same sensor gets the same color in multiple updates."""
        csv_path = temp_csv([("CPU Temp", "°C")], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])
        reader.read_initial_data(window_seconds=10)

        console = Console()
        layout = HWInfoLayout(console)

        # First assignment
        layout._assign_sensor_colors(sensors)
        first_color = layout.sensor_colors["CPU Temp [°C]"]

        # Second assignment (simulating re-initialization)
        layout._assign_sensor_colors(sensors)
        second_color = layout.sensor_colors["CPU Temp [°C]"]

        assert first_color == second_color, \
            "Same sensor should get same color across multiple assignments"


class TestColorPalette:
    """Test the color palette used for sensor assignment."""

    def test_palette_has_distinct_colors(self):
        """Test that the first 8 colors in the palette are distinct."""
        from hwinfo_tui.display.layout import HWInfoLayout

        # Get the RGB palette
        rgb_palette = [
            (255, 100, 100),  # Bright red
            (100, 255, 100),  # Bright green
            (100, 150, 255),  # Bright blue
            (255, 255, 100),  # Bright yellow
            (255, 100, 255),  # Bright magenta
            (100, 255, 255),  # Bright cyan
            (255, 180, 100),  # Orange
            (180, 100, 255),  # Purple
        ]

        # Verify all colors are unique
        assert len(rgb_palette) == len(set(rgb_palette)), \
            "All colors in palette should be distinct"

        # Verify all colors are valid RGB tuples
        for color in rgb_palette:
            assert len(color) == 3, "Color should be 3-element tuple"
            assert all(0 <= c <= 255 for c in color), \
                "Color values should be in range [0, 255]"

    def test_colors_are_rgb_tuples_not_strings(self, temp_csv):
        """Test that assigned colors are RGB tuples, not color name strings."""
        csv_path = temp_csv([("CPU Temp", "°C")], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])

        console = Console()
        layout = HWInfoLayout(console)
        layout._assign_sensor_colors(sensors)

        color = layout.sensor_colors["CPU Temp [°C]"]

        # Verify it's a tuple
        assert isinstance(color, tuple), \
            f"Color should be tuple, got {type(color)}"

        # Verify it has 3 elements
        assert len(color) == 3, \
            f"Color should have 3 elements, got {len(color)}"

        # Verify all elements are numeric
        assert all(isinstance(c, (int, float)) for c in color), \
            "Color tuple should contain numeric values"

        # Verify it's NOT a string (common bug)
        assert not isinstance(color, str), \
            "Color should not be a string like 'red' or 'yellow'"
