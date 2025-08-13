"""Rich table display for sensor statistics."""

from __future__ import annotations

from typing import Dict, List, Optional, Set

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
        stats: Dict[str, SensorStats], 
        sensor_groups: List[SensorGroup],
        time_window: int = 300,
        sensor_colors: Dict[str, tuple] = None
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
        
        # Add columns
        table.add_column("Sensor", style="bold", no_wrap=True, min_width=20)
        table.add_column("Last", justify="right", min_width=8)
        table.add_column("Min", justify="right", min_width=8)
        table.add_column("Max", justify="right", min_width=8)
        table.add_column("Avg", justify="right", min_width=8)
        table.add_column("P95", justify="right", min_width=8)
        table.add_column("Unit", justify="center", min_width=6)
        
        # Add sensor rows directly (no grouping)
        for sensor_stats in stats.values():
            self._add_sensor_row(table, sensor_stats, sensor_colors or {})
        
        return table
    
    def _group_stats_by_unit(
        self, 
        stats: Dict[str, SensorStats], 
        sensor_groups: List[SensorGroup]
    ) -> Dict[Optional[str], List[SensorStats]]:
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
    
    def _add_sensor_row(self, table: Table, sensor_stats: SensorStats, sensor_colors: Dict[str, tuple]) -> None:
        """Add a row for a single sensor to the table."""
        # Get display name (remove unit suffix) with color coding
        display_name = self._get_colored_display_name(sensor_stats.sensor_name, sensor_colors)
        
        # Get color-coded values
        last_text = self._get_colored_value(sensor_stats, sensor_stats.last)
        min_text = self._get_colored_value(sensor_stats, sensor_stats.min_value)
        max_text = self._get_colored_value(sensor_stats, sensor_stats.max_value)
        avg_text = self._get_colored_value(sensor_stats, sensor_stats.avg_value)
        p95_text = self._get_colored_value(sensor_stats, sensor_stats.p95_value)
        
        # Unit display
        unit_text = Text(sensor_stats.display_unit, style="dim")
        
        # Add row to table
        table.add_row(
            display_name,
            last_text,
            min_text,
            max_text,
            avg_text,
            p95_text,
            unit_text
        )
    
    def _get_display_name(self, sensor_name: str) -> str:
        """Get a shortened display name for the sensor."""
        # Remove unit suffix if present
        import re
        name = re.sub(r'\s*\[[^\]]+\]', '', sensor_name).strip()
        
        # Shorten long names
        if len(name) > 25:
            name = name[:22] + "..."
        
        return name
    
    def _get_colored_display_name(self, sensor_name: str, sensor_colors: Dict[str, tuple]) -> Text:
        """Get a colored display name for the sensor matching its chart line color."""
        display_name = self._get_display_name(sensor_name)
        
        # Get the RGB color for this sensor from the chart
        rgb_color = sensor_colors.get(sensor_name, (255, 255, 255))  # Default to white
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Sensor '{sensor_name}' -> RGB color {rgb_color}")
        
        # Create colored text using RGB
        from rich.color import Color
        color = Color.from_rgb(rgb_color[0], rgb_color[1], rgb_color[2])
        return Text(display_name, style=f"bold {color}")
    
    def _get_colored_value(self, sensor_stats: SensorStats, value: Optional[float]) -> Text:
        """Get color-coded text for a value."""
        if value is None:
            return Text("N/A", style="dim")
        
        formatted_value = sensor_stats._format_value(value)
        color = self.stats_calculator.get_color_for_value(sensor_stats, value)
        
        return Text(formatted_value, style=color)
    
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
    
    def create_summary_line(self, stats: Dict[str, SensorStats], units: Set[Optional[str]]) -> Text:
        """Create a summary line showing key information."""
        sensor_count = len(stats)
        unit_list = [unit if unit else "no unit" for unit in sorted(units) if unit is not None]
        
        if not unit_list:
            unit_str = "no units"
        elif len(unit_list) == 1:
            unit_str = f"unit [{unit_list[0]}]"
        else:
            unit_str = f"units [{'] and ['.join(unit_list)}]"
        
        summary = f"Monitoring {sensor_count} sensors with {unit_str}"
        
        return Text(summary, style="dim italic")
    
    def create_status_indicators(self, stats: Dict[str, SensorStats]) -> Text:
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
    
    def create_table(self, stats: Dict[str, SensorStats]) -> Table:
        """Create a compact table for smaller displays."""
        table = Table(
            show_header=True,
            header_style="bold",
            expand=True,
            box=None,
            width=None
        )
        
        # Add columns
        table.add_column("Sensor", style="bold", no_wrap=True, min_width=15)
        table.add_column("Value", justify="right", min_width=8)
        table.add_column("Unit", justify="center", min_width=4)
        
        # Add rows
        for sensor_stats in stats.values():
            display_name = self._get_short_name(sensor_stats.sensor_name)
            value_text = self._get_colored_value(sensor_stats, sensor_stats.last)
            unit_text = Text(sensor_stats.display_unit, style="dim")
            
            table.add_row(display_name, value_text, unit_text)
        
        return table
    
    def _get_short_name(self, sensor_name: str) -> str:
        """Get a very short name for the sensor."""
        import re
        name = re.sub(r'\s*\[[^\]]+\]', '', sensor_name).strip()
        
        # Very aggressive shortening for compact view
        if len(name) > 15:
            name = name[:12] + "..."
        
        return name
    
    def _get_colored_value(self, sensor_stats: SensorStats, value: Optional[float]) -> Text:
        """Get color-coded text for a value."""
        if value is None:
            return Text("N/A", style="dim")
        
        formatted_value = sensor_stats._format_value(value)
        color = self.stats_calculator.get_color_for_value(sensor_stats, value)
        
        return Text(formatted_value, style=color)