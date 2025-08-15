"""Plotext chart display for sensor data visualization."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

import plotext as plt
from rich.ansi import AnsiDecoder
from rich.console import Group
from rich.jupyter import JupyterMixin

from ..data.sensors import Sensor, SensorGroup
from ..utils.stats import SensorStats

logger = logging.getLogger(__name__)


class PlotextMixin(JupyterMixin):
    """Mixin class to render plotext charts in Rich panels."""
    
    def __init__(
        self,
        sensors: Dict[str, Sensor],
        sensor_groups: List[SensorGroup],
        time_window_seconds: int = 300,
        title: str = "Hardware Sensor Monitoring",
    sensor_colors: Optional[Dict[str, tuple]] = None
    ) -> None:
        """Initialize the plotext mixin."""
        self.sensors = sensors
        self.sensor_groups = sensor_groups
        self.time_window_seconds = time_window_seconds
        self.title = title
        self.decoder = AnsiDecoder()
        # Use provided sensor colors from layout
        self.sensor_colors = sensor_colors or {}
    
    def __rich_console__(self, console, options):
        """Render the plotext chart for Rich console."""
        try:
            # Get available dimensions
            width = options.max_width or console.width
            height = options.height or 15  # Default height
            
            # Create the plotext chart
            chart_str = self._create_plotext_chart(width, height)
            
            # Decode ANSI and render
            rich_canvas = Group(*self.decoder.decode(chart_str))
            yield rich_canvas
            
        except Exception as e:
            logger.error(f"Failed to render chart: {e}")
            # Fallback to simple text
            yield f"Chart error: {str(e)}"
    
    def _create_plotext_chart(self, width: int, height: int) -> str:
        """Create a plotext chart and return as string."""
        plt.clear_data()
        plt.clear_color()
        
        # Configure plot size to use all available space
        chart_width = max(width - 2, 40)  # Minimal margin for text wrapping
        chart_height = max(height - 2, 10)  # Minimal margin for title/labels
        plt.plotsize(chart_width, chart_height)
        
        # Color mappings are provided by layout
        
        # Check if we have data
        if not self.sensors:
            return self._create_empty_chart(chart_width, chart_height)
        
        # Get time range
        latest_time = self._get_latest_timestamp()
        if latest_time is None:
            return self._create_empty_chart(chart_width, chart_height)
        
        start_time = latest_time - timedelta(seconds=self.time_window_seconds)
        
        # Plot data with dual axis support
        dual_axis_mode = len(self.sensor_groups) == 2
        
        if dual_axis_mode:
            # Plot first group on left axis
            if len(self.sensor_groups) > 0:
                left_sensors = {name: self.sensors[name] for name in self.sensor_groups[0].sensor_names if name in self.sensors}
                for sensor_name, sensor in left_sensors.items():
                    timestamps, values = self._get_sensor_data_in_range(sensor, start_time, latest_time)
                    if timestamps and values:
                        time_values = [(ts - start_time).total_seconds() for ts in timestamps]
                        color = self._rgb_to_plotext_color(self.sensor_colors.get(sensor_name, (255, 255, 255)))
                        try:
                            plt.plot(time_values, values, color=color, marker="braille", xside="lower", yside="left")
                        except Exception as e:
                            logger.warning(f"Failed to plot {sensor_name}: {e}")
            
            # Plot second group on right axis
            if len(self.sensor_groups) > 1:
                right_sensors = {name: self.sensors[name] for name in self.sensor_groups[1].sensor_names if name in self.sensors}
                for sensor_name, sensor in right_sensors.items():
                    timestamps, values = self._get_sensor_data_in_range(sensor, start_time, latest_time)
                    if timestamps and values:
                        time_values = [(ts - start_time).total_seconds() for ts in timestamps]
                        color = self._rgb_to_plotext_color(self.sensor_colors.get(sensor_name, (255, 255, 255)))
                        try:
                            plt.plot(time_values, values, color=color, marker="braille", xside="lower", yside="right")
                        except Exception as e:
                            logger.warning(f"Failed to plot {sensor_name}: {e}")
        else:
            # Single axis mode
            for sensor_name, sensor in self.sensors.items():
                if not sensor.readings:
                    continue
                
                timestamps, values = self._get_sensor_data_in_range(sensor, start_time, latest_time)
                if not timestamps or not values:
                    continue
                
                # Convert to relative time
                time_values = [(ts - start_time).total_seconds() for ts in timestamps]
                
                # Plot with error handling
                color = self._rgb_to_plotext_color(self.sensor_colors.get(sensor_name, (255, 255, 255)))
                
                try:
                    # Use line plot with braille markers
                    plt.plot(time_values, values, color=color, marker="braille")
                except Exception as e:
                    logger.warning(f"Failed to plot {sensor_name}: {e}")
                    continue
        
        # Configure y-axis ticks with units
        self._configure_y_ticks_with_units(dual_axis_mode)
        
        # Configure chart with HH:mm:ss tick labels
        self._configure_chart_with_time_ticks(start_time, latest_time)
        
        # Build and return
        try:
            return plt.build()
        except Exception as e:
            logger.error(f"Failed to build chart: {e}")
            return self._create_error_chart(str(e), chart_width, chart_height)
    
    def _rgb_to_plotext_color(self, rgb_tuple: tuple) -> Any:
        """Convert RGB tuple to plotext color format."""
        r, g, b = rgb_tuple
        # Plotext supports RGB colors as tuples or as color names
        # For better compatibility, we'll map to the closest standard color
        color_map = {
            (255, 100, 100): "red",      # Bright red
            (100, 255, 100): "green",    # Bright green  
            (100, 150, 255): "blue",     # Bright blue
            (255, 255, 100): "yellow",   # Bright yellow
            (255, 100, 255): "magenta",  # Bright magenta
            (100, 255, 255): "cyan",     # Bright cyan
            (255, 180, 100): "orange",   # Orange
            (180, 100, 255): "violet",   # Purple
        }
        
        # Return the mapped color or use RGB tuple format for plotext
        mapped_color = color_map.get(rgb_tuple)
        if mapped_color:
            return mapped_color
        else:
            # Try to use RGB tuple directly (plotext may accept this)
            return rgb_tuple
    
    def _get_latest_timestamp(self) -> Optional[datetime]:
        """Get the latest timestamp across all sensors."""
        latest = None
        for sensor in self.sensors.values():
            sensor_latest = sensor.latest_timestamp
            if sensor_latest is not None:
                if latest is None or sensor_latest > latest:
                    latest = sensor_latest
        return latest
    
    def _get_sensor_data_in_range(
        self, sensor: Sensor, start_time: datetime, end_time: datetime
    ) -> Tuple[List[datetime], List[float]]:
        """Get sensor data within time range."""
        import math
        timestamps, values = [], []
        for reading in sensor.readings:
            if start_time <= reading.timestamp <= end_time:
                # Filter out NaN and infinite values
                if not (math.isnan(reading.value) or math.isinf(reading.value)):
                    timestamps.append(reading.timestamp)
                    values.append(reading.value)
        return timestamps, values
    
    
    def _get_display_name(self, sensor_name: str) -> str:
        """Get display name for sensor."""
        import re
        name = re.sub(r'\s*\[[^\]]+\]', '', sensor_name).strip()
        if len(name) > 20:
            name = name[:17] + "..."
        return name
    
    def _configure_chart_with_time_ticks(self, start_time: datetime, end_time: datetime) -> None:
        """Configure chart appearance and set x-axis to actual timestamps (HH:mm:ss)."""
        # Keep x domain in seconds since start of window
        plt.xlim(0, self.time_window_seconds)
        
        # Build evenly spaced tick positions over the window
        try:
            # Choose a reasonable number of ticks based on window length
            # Aim for 3 ticks inclusive of both ends
            num_ticks = 3
            step = self.time_window_seconds / max(1, (num_ticks - 1))
            positions = [round(i * step, 2) for i in range(num_ticks)]
            # Ensure last tick aligns to window end
            positions[-1] = float(self.time_window_seconds)
            # Map positions to absolute timestamps
            from datetime import timedelta as _td
            labels = [(start_time + _td(seconds=pos)).strftime("%H:%M:%S") for pos in positions]
            # Apply ticks with labels
            try:
                plt.xticks(positions, labels)
            except Exception:
                # If xticks API is unavailable, silently continue
                pass
        except Exception:
            # Fallback: no custom ticks
            pass
        
    # No x-axis label or legend per request
    
    def _configure_y_ticks_with_units(self, dual_axis_mode: bool) -> None:
        """Configure y-axis ticks with unit-formatted labels."""
        try:
            if dual_axis_mode and len(self.sensor_groups) >= 2:
                # Dual-axis mode: set custom ticks for both left and right axes
                self._set_axis_ticks_with_units(self.sensor_groups[0], "left")
                self._set_axis_ticks_with_units(self.sensor_groups[1], "right")
                
            elif len(self.sensor_groups) >= 1:
                # Single-axis mode: set ticks for primary axis
                self._set_axis_ticks_with_units(self.sensor_groups[0], "left")
                
        except Exception as e:
            logger.warning(f"Failed to configure y-axis ticks with units: {e}")
    
    def _set_axis_ticks_with_units(self, sensor_group, axis_side: str) -> None:
        """Set y-axis ticks with units for a specific axis side."""
        try:
            # Get data range from sensors in this group
            min_val, max_val = self._get_sensor_group_range(sensor_group)
            
            if min_val is None or max_val is None:
                return
            
            # Generate appropriate tick positions
            tick_positions = self._generate_tick_positions(min_val, max_val)
            
            # Format tick labels with units
            unit = sensor_group.unit
            if unit:
                tick_labels = [f"{pos:.1f}{unit}" for pos in tick_positions]
            else:
                tick_labels = [f"{pos:.1f}" for pos in tick_positions]
            
            # Apply ticks to the specified axis
            if axis_side == "right":
                plt.yticks(tick_positions, tick_labels, yside="right")
            else:
                plt.yticks(tick_positions, tick_labels, yside="left")
                
        except Exception as e:
            logger.warning(f"Failed to set {axis_side} axis ticks: {e}")
    
    def _get_sensor_group_range(self, sensor_group) -> tuple:
        """Get the min/max value range for sensors in a group."""
        try:
            all_values = []
            for sensor in sensor_group.sensors:
                if sensor.readings:
                    all_values.extend(sensor.values)
            
            if not all_values:
                return None, None
                
            return min(all_values), max(all_values)
            
        except Exception:
            return None, None
    
    def _generate_tick_positions(self, min_val: float, max_val: float, num_ticks: int = 6) -> list:
        """Generate evenly distributed tick positions between min and max values."""
        try:
            if min_val == max_val:
                return [min_val]
            
            # Add some padding to the range
            range_size = max_val - min_val
            padding = range_size * 0.1
            
            start = min_val - padding
            end = max_val + padding
            
            # Generate evenly spaced positions
            if num_ticks <= 1:
                return [start]
                
            step = (end - start) / (num_ticks - 1)
            positions = [start + i * step for i in range(num_ticks)]
            
            return positions
            
        except Exception:
            return [min_val, max_val]
        
    def _create_empty_chart(self, width: int, height: int) -> str:
        """Create empty chart placeholder."""
        plt.clear_data()
        plt.plotsize(width, height)
        return plt.build()
    
    def _create_error_chart(self, error: str, width: int, height: int) -> str:
        """Create error chart placeholder."""
        plt.clear_data()
        plt.plotsize(width, height)
        return plt.build()


class SensorChart:
    """Chart display for sensor data using plotext with Rich integration."""
    
    def __init__(self) -> None:
        """Initialize the sensor chart."""
        self.dual_axis_mode = False
        # Basic fallback color palette for internal helpers
        self.colors = ["red", "green", "blue", "yellow", "magenta", "cyan", "white"]
        
    def create_chart(
        self,
        sensors: Dict[str, Sensor],
        sensor_groups: List[SensorGroup],
        time_window_seconds: int = 300,
        width: Optional[int] = None,
        height: Optional[int] = None,
        sensor_colors: Optional[Dict[str, tuple]] = None,
    ) -> PlotextMixin:
        """Create a chart mixin for Rich display."""
        chart_mixin = PlotextMixin(
            sensors=sensors,
            sensor_groups=sensor_groups,
            time_window_seconds=time_window_seconds,
            sensor_colors=sensor_colors or {}
        )
        # Store the mixin so we can access color mappings later
        self.current_chart = chart_mixin
        return chart_mixin
    
    def get_sensor_colors(self) -> Dict[str, tuple]:
        """Get the current sensor to color mapping."""
        if hasattr(self, 'current_chart'):
            return self.current_chart.sensor_colors
        return {}
    
    def _plot_single_axis_sensors(
        self,
        sensors: Dict[str, Sensor],
        sensor_group: Optional[SensorGroup],
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """Plot sensors on a single y-axis."""
        self.color_index = 0
        
        for sensor_name, sensor in sensors.items():
            if not sensor.readings:
                continue
            
            # Get data within time window
            timestamps, values = self._get_sensor_data_in_range(sensor, start_time, end_time)
            
            if not timestamps or not values:
                continue
            
            # Convert timestamps to relative seconds
            time_values = [(ts - start_time).total_seconds() for ts in timestamps]
            
            # Plot line with better visibility
            color = self._get_next_color()
            display_name = self._get_display_name(sensor_name)
            
            # Use scatter plot with ASCII marker for better compatibility
            try:
                plt.scatter(time_values, values, label=display_name, color=color, marker="dot")
            except:
                # Fallback to just line plot if scatter fails
                plt.plot(time_values, values, label=display_name, color=color)
            
            # Always add a line for trend visibility
            if len(time_values) > 1:
                plt.plot(time_values, values, color=color)
    
    def _plot_dual_axis_sensors(
        self,
        sensors: Dict[str, Sensor],
        sensor_groups: List[SensorGroup],
        start_time: datetime,
        end_time: datetime
    ) -> None:
        """Plot sensors on dual y-axes."""
        self.color_index = 0
        
        # Plot left axis sensors (first group)
        if len(sensor_groups) > 0:
            left_sensors = {name: sensors[name] for name in sensor_groups[0].sensor_names if name in sensors}
            for sensor_name, sensor in left_sensors.items():
                timestamps, values = self._get_sensor_data_in_range(sensor, start_time, end_time)
                if timestamps and values:
                    time_values = [(ts - start_time).total_seconds() for ts in timestamps]
                    color = self._get_next_color()
                    display_name = self._get_display_name(sensor_name)
                    try:
                        plt.scatter(time_values, values, label=display_name, color=color, marker="dot")
                    except:
                        plt.plot(time_values, values, label=display_name, color=color)
                    if len(time_values) > 1:
                        plt.plot(time_values, values, color=color)
        
        # Switch to right axis for second group
        if len(sensor_groups) > 1:
            # Try to use twinx if available
            twinx = getattr(plt, "twinx", None)
            if callable(twinx):
                try:
                    twinx()
                except Exception:
                    pass
            
            right_sensors = {name: sensors[name] for name in sensor_groups[1].sensor_names if name in sensors}
            for sensor_name, sensor in right_sensors.items():
                timestamps, values = self._get_sensor_data_in_range(sensor, start_time, end_time)
                if timestamps and values:
                    time_values = [(ts - start_time).total_seconds() for ts in timestamps]
                    color = self._get_next_color()
                    display_name = self._get_display_name(sensor_name)
                    try:
                        plt.scatter(time_values, values, label=display_name, color=color, marker="dot")
                    except:
                        plt.plot(time_values, values, label=display_name, color=color)
                    if len(time_values) > 1:
                        plt.plot(time_values, values, color=color)
    
    def _get_sensor_data_in_range(
        self,
        sensor: Sensor,
        start_time: datetime,
        end_time: datetime
    ) -> Tuple[List[datetime], List[float]]:
        """Get sensor data within the specified time range."""
        timestamps = []
        values = []
        
        for reading in sensor.readings:
            if start_time <= reading.timestamp <= end_time:
                timestamps.append(reading.timestamp)
                values.append(reading.value)
        
        return timestamps, values
    
    def _configure_chart(self, sensor_groups: List[SensorGroup], time_window_seconds: int) -> None:
        """Configure chart appearance and labels (no x label, no legend)."""
        # Title based on units present
        if sensor_groups:
            units = [group.unit for group in sensor_groups if group.unit]
            if len(units) == 1:
                title = f"Hardware Sensor Monitoring - [{units[0]}]"
            elif len(units) == 2:
                title = f"Hardware Sensor Monitoring - [{units[0]}] & [{units[1]}]"
            else:
                title = "Hardware Sensor Monitoring"
        else:
            title = "Hardware Sensor Monitoring"

        plt.title(title)

        # X-axis: time window limits only (no label)
        plt.xlim(0, time_window_seconds)

        # Y-axis label based on first group's unit if available
        if sensor_groups and len(sensor_groups) >= 1:
            unit = sensor_groups[0].unit
            if unit:
                plt.ylabel(f"Value ({unit})")
            else:
                plt.ylabel("Value")
        else:
            plt.ylabel("Value")

        plt.theme("dark")
        # No legend per request
    
    def _get_latest_timestamp(self, sensors: Dict[str, Sensor]) -> Optional[datetime]:
        """Get the latest timestamp across all sensors."""
        latest = None
        
        for sensor in sensors.values():
            sensor_latest = sensor.latest_timestamp
            if sensor_latest is not None:
                if latest is None or sensor_latest > latest:
                    latest = sensor_latest
        
        return latest
    
    def _get_next_color(self) -> str:
        """Get the next color from the color palette."""
        color = self.colors[self.color_index % len(self.colors)]
        self.color_index += 1
        return color
    
    def _get_display_name(self, sensor_name: str) -> str:
        """Get a display name for the sensor (shortened if needed)."""
        import re
        # Remove unit suffix
        name = re.sub(r'\s*\[[^\]]+\]', '', sensor_name).strip()
        
        # Shorten for legend display
        if len(name) > 20:
            name = name[:17] + "..."
        
        return name
    
    def _create_empty_chart(self, width: Optional[int] = None, height: Optional[int] = None) -> str:
        """Create an empty chart placeholder."""
        plt.clear_data()
        plt.clear_color()

        # Apply same sizing logic as main chart
        if width and height:
            plt.limit_size(False, False)
            chart_width = max(width - 8, 40)
            chart_height = max(height - 6, 10)
        else:
            plt.limit_size(True, True)
            term_w = getattr(plt, "terminal_width", lambda: 80)() or 80
            term_h = getattr(plt, "terminal_height", lambda: 24)() or 24
            chart_width = max(term_w - 10, 50)
            chart_height = max(term_h // 2, 15)

        plt.plotsize(chart_width, chart_height)
        plt.title("No Data Available")
        # No x-axis label per request
        plt.ylabel("Value")

        try:
            # Add placeholder text
            plt.text(chart_width // 2, chart_height // 2, "No sensor data to display", alignment="center")
            return plt.build()
        except Exception:
            return "No data available"
    
    def _create_error_chart(self, error_message: str, width: Optional[int] = None, height: Optional[int] = None) -> str:
        """Create an error chart placeholder."""
        plt.clear_data()
        plt.clear_color()

        # Apply same sizing logic as main chart
        if width and height:
            plt.limit_size(False, False)
            chart_width = max(width - 8, 40)
            chart_height = max(height - 6, 10)
        else:
            plt.limit_size(True, True)
            term_w = getattr(plt, "terminal_width", lambda: 80)() or 80
            term_h = getattr(plt, "terminal_height", lambda: 24)() or 24
            chart_width = max(term_w - 10, 50)
            chart_height = max(term_h // 2, 15)

        plt.plotsize(chart_width, chart_height)
        plt.title("Chart Error")
        # No x-axis label per request
        plt.ylabel("Value")

        try:
            # Add error message
            plt.text(chart_width // 2, chart_height // 2, f"Error: {error_message[:30]}", alignment="center")
            return plt.build()
        except Exception:
            return f"Chart error: {error_message}"


class MiniChart:
    """Minimalistic chart for compact display."""
    
    def __init__(self) -> None:
        """Initialize the mini chart."""
        self.colors = ["red", "green", "blue", "yellow"]
        
    def create_sparkline(self, sensor: Sensor, width: int = 40) -> str:
        """Create a sparkline for a single sensor."""
        if not sensor.readings or len(sensor.readings) < 2:
            return "─" * width
        
        # Get last N values for the sparkline
        values = sensor.values[-width:]
        
        if not values:
            return "─" * width
        
        # Normalize values to sparkline characters
        min_val = min(values)
        max_val = max(values)
        
        if max_val == min_val:
            return "─" * len(values)
        
        # Sparkline characters from low to high
        chars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
        
        sparkline = ""
        for value in values:
            normalized = (value - min_val) / (max_val - min_val)
            char_index = min(int(normalized * len(chars)), len(chars) - 1)
            sparkline += chars[char_index]
        
        return sparkline
    
    def create_trend_indicator(self, sensor: Sensor) -> str:
        """Create a trend indicator for a sensor."""
        if len(sensor.readings) < 3:
            return "→"
        
        recent_values = sensor.values[-5:]  # Look at last 5 values
        
        if len(recent_values) < 2:
            return "→"
        
        # Calculate trend
        first_half = recent_values[:len(recent_values)//2]
        second_half = recent_values[len(recent_values)//2:]
        
        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)
        
        diff_percent = ((avg_second - avg_first) / avg_first * 100) if avg_first != 0 else 0
        
        if diff_percent > 5:
            return "↗"  # Rising
        elif diff_percent < -5:
            return "↘"  # Falling
        else:
            return "→"  # Stable