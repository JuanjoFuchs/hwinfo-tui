"""Plotext chart display for sensor data visualization."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Generator

import plotext as plt
from rich.ansi import AnsiDecoder
from rich.console import Console, ConsoleOptions, Group, RenderableType
from rich.jupyter import JupyterMixin

from ..data.sensors import Sensor, SensorGroup

logger = logging.getLogger(__name__)


class PlotextMixin(JupyterMixin):
    """Mixin class to render plotext charts in Rich panels."""

    def __init__(
        self,
        sensors: dict[str, Sensor],
        sensor_groups: list[SensorGroup],
        time_window_seconds: int = 300,
        title: str = "Hardware Sensor Monitoring",
        sensor_colors: dict[str, tuple] | None = None,
        explicit_height: int | None = None
    ) -> None:
        """Initialize the plotext mixin."""
        self.sensors = sensors
        self.sensor_groups = sensor_groups
        self.time_window_seconds = time_window_seconds
        self.title = title
        self.decoder = AnsiDecoder()
        # Use provided sensor colors from layout
        self.sensor_colors = sensor_colors or {}
        # Store explicit height if provided
        self.explicit_height = explicit_height

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> Generator[RenderableType, None, None]:
        """Render the plotext chart for Rich console."""
        try:
            # Get available dimensions
            width = options.max_width or console.width
            # Use explicit height if provided, otherwise fall back to options or default
            height = self.explicit_height or options.height or 15

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

        # Disable plotext's default size limiter to allow charts larger than ~25 lines
        plt.limit_size(False, False)

        # Configure plot size to use all available space
        chart_width = max(width - 2, 40)  # Minimal margin for text wrapping
        chart_height = max(height, 10)  # Use full height allocated by layout
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
                        color = self.sensor_colors.get(sensor_name, (255, 255, 255))
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
                        color = self.sensor_colors.get(sensor_name, (255, 255, 255))
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
                color = self.sensor_colors.get(sensor_name, (255, 255, 255))

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
            return plt.build()  # type: ignore  # type: ignore
        except Exception as e:
            logger.error(f"Failed to build chart: {e}")
            return self._create_error_chart(str(e), chart_width, chart_height)

    def _get_latest_timestamp(self) -> datetime | None:
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
    ) -> tuple[list[datetime], list[float]]:
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

    def _set_axis_ticks_with_units(self, sensor_group: SensorGroup, axis_side: str) -> None:
        """Set y-axis ticks with units for a specific axis side."""
        try:
            unit = sensor_group.unit

            # Special handling for Yes/No sensors
            if unit == "Yes/No":
                # Set exactly 2 ticks: No at 0, Yes at 1
                tick_positions = [0.0, 1.0]
                tick_labels = ["No", "Yes"]
                # Constrain Y-axis to [0, 1] range to ensure No is at bottom
                plt.ylim(0.0, 1.0, yside=axis_side)
            else:
                # Get data range from sensors in this group
                min_val, max_val = self._get_sensor_group_range(sensor_group)

                if min_val is None or max_val is None:
                    return

                # Generate appropriate tick positions
                tick_positions = self._generate_tick_positions(min_val, max_val)

                # Format tick labels with units
                if unit:
                    tick_labels = [f"{pos:.1f}{unit}" for pos in tick_positions]
                else:
                    tick_labels = [f"{pos:.1f}" for pos in tick_positions]

            # Apply ticks to the specified axis
            plt.yticks(tick_positions, tick_labels, yside=axis_side)

        except Exception as e:
            logger.warning(f"Failed to set {axis_side} axis ticks: {e}")

    def _get_sensor_group_range(self, sensor_group: SensorGroup) -> tuple[float | None, float | None]:
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
        plt.limit_size(False, False)
        plt.plotsize(width, height)
        return plt.build()  # type: ignore

    def _create_error_chart(self, error: str, width: int, height: int) -> str:
        """Create error chart placeholder."""
        plt.clear_data()
        plt.limit_size(False, False)
        plt.plotsize(width, height)
        return plt.build()  # type: ignore


class SensorChart:
    """Chart display for sensor data using plotext with Rich integration."""

    def __init__(self) -> None:
        """Initialize the sensor chart."""
        pass

    def create_chart(
        self,
        sensors: dict[str, Sensor],
        sensor_groups: list[SensorGroup],
        time_window_seconds: int = 300,
        width: int | None = None,
        height: int | None = None,
        sensor_colors: dict[str, tuple] | None = None,
    ) -> PlotextMixin:
        """Create a chart mixin for Rich display."""
        chart_mixin = PlotextMixin(
            sensors=sensors,
            sensor_groups=sensor_groups,
            time_window_seconds=time_window_seconds,
            sensor_colors=sensor_colors or {},
            explicit_height=height
        )
        # Store the mixin so we can access color mappings later
        self.current_chart = chart_mixin
        return chart_mixin

    def get_sensor_colors(self) -> dict[str, tuple]:
        """Get the current sensor to color mapping."""
        if hasattr(self, 'current_chart'):
            return self.current_chart.sensor_colors
        return {}


