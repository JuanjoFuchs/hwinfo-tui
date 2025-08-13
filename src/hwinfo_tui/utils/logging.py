"""Logging configuration and utilities for HWInfo TUI."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler


class HWInfoLogger:
    """Custom logger setup for HWInfo TUI."""
    
    def __init__(self, name: str = "hwinfo_tui") -> None:
        """Initialize the logger."""
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_complete = False
    
    def setup(
        self,
        level: str = "WARNING",
        log_file: Optional[Path] = None,
        console: Optional[Console] = None
    ) -> logging.Logger:
        """Setup logging configuration."""
        if self._setup_complete:
            return self.logger
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Set level
        numeric_level = getattr(logging, level.upper(), logging.WARNING)
        self.logger.setLevel(numeric_level)
        
        # Create formatters
        file_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            fmt='%(name)s: %(message)s'
        )
        
        # Add file handler if specified
        if log_file:
            try:
                # Create log directory if it doesn't exist
                log_file.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(numeric_level)
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                print(f"Warning: Could not setup file logging: {e}", file=sys.stderr)
        
        # Add console handler
        if console:
            # Use Rich handler for better formatting
            rich_handler = RichHandler(
                console=console,
                show_path=False,
                show_time=False,
                markup=True
            )
            rich_handler.setLevel(numeric_level)
            self.logger.addHandler(rich_handler)
        else:
            # Fallback to standard stream handler
            stream_handler = logging.StreamHandler(sys.stderr)
            stream_handler.setLevel(numeric_level)
            stream_handler.setFormatter(console_formatter)
            self.logger.addHandler(stream_handler)
        
        self._setup_complete = True
        return self.logger
    
    def get_logger(self) -> logging.Logger:
        """Get the logger instance."""
        if not self._setup_complete:
            self.setup()
        return self.logger


# Global logger instance
_logger_instance: Optional[HWInfoLogger] = None


def setup_logging(
    level: str = "WARNING",
    log_file: Optional[Path] = None,
    console: Optional[Console] = None
) -> logging.Logger:
    """Setup global logging configuration."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = HWInfoLogger()
    
    return _logger_instance.setup(level, log_file, console)


def get_logger(name: str = "hwinfo_tui") -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


class ErrorHandler:
    """Centralized error handling for the application."""
    
    def __init__(self, console: Console, logger: logging.Logger) -> None:
        """Initialize the error handler."""
        self.console = console
        self.logger = logger
    
    def handle_startup_error(self, error: Exception, context: str = "") -> None:
        """Handle startup errors."""
        error_msg = f"Startup error: {error}"
        if context:
            error_msg = f"{context}: {error}"
        
        self.logger.error(error_msg, exc_info=True)
        self.console.print(f"[red]Error:[/red] {error}")
        
        # Provide helpful suggestions
        if "No such file or directory" in str(error):
            self.console.print("[yellow]Tip:[/yellow] Check that the CSV file path is correct")
        elif "Permission denied" in str(error):
            self.console.print("[yellow]Tip:[/yellow] Make sure you have read access to the CSV file")
        elif "No matching sensors" in str(error):
            self.console.print("[yellow]Tip:[/yellow] Use 'hwinfo-tui list-sensors' to see available sensors")
    
    def handle_runtime_error(self, error: Exception, context: str = "", recoverable: bool = True) -> None:
        """Handle runtime errors."""
        error_msg = f"Runtime error: {error}"
        if context:
            error_msg = f"{context}: {error}"
        
        self.logger.error(error_msg, exc_info=True)
        
        if recoverable:
            self.console.print(f"[yellow]Warning:[/yellow] {error}")
            self.console.print("[dim]Continuing operation...[/dim]")
        else:
            self.console.print(f"[red]Fatal Error:[/red] {error}")
    
    def handle_data_error(self, error: Exception, sensor_name: str = "") -> None:
        """Handle data processing errors."""
        context = f"Data error for sensor '{sensor_name}'" if sensor_name else "Data processing error"
        error_msg = f"{context}: {error}"
        
        self.logger.warning(error_msg)
        # Don't show data errors to user unless in debug mode
    
    def handle_display_error(self, error: Exception, component: str = "") -> None:
        """Handle display/rendering errors."""
        context = f"Display error in {component}" if component else "Display error"
        error_msg = f"{context}: {error}"
        
        self.logger.warning(error_msg)
        self.console.print(f"[yellow]Display issue:[/yellow] {component} rendering failed")
    
    def handle_config_error(self, error: Exception) -> None:
        """Handle configuration errors."""
        self.logger.warning(f"Configuration error: {error}")
        self.console.print(f"[yellow]Config Warning:[/yellow] {error}")
        self.console.print("[dim]Using default settings...[/dim]")


def create_safe_wrapper(func, error_handler: ErrorHandler, context: str = ""):
    """Create a safe wrapper function that handles exceptions."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_handler.handle_runtime_error(e, context, recoverable=True)
            return None
    
    return wrapper


def get_log_file_path() -> Path:
    """Get the default log file path."""
    # Try to use platform-appropriate log directory
    if sys.platform == "win32":
        # Windows: Use %LOCALAPPDATA%
        import os
        local_app_data = os.environ.get('LOCALAPPDATA')
        if local_app_data:
            return Path(local_app_data) / "hwinfo-tui" / "hwinfo-tui.log"
    
    # Unix-like systems: Use XDG cache directory or fallback
    import os
    xdg_cache = os.environ.get('XDG_CACHE_HOME')
    if xdg_cache:
        return Path(xdg_cache) / "hwinfo-tui" / "hwinfo-tui.log"
    
    # Fallback to user home directory
    return Path.home() / ".cache" / "hwinfo-tui" / "hwinfo-tui.log"


class ContextualLogger:
    """Logger with contextual information."""
    
    def __init__(self, base_logger: logging.Logger, context: str) -> None:
        """Initialize contextual logger."""
        self.base_logger = base_logger
        self.context = context
    
    def debug(self, msg: str) -> None:
        """Log debug message with context."""
        self.base_logger.debug(f"[{self.context}] {msg}")
    
    def info(self, msg: str) -> None:
        """Log info message with context."""
        self.base_logger.info(f"[{self.context}] {msg}")
    
    def warning(self, msg: str) -> None:
        """Log warning message with context."""
        self.base_logger.warning(f"[{self.context}] {msg}")
    
    def error(self, msg: str, exc_info: bool = False) -> None:
        """Log error message with context."""
        self.base_logger.error(f"[{self.context}] {msg}", exc_info=exc_info)
    
    def exception(self, msg: str) -> None:
        """Log exception with context."""
        self.base_logger.exception(f"[{self.context}] {msg}")


def get_contextual_logger(context: str) -> ContextualLogger:
    """Get a contextual logger."""
    base_logger = get_logger()
    return ContextualLogger(base_logger, context)