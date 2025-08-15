"""Configuration management for HWInfo TUI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib  # type: ignore # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python versions
    except ImportError:
        import toml as tomllib  # Final fallback


@dataclass
class DisplayConfig:
    """Configuration for display settings."""
    refresh_rate: float = 1.0
    theme: str = "default"
    time_window: int = 300


@dataclass
class SensorThresholds:
    """Configuration for sensor thresholds."""
    cpu_temp_critical: float = 85.0
    cpu_temp_warning: float = 75.0
    gpu_temp_critical: float = 90.0
    gpu_temp_warning: float = 80.0
    cpu_usage_warning: float = 80.0
    cpu_usage_critical: float = 95.0
    memory_usage_warning: float = 80.0
    memory_usage_critical: float = 90.0
    cpu_power_warning: float = 100.0
    cpu_power_critical: float = 200.0
    gpu_power_warning: float = 250.0
    gpu_power_critical: float = 400.0


@dataclass
class ChartConfig:
    """Configuration for chart settings."""
    default_type: str = "line"
    smooth_updates: bool = True
    auto_scale: bool = True
    max_data_points: int = 3600
    dual_axis_threshold: int = 2


@dataclass
class UIConfig:
    """Configuration for UI settings."""
    compact_mode_width: int = 100
    compact_mode_height: int = 20
    show_legend: bool = True
    show_grid: bool = True
    animation_speed: str = "normal"


@dataclass
class AlertConfig:
    """Configuration for alert settings."""
    enable_visual_alerts: bool = True
    enable_audio_alerts: bool = False
    blink_critical_values: bool = True
    critical_color: str = "red"
    warning_color: str = "yellow"
    normal_color: str = "green"


@dataclass
class HWInfoConfig:
    """Main configuration class for HWInfo TUI."""
    display: DisplayConfig = field(default_factory=DisplayConfig)
    sensors: SensorThresholds = field(default_factory=SensorThresholds)
    charts: ChartConfig = field(default_factory=ChartConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)

    @classmethod
    def load_from_file(cls, config_path: Path | None = None) -> HWInfoConfig:
        """Load configuration from a TOML file."""
        if config_path is None:
            config_path = cls.find_config_file()

        if config_path and config_path.exists():
            try:
                with open(config_path, 'rb') as f:
                    data = tomllib.load(f)
                return cls.from_dict(data)
            except Exception:
                # If config loading fails, return default config
                return cls()

        return cls()

    @classmethod
    def from_dict(cls, data: dict) -> HWInfoConfig:
        """Create configuration from dictionary."""
        config = cls()

        # Load display settings
        if 'display' in data:
            display_data = data['display']
            config.display = DisplayConfig(
                refresh_rate=display_data.get('refresh_rate', 1.0),
                theme=display_data.get('theme', 'default'),
                time_window=display_data.get('time_window', 300)
            )

        # Load sensor thresholds
        if 'sensors' in data:
            sensor_data = data['sensors']
            config.sensors = SensorThresholds(
                cpu_temp_critical=sensor_data.get('cpu_temp_critical', 85.0),
                cpu_temp_warning=sensor_data.get('cpu_temp_warning', 75.0),
                gpu_temp_critical=sensor_data.get('gpu_temp_critical', 90.0),
                gpu_temp_warning=sensor_data.get('gpu_temp_warning', 80.0),
                cpu_usage_warning=sensor_data.get('cpu_usage_warning', 80.0),
                cpu_usage_critical=sensor_data.get('cpu_usage_critical', 95.0),
                memory_usage_warning=sensor_data.get('memory_usage_warning', 80.0),
                memory_usage_critical=sensor_data.get('memory_usage_critical', 90.0),
                cpu_power_warning=sensor_data.get('cpu_power_warning', 100.0),
                cpu_power_critical=sensor_data.get('cpu_power_critical', 200.0),
                gpu_power_warning=sensor_data.get('gpu_power_warning', 250.0),
                gpu_power_critical=sensor_data.get('gpu_power_critical', 400.0)
            )

        # Load chart settings
        if 'charts' in data:
            chart_data = data['charts']
            config.charts = ChartConfig(
                default_type=chart_data.get('default_type', 'line'),
                smooth_updates=chart_data.get('smooth_updates', True),
                auto_scale=chart_data.get('auto_scale', True),
                max_data_points=chart_data.get('max_data_points', 3600),
                dual_axis_threshold=chart_data.get('dual_axis_threshold', 2)
            )

        # Load UI settings
        if 'ui' in data:
            ui_data = data['ui']
            config.ui = UIConfig(
                compact_mode_width=ui_data.get('compact_mode_width', 100),
                compact_mode_height=ui_data.get('compact_mode_height', 20),
                show_legend=ui_data.get('show_legend', True),
                show_grid=ui_data.get('show_grid', True),
                animation_speed=ui_data.get('animation_speed', 'normal')
            )

        # Load alert settings
        if 'alerts' in data:
            alert_data = data['alerts']
            config.alerts = AlertConfig(
                enable_visual_alerts=alert_data.get('enable_visual_alerts', True),
                enable_audio_alerts=alert_data.get('enable_audio_alerts', False),
                blink_critical_values=alert_data.get('blink_critical_values', True),
                critical_color=alert_data.get('critical_color', 'red'),
                warning_color=alert_data.get('warning_color', 'yellow'),
                normal_color=alert_data.get('normal_color', 'green')
            )

        return config

    @staticmethod
    def find_config_file() -> Path | None:
        """Find configuration file in standard locations."""
        # Search paths in order of preference
        search_paths = [
            Path.cwd() / "config.toml",
            Path.cwd() / "hwinfo-tui.toml",
            Path.home() / ".config" / "hwinfo-tui" / "config.toml",
            Path.home() / ".hwinfo-tui.toml",
        ]

        # Add XDG config directory on Unix-like systems
        if os.name != 'nt':
            xdg_config = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config:
                search_paths.insert(-1, Path(xdg_config) / "hwinfo-tui" / "config.toml")

        for path in search_paths:
            if path.exists() and path.is_file():
                return path

        return None

    def get_color_for_value(self, value: float, unit: str | None, sensor_name: str = "") -> str:
        """Get color for a value based on configured thresholds."""
        if unit == "°C":
            # Temperature thresholds
            if "cpu" in sensor_name.lower():
                if value >= self.sensors.cpu_temp_critical:
                    return self.alerts.critical_color
                elif value >= self.sensors.cpu_temp_warning:
                    return self.alerts.warning_color
            elif "gpu" in sensor_name.lower():
                if value >= self.sensors.gpu_temp_critical:
                    return self.alerts.critical_color
                elif value >= self.sensors.gpu_temp_warning:
                    return self.alerts.warning_color
            else:
                # Generic temperature thresholds
                if value >= 85:
                    return self.alerts.critical_color
                elif value >= 75:
                    return self.alerts.warning_color

        elif unit == "%":
            # Usage/percentage thresholds
            if "cpu" in sensor_name.lower() and "usage" in sensor_name.lower():
                if value >= self.sensors.cpu_usage_critical:
                    return self.alerts.critical_color
                elif value >= self.sensors.cpu_usage_warning:
                    return self.alerts.warning_color
            elif "memory" in sensor_name.lower():
                if value >= self.sensors.memory_usage_critical:
                    return self.alerts.critical_color
                elif value >= self.sensors.memory_usage_warning:
                    return self.alerts.warning_color
            else:
                # Generic percentage thresholds
                if value >= 90:
                    return self.alerts.critical_color
                elif value >= 80:
                    return self.alerts.warning_color

        elif unit == "W":
            # Power thresholds
            if "cpu" in sensor_name.lower():
                if value >= self.sensors.cpu_power_critical:
                    return self.alerts.critical_color
                elif value >= self.sensors.cpu_power_warning:
                    return self.alerts.warning_color
            elif "gpu" in sensor_name.lower():
                if value >= self.sensors.gpu_power_critical:
                    return self.alerts.critical_color
                elif value >= self.sensors.gpu_power_warning:
                    return self.alerts.warning_color

        return self.alerts.normal_color

    def should_use_compact_mode(self, width: int, height: int) -> bool:
        """Determine if compact mode should be used based on terminal size."""
        return width < self.ui.compact_mode_width or height < self.ui.compact_mode_height


# Global configuration instance
_config_instance: HWInfoConfig | None = None


def get_config() -> HWInfoConfig:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = HWInfoConfig.load_from_file()
    return _config_instance


def reload_config() -> HWInfoConfig:
    """Reload the configuration from file."""
    global _config_instance
    _config_instance = HWInfoConfig.load_from_file()
    return _config_instance
