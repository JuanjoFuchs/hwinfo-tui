"""Plotext chart display for sensor data visualization."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

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
        sensor_colors: Dict[str, tuple] = None
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
                        color = self.sensor_colors[sensor_name]  # Use RGB color
                        display_name = self._get_display_name(sensor_name)
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
                        color = self.sensor_colors[sensor_name]  # Use RGB color
                        display_name = self._get_display_name(sensor_name)
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
                color = self.sensor_colors[sensor_name]  # Use RGB color
                display_name = self._get_display_name(sensor_name)
                
                try:
                    # Use line plot with braille markers
                    plt.plot(time_values, values, color=color, marker="braille")
                except Exception as e:
                    logger.warning(f"Failed to plot {sensor_name}: {e}")
                    continue
        
        # Configure chart
        self._configure_chart()
        
        # Debug: Log RGB color mappings
        logger.info(f"RGB color mappings: {self.sensor_colors}")
        
        # Build and return
        try:
            return plt.build()
        except Exception as e:
            logger.error(f"Failed to build chart: {e}")
            return self._create_error_chart(str(e), chart_width, chart_height)
    
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
    
    def _configure_chart(self) -> None:
        """Configure chart appearance - minimal interface."""
        # Set time range only
        plt.xlim(0, self.time_window_seconds)
        
        # Grid for data reading
        # plt.grid(True)
        
        # Show legend for data identification
        # try:
        #     plt.show_legend()
        # except (AttributeError, TypeError):
        #     pass
    
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
        
    def create_chart(
        self,
        sensors: Dict[str, Sensor],
        sensor_groups: List[SensorGroup],
        time_window_seconds: int = 300,
        width: Optional[int] = None,
        height: Optional[int] = None,
        sensor_colors: Dict[str, tuple] = None
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
    
    def get_sensor_colors(self) -> Dict[str, str]:
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
            try:
                plt.twinx()  # Try to use twinx if available
            except AttributeError:
                # Fallback: just plot on same axis with different colors
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
        """Configure chart appearance and labels."""
        # Set simplified title
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
        
        # Configure x-axis (time) - use relative time from now
        plt.xlabel("Time (s ago)")
        plt.xlim(0, time_window_seconds)
        
        # Configure y-axis labels (simplified)
        if sensor_groups and len(sensor_groups) >= 1:
            unit = sensor_groups[0].unit
            if unit:
                plt.ylabel(f"Value ({unit})")
            else:
                plt.ylabel("Value")
        else:
            plt.ylabel("Value")
        
        # Simplified grid and theme
        plt.grid(True)
        plt.theme("dark")
        
        # Try to show legend if available
        try:
            plt.show_legend()
        except (AttributeError, TypeError):
            # Fallback if legend methods don't work
            pass
    
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
            chart_width = max(plt.terminal_width() - 10, 50)
            chart_height = max(plt.terminal_height() // 2, 15)
        
        plt.plotsize(chart_width, chart_height)
        plt.title("No Data Available")
        plt.xlabel("Time")
        plt.ylabel("Value")
        
        try:
            # Add placeholder text
            plt.text(chart_width//2, chart_height//2, "No sensor data to display", alignment="center")
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
            chart_width = max(plt.terminal_width() - 10, 50)
            chart_height = max(plt.terminal_height() // 2, 15)
        
        plt.plotsize(chart_width, chart_height)
        plt.title("Chart Error")
        plt.xlabel("Time")
        plt.ylabel("Value")
        
        try:
            # Add error message
            plt.text(chart_width//2, chart_height//2, f"Error: {error_message[:30]}", alignment="center")
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