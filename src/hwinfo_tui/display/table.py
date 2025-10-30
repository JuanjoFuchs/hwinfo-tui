"""Rich table display for sensor statistics."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..data.sensors import SensorGroup
from ..utils.stats import SensorStats, StatsCalculator


class StatsTable:
    """Rich table for displaying sensor statistics."""

    def __init__(self, console: Console) -> None:
        """Initialize the statistics table."""
        self.console = console
        self.stats_calculator = StatsCalculator()

    def create_table(
        self,
        stats: dict[str, SensorStats],
        sensor_groups: list[SensorGroup],
        time_window: int = 300,
        sensor_colors: dict[str, tuple] | None = None
    ) -> Table:
        """Create a Rich table displaying sensor statistics."""
        table = Table(
            show_header=True,
            header_style="bold",
            show_edge=False,
            show_lines=False,
            box=None,
            expand=True,
            width=None
        )

        # Add columns - Sensor column can expand to use available space
        table.add_column("Sensor", style="bold", no_wrap=True, min_width=20, ratio=2)
        table.add_column("Last", justify="right", min_width=10, max_width=15)
        table.add_column("Min", justify="right", min_width=10, max_width=15)
        table.add_column("Max", justify="right", min_width=10, max_width=15)
        table.add_column("Avg", justify="right", min_width=10, max_width=15)
        table.add_column("P95", justify="right", min_width=10, max_width=15)

        # Add sensor rows directly (no grouping)
        for sensor_stats in stats.values():
            self._add_sensor_row(table, sensor_stats, sensor_colors or {})

        return table

    def _group_stats_by_unit(
        self,
        stats: dict[str, SensorStats],
        sensor_groups: list[SensorGroup]
    ) -> dict[str | None, list[SensorStats]]:
        """Group statistics by unit."""
        grouped = {}

        for group in sensor_groups:
            unit_stats = []
            for sensor_name in group.sensor_names:
                if sensor_name in stats:
                    unit_stats.append(stats[sensor_name])

            if unit_stats:
                grouped[group.unit] = unit_stats

        return grouped

    def _add_sensor_row(self, table: Table, sensor_stats: SensorStats, sensor_colors: dict[str, tuple]) -> None:
        """Add a row for a single sensor to the table."""
        # Get display name (remove unit suffix) with color coding
        display_name = self._get_colored_display_name(sensor_stats.sensor_name, sensor_colors)

        # Get color-coded values using sensor colors
        last_text = self._get_colored_value(sensor_stats, sensor_stats.last, sensor_colors)
        min_text = self._get_colored_value(sensor_stats, sensor_stats.min_value, sensor_colors)
        max_text = self._get_colored_value(sensor_stats, sensor_stats.max_value, sensor_colors)
        avg_text = self._get_colored_value(sensor_stats, sensor_stats.avg_value, sensor_colors)
        p95_text = self._get_colored_value(sensor_stats, sensor_stats.p95_value, sensor_colors)

        # Add row to table (units are now included in the values)
        table.add_row(
            display_name,
            last_text,
            min_text,
            max_text,
            avg_text,
            p95_text
        )

    def _get_display_name(self, sensor_name: str) -> str:
        """Get a display name for the sensor."""
        # Remove unit suffix if present
        import re
        name = re.sub(r'\s*\[[^\]]+\]', '', sensor_name).strip()

        # Let Rich handle wrapping/truncation based on available space
        return name

    def _get_colored_display_name(self, sensor_name: str, sensor_colors: dict[str, tuple]) -> Text:
        """Get a colored display name for the sensor matching its chart line color."""
        display_name = self._get_display_name(sensor_name)

        # Get the RGB color for this sensor from the chart
        rgb_color = sensor_colors.get(sensor_name, (255, 255, 255))  # Default to white

        # Create colored text using RGB
        color_style = f"rgb({rgb_color[0]},{rgb_color[1]},{rgb_color[2]})"
        return Text(display_name, style=f"bold {color_style}")

    def _get_colored_value(self, sensor_stats: SensorStats, value: float | None, sensor_colors: dict[str, tuple]) -> Text:
        """Get color-coded text for a value using sensor colors and including units."""
        if value is None:
            return Text("N/A", style="dim")

        formatted_value = sensor_stats._format_value(value)

        # Include unit in the formatted value
        if sensor_stats.display_unit:
            formatted_value_with_unit = f"{formatted_value}{sensor_stats.display_unit}"
        else:
            formatted_value_with_unit = formatted_value

        # Use sensor color instead of threshold-based color
        rgb_color = sensor_colors.get(sensor_stats.sensor_name, (255, 255, 255))
        color_style = f"rgb({rgb_color[0]},{rgb_color[1]},{rgb_color[2]})"

        return Text(formatted_value_with_unit, style=color_style)

    def _format_time_window(self, seconds: int) -> str:
        """Format time window for display."""
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

    def create_summary_line(self, stats: dict[str, SensorStats], units: set[str | None]) -> Text:
        """Create a summary line showing key information."""
        sensor_count = len(stats)
        unit_list = [unit if unit else "no unit" for unit in sorted(unit for unit in units if unit is not None)]

        if not unit_list:
            unit_str = "no units"
        elif len(unit_list) == 1:
            unit_str = f"unit [{unit_list[0]}]"
        else:
            unit_str = f"units [{'] and ['.join(unit_list)}]"

        summary = f"Monitoring {sensor_count} sensors with {unit_str}"

        return Text(summary, style="dim italic")

    def create_status_indicators(self, stats: dict[str, SensorStats]) -> Text:
        """Create status indicators for all sensors."""
        status_counts = {"normal": 0, "warning": 0, "critical": 0, "unknown": 0}

        for sensor_stats in stats.values():
            status = self.stats_calculator.get_threshold_status(sensor_stats)
            status_counts[status] += 1

        indicators = []

        if status_counts["critical"] > 0:
            indicators.append(Text(f"●{status_counts['critical']} Critical", style="red"))

        if status_counts["warning"] > 0:
            indicators.append(Text(f"●{status_counts['warning']} Warning", style="yellow"))

        if status_counts["normal"] > 0:
            indicators.append(Text(f"●{status_counts['normal']} Normal", style="green"))

        if status_counts["unknown"] > 0:
            indicators.append(Text(f"●{status_counts['unknown']} No Data", style="dim"))

        if not indicators:
            return Text("No sensors", style="dim")

        # Combine indicators
        result = Text("")
        for i, indicator in enumerate(indicators):
            if i > 0:
                result.append(" ", style="dim")
            result.append(indicator)

        return result


class CompactTable:
    """Compact version of the statistics table for smaller terminals."""

    def __init__(self, console: Console) -> None:
        """Initialize the compact table."""
        self.console = console
        self.stats_calculator = StatsCalculator()

    def create_table(self, stats: dict[str, SensorStats], sensor_colors: dict[str, tuple] | None = None) -> Table:
        """Create a compact table for smaller displays."""
        table = Table(
            show_header=True,
            header_style="bold",
            expand=True,
            box=None,
            width=None
        )

        # Add columns - Sensor expands to use available space
        table.add_column("Sensor", style="bold", no_wrap=True, min_width=15, ratio=3)
        table.add_column("Value", justify="right", min_width=12, max_width=20)

        # Add rows
        for sensor_stats in stats.values():
            if sensor_colors:
                display_name = self._get_colored_short_name(sensor_stats.sensor_name, sensor_colors)
            else:
                display_name = Text(self._get_short_name(sensor_stats.sensor_name))
            value_text = self._get_colored_value(sensor_stats, sensor_stats.last, sensor_colors or {})

            table.add_row(display_name, value_text)

        return table

    def _get_short_name(self, sensor_name: str) -> str:
        """Get display name for the sensor in compact view."""
        import re
        name = re.sub(r'\s*\[[^\]]+\]', '', sensor_name).strip()

        # Let Rich handle truncation based on available space
        return name

    def _get_colored_short_name(self, sensor_name: str, sensor_colors: dict[str, tuple]) -> Text:
        """Get a colored short name for the sensor."""
        short_name = self._get_short_name(sensor_name)
        rgb_color = sensor_colors.get(sensor_name, (255, 255, 255))
        color_style = f"rgb({rgb_color[0]},{rgb_color[1]},{rgb_color[2]})"
        return Text(short_name, style=f"bold {color_style}")

    def _get_colored_value(self, sensor_stats: SensorStats, value: float | None, sensor_colors: dict[str, tuple]) -> Text:
        """Get color-coded text for a value using sensor colors and including units."""
        if value is None:
            return Text("N/A", style="dim")

        formatted_value = sensor_stats._format_value(value)

        # Include unit in the formatted value
        if sensor_stats.display_unit:
            formatted_value_with_unit = f"{formatted_value}{sensor_stats.display_unit}"
        else:
            formatted_value_with_unit = formatted_value

        # Use sensor color instead of threshold-based color
        rgb_color = sensor_colors.get(sensor_stats.sensor_name, (255, 255, 255))
        color_style = f"rgb({rgb_color[0]},{rgb_color[1]},{rgb_color[2]})"

        return Text(formatted_value_with_unit, style=color_style)
