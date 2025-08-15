"""Main application entry point and core loop for HWInfo TUI."""

from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path
from threading import Event

from rich.console import Console
from rich.live import Live

try:
    # Try relative imports first (normal package usage)
    from .data.csv_reader import CSVReader
    from .data.sensors import Sensor
    from .display.layout import HWInfoLayout
    from .utils.stats import StatsCalculator
    from .utils.units import UnitFilter
except ImportError:
    # Fallback to absolute imports (PyInstaller compatibility)
    from hwinfo_tui.data.csv_reader import CSVReader
    from hwinfo_tui.data.sensors import Sensor
    from hwinfo_tui.display.layout import HWInfoLayout
    from hwinfo_tui.utils.stats import StatsCalculator
    from hwinfo_tui.utils.units import UnitFilter

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)


class HWInfoApp:
    """Main HWInfo TUI application."""

    def __init__(
        self,
        csv_path: Path,
        sensor_names: list[str],
        refresh_rate: float = 1.0,
        time_window: int = 300,
        theme: str = "default"
    ) -> None:
        """Initialize the application."""
        self.csv_path = csv_path
        self.sensor_names = sensor_names
        self.refresh_rate = refresh_rate
        self.time_window = time_window
        self.theme = theme

        # Application components
        self.console = Console()
        self.layout = HWInfoLayout(self.console)
        self.stats_calculator = StatsCalculator(time_window)
        self.unit_filter = UnitFilter()

        # Application state
        self.running = Event()
        self.paused = Event()
        self.should_reset = Event()
        self.csv_reader: CSVReader | None = None
        self.sensors: dict[str, Sensor] = {}

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)

    def initialize(self) -> bool:
        """Initialize the application components."""
        try:
            # Initialize CSV reader
            self.csv_reader = CSVReader(self.csv_path)

            # Initialize sensors
            self.sensors = self.csv_reader.initialize_sensors(self.sensor_names)

            if not self.sensors:
                self.console.print("[red]Error:[/red] No sensors could be initialized")
                return False

            # Read initial data
            self.csv_reader.read_initial_data(self.time_window)

            # Start monitoring
            self.csv_reader.start_monitoring(callback=self._on_new_data)

            logger.info(f"Initialized {len(self.sensors)} sensors")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            self.console.print(f"[red]Error:[/red] {e}")
            return False

    def _on_new_data(self) -> None:
        """Callback for when new data is available."""
        if not self.paused.is_set():
            # Trigger display update by waking up the main loop
            pass

    def run(self) -> int:
        """Run the main application loop."""
        if not self.initialize():
            return 1

        self.running.set()

        try:
            with Live(
                self._create_initial_display(),
                console=self.console,
                refresh_per_second=max(1.0 / self.refresh_rate, 1),
                transient=False
            ) as live:
                self._main_loop(live)

            return 0

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Interrupted by user[/yellow]")
            return 0
        except Exception as e:
            logger.error(f"Application error: {e}")
            self.console.print(f"\n[red]Error:[/red] {e}")
            return 1
        finally:
            self.cleanup()

    def _create_initial_display(self) -> any:
        """Create the initial display layout."""
        # Calculate initial stats
        stats = self.stats_calculator.calculate_all_stats(self.sensors)

        # Create sensor groups
        sensor_groups = self.unit_filter.create_sensor_groups(self.sensors)

        # Create layout
        return self.layout.update_layout(
            sensors=self.sensors,
            sensor_groups=sensor_groups,
            stats=stats,
            time_window=self.time_window,
            refresh_rate=self.refresh_rate,
            csv_path=str(self.csv_path)
        )

    def _main_loop(self, live: Live) -> None:
        """Main application loop."""
        last_update = 0.0

        while self.running.is_set():
            try:
                current_time = time.time()

                # Check if we should update the display
                if current_time - last_update >= self.refresh_rate:
                    # Handle reset if requested
                    if self.should_reset.is_set():
                        self._handle_reset()
                        self.should_reset.clear()

                    # Update display if not paused
                    if not self.paused.is_set():
                        self._update_display(live)
                        last_update = current_time

                # Handle keyboard input (non-blocking)
                self._handle_keyboard_input()

                # Small sleep to prevent busy waiting
                time.sleep(0.05)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(0.5)  # Prevent rapid error loops

    def _update_display(self, live: Live) -> None:
        """Update the display with current data."""
        try:
            # Read any new CSV data
            if self.csv_reader:
                self.csv_reader.read_new_data()

            # Calculate current statistics
            stats = self.stats_calculator.calculate_all_stats(self.sensors)

            # Create sensor groups
            sensor_groups = self.unit_filter.create_sensor_groups(self.sensors)

            # Update layout
            updated_layout = self.layout.update_layout(
                sensors=self.sensors,
                sensor_groups=sensor_groups,
                stats=stats,
                time_window=self.time_window,
                refresh_rate=self.refresh_rate,
                csv_path=str(self.csv_path)
            )

            # Update live display
            live.update(updated_layout)

        except Exception as e:
            logger.error(f"Failed to update display: {e}")

    def _handle_keyboard_input(self) -> None:
        """Handle keyboard input (simplified - real implementation would use keyboard library)."""
        # This is a placeholder for keyboard input handling
        # In a real implementation, you would use a library like `keyboard` or `pynput`
        # to handle non-blocking keyboard input
        pass

    def _handle_reset(self) -> None:
        """Handle reset request."""
        try:
            # Clear all sensor readings
            for sensor in self.sensors.values():
                sensor.clear_readings()

            # Re-read initial data
            if self.csv_reader:
                self.csv_reader.read_initial_data(self.time_window)

            logger.info("Display reset completed")

        except Exception as e:
            logger.error(f"Failed to reset display: {e}")

    def toggle_pause(self) -> None:
        """Toggle pause state."""
        if self.paused.is_set():
            self.paused.clear()
            logger.info("Resumed monitoring")
        else:
            self.paused.set()
            logger.info("Paused monitoring")

        # Update layout pause state
        self.layout.toggle_pause()

    def reset_display(self) -> None:
        """Request a display reset."""
        self.should_reset.set()

    def stop(self) -> None:
        """Stop the application."""
        self.running.clear()
        logger.info("Application stop requested")

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.csv_reader:
                self.csv_reader.stop_monitoring()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


def run_application(
    csv_path: Path,
    sensor_names: list[str],
    refresh_rate: float = 1.0,
    time_window: int = 300,
    theme: str = "default"
) -> int:
    """Run the HWInfo TUI application."""
    app = HWInfoApp(
        csv_path=csv_path,
        sensor_names=sensor_names,
        refresh_rate=refresh_rate,
        time_window=time_window,
        theme=theme
    )

    return app.run()


def app() -> None:
    """Entry point for the CLI application."""
    try:
        from .cli import app as typer_app
    except ImportError:
        from hwinfo_tui.cli import app as typer_app
    typer_app()


if __name__ == "__main__":
    app()
