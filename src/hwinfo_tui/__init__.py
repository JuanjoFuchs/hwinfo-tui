"""HWInfo TUI - A gping-inspired hardware monitoring tool."""

try:
    from importlib.metadata import version
except ImportError:
    # Python < 3.8 fallback
    from importlib_metadata import version

__version__ = version("hwinfo-tui")
__author__ = "JuanjoFuchs"
__description__ = "A gping-inspired terminal visualization tool for monitoring real-time hardware sensor data from HWInfo"
