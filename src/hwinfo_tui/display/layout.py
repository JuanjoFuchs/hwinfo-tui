"""Layout management for the HWInfo TUI display."""

from __future__ import annotations

import os
from typing import Any

from rich.console import Console, Group
from rich.layout import Layout
from rich.text import Text

from ..data.sensors import Sensor, SensorGroup
from ..utils.stats import SensorStats
from .chart import SensorChart
from .table import CompactTable, StatsTable


class HWInfoLayout:
    """Main layout manager for the HWInfo TUI."""

    def __init__(self, console: Console) -> None:
        """Initialize the layout manager."""
        self.console = console
        self.stats_table = StatsTable(console)
        self.compact_table = CompactTable(console)
        self.chart = SensorChart()

        # Layout components (header-less)
        self.root_layout = Layout()
        self.body_layout = Layout()

        # Setup layout structure (no header, no footer)
        self.root_layout = self.body_layout

        # State
        self.paused = False
        self.compact_mode = False

        # Color management - improved colors for better terminal visibility
        self.rgb_colors = [
            (255, 100, 100),   # Bright red
            (100, 255, 100),   # Bright green
            (100, 150, 255),   # Bright blue
            (255, 255, 100),   # Bright yellow
            (255, 100, 255),   # Bright magenta
            (100, 255, 255),   # Bright cyan
            (255, 180, 100),   # Orange
            (180, 100, 255),   # Purple
        ]
        self.sensor_colors: dict[str, tuple[int, int, int]] = {}  # Current sensor to RGB color mapping

    def get_terminal_size(self) -> tuple[int, int]:
        """Get current terminal size."""
        try:
            size = os.get_terminal_size()
            return size.columns, size.lines
        except OSError:
            return 80, 24  # Default fallback

    def should_use_compact_mode(self) -> bool:
        """Determine if compact mode should be used."""
        width, height = self.get_terminal_size()
        return width < 100 or height < 20

    def should_use_compact_table(self) -> bool:
        """Determine if compact table (fewer columns) should be used based on width."""
        width, height = self.get_terminal_size()
        return width < 100

    def _assign_sensor_colors(self, sensors: dict[str, Sensor]) -> None:
        """Assign RGB colors to sensors deterministically based on sensor names."""
        # Get all sensor names and sort them for consistent ordering
        sensor_names = sorted(sensors.keys())

        # Clear previous mappings
        self.sensor_colors = {}

        # Assign RGB colors based on position in sorted list
        for i, sensor_name in enumerate(sensor_names):
            rgb_color = self.rgb_colors[i % len(self.rgb_colors)]
            self.sensor_colors[sensor_name] = rgb_color

            # Also assign the color to the sensor info for easy access
            if isinstance(sensors[sensor_name], Sensor):
                sensors[sensor_name].info.color = f"rgb({rgb_color[0]},{rgb_color[1]},{rgb_color[2]})"

        # Log color assignments for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Color assignments: {self.sensor_colors}")

    def update_layout(
        self,
        sensors: dict[str, Sensor],
        sensor_groups: list[SensorGroup],
        stats: dict[str, SensorStats],
        time_window: int,
        refresh_rate: float,
        csv_path: str
    ) -> Layout:
        """Update the complete layout with current data."""
        # Determine display mode
        self.compact_mode = self.should_use_compact_mode()
        width, height = self.get_terminal_size()

        # Assign colors to sensors
        self._assign_sensor_colors(sensors)

        # Update body based on mode (no header)
        if self.compact_mode:
            self._update_compact_body(sensors, stats, time_window)
        else:
            self._update_full_body(sensors, sensor_groups, stats, time_window, width, height)

        return self.root_layout


    def _update_full_body(
        self,
        sensors: dict[str, Sensor],
        sensor_groups: list[SensorGroup],
        stats: dict[str, SensorStats],
        time_window: int,
        width: int,
        height: int
    ) -> None:
        """Update body layout for full display mode."""
        # Calculate available space for body (no header)
        # With screen=True, use full height without padding
        available_height = height

        # Split body into table and chart sections - minimize table, maximize chart
        table_height = min(len(stats) + 3, max(6, available_height // 6))  # Compact table, at least 6 lines, max 1/6 of space
        chart_height = available_height - table_height

        table_layout = Layout(size=table_height)
        chart_layout = Layout(size=chart_height)

        self.body_layout.split_column(table_layout, chart_layout)

        # Create chart mixin with color information and explicit height
        chart_mixin = self.chart.create_chart(
            sensors, sensor_groups, time_window,
            height=chart_height,
            sensor_colors=self.sensor_colors
        )

        # Update table with color information - choose table based on width only
        if self.should_use_compact_table():
            table = self.compact_table.create_table(stats, self.sensor_colors)
        else:
            table = self.stats_table.create_table(stats, sensor_groups, time_window, self.sensor_colors)
        table_layout.update(table)

        chart_layout.update(chart_mixin)

    def _update_compact_body(
        self,
        sensors: dict[str, Sensor],
        stats: dict[str, SensorStats],
        time_window: int
    ) -> None:
        """Update body layout for compact display mode."""
        # In compact mode, show table only or simple chart
        width, height = self.get_terminal_size()

        if height < 15:
            # Very small terminal - table only, choose table based on width
            if self.should_use_compact_table():
                table = self.compact_table.create_table(stats, self.sensor_colors)
            else:
                # Import sensor_groups for full table
                sensor_groups = self._create_sensor_groups(sensors)
                table = self.stats_table.create_table(stats, sensor_groups, time_window, self.sensor_colors)
            self.body_layout.update(table)
        else:
            # Small terminal - table + mini chart, choose table based on width
            table_height = min(len(stats) + 3, height // 2)
            chart_height = height - table_height

            table_layout = Layout(size=table_height)
            chart_layout = Layout(size=chart_height)

            self.body_layout.split_column(table_layout, chart_layout)

            # Create sensor groups once for both table and chart
            sensor_groups = self._create_sensor_groups(sensors)

            # Choose table type based on width, not height
            if self.should_use_compact_table():
                table = self.compact_table.create_table(stats, self.sensor_colors)
            else:
                table = self.stats_table.create_table(stats, sensor_groups, time_window, self.sensor_colors)
            table_layout.update(table)

            # Mini chart (no panel border) with explicit height
            chart_mixin = self.chart.create_chart(
                sensors, sensor_groups, time_window,
                height=chart_height,
                sensor_colors=self.sensor_colors
            )

            chart_layout.update(chart_mixin)


    def _create_sensor_groups(self, sensors: dict[str, Sensor]) -> list[SensorGroup]:
        """Create sensor groups from sensors dictionary."""
        from ..utils.units import UnitFilter
        unit_filter = UnitFilter()
        return unit_filter.create_sensor_groups(sensors)

    def toggle_pause(self) -> bool:
        """Toggle pause state and return new state."""
        self.paused = not self.paused
        return self.paused
