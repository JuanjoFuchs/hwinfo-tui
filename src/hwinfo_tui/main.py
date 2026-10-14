"""Main application entry point and core loop for HWInfo TUI."""

from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path
from threading import Event
from typing import Any

from rich.console import Console
from rich.live import Live

try:
    # Try relative imports first (normal package usage)
    from .data.csv_reader import FILE_MISSING, FILE_OK, CSVReader
    from .data.sensors import Sensor
    from .display.layout import HWInfoLayout
    from .utils.stats import StatsCalculator
    from .utils.units import UnitFilter, validate_sensor_compatibility
except ImportError:
    # Fallback to absolute imports (PyInstaller compatibility)
    from hwinfo_tui.data.csv_reader import FILE_MISSING, FILE_OK, CSVReader
    from hwinfo_tui.data.sensors import Sensor
    from hwinfo_tui.display.layout import HWInfoLayout
    from hwinfo_tui.utils.stats import StatsCalculator
    from hwinfo_tui.utils.units import UnitFilter, validate_sensor_compatibility

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# How often to look for a usable log while waiting for one.
WAIT_POLL_SECONDS = 1.0


def resolve_sensors(reader: CSVReader, patterns: list[str]) -> tuple[list[str], list[str]]:
    """Match sensor patterns against the log's header and apply unit filtering.

    Returns (accepted sensor names, patterns that matched no column).
    """
    available = [s.lower() for s in reader.get_available_sensors()]
    missing = [p for p in patterns if not any(p.lower() in s for s in available)]
    matched = reader.find_matching_sensors(patterns)
    accepted, _, _ = validate_sensor_compatibility(matched)
    return accepted, missing


class HWInfoApp:
    """Main HWInfo TUI application.

    The log is HWiNFO's to start, stop and recreate, so the app never gives up on
    it: until the file has a usable header and the requested sensors it shows a
    waiting screen, and it reopens the file whenever HWiNFO restarts the log.
    """

    def __init__(
        self,
        csv_path: Path,
        sensor_names: list[str],
        refresh_rate: float = 1.0,
        time_window: int = 300,
        stale_after: int = 15
    ) -> None:
        """Initialize the application."""
        self.csv_path = csv_path
        self.sensor_names = sensor_names
        self.refresh_rate = refresh_rate
        self.time_window = time_window
        self.stale_after = stale_after

        # Why the log isn't open yet (None once it is), and whether an open log
        # has since disappeared from disk.
        self.waiting_reason: str | None = "Starting"
        self.file_gone = False
        self._last_open_attempt = 0.0

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
        def signal_handler(signum: int, frame: Any) -> None:
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)

    def initialize(self) -> bool:
        """Try to open the log and start reading it.

        Returns False, with waiting_reason set, while the file is missing, has no
        usable header or rows yet, or lacks every requested sensor. Never raises:
        a bad file is something to wait out, not a crash.
        """
        self._last_open_attempt = time.time()
        if not self.csv_path.exists():
            self.waiting_reason = "The file doesn't exist yet."
            return False

        try:
            reader = CSVReader(self.csv_path)
            accepted, missing = resolve_sensors(reader, self.sensor_names)
            if not accepted:
                self.waiting_reason = (
                    "None of the requested sensors are in the file yet: " + ", ".join(missing)
                )
                return False

            sensors = reader.initialize_sensors(accepted)
            reader.read_initial_data(self.time_window)
            if reader.last_data_time is None:
                self.waiting_reason = "The file has a header but no data rows yet."
                return False

        except Exception as e:
            logger.info(f"Log not usable yet: {e}")
            self.waiting_reason = f"The file isn't a readable HWiNFO log yet ({e})."
            return False

        self._close_reader()
        self.csv_reader = reader
        self.sensors = sensors
        self.csv_reader.start_monitoring(callback=self._on_new_data)
        self.waiting_reason = None
        self.file_gone = False

        logger.info(f"Initialized {len(self.sensors)} sensors")
        return True

    def _close_reader(self) -> None:
        """Stop and drop the current reader, if any."""
        if self.csv_reader:
            self.csv_reader.stop_monitoring()
        self.csv_reader = None

    def check_log(self) -> None:
        """Follow the log through HWiNFO starting, stopping and restarting it.

        Called once per refresh. While waiting it retries the open; once open it
        notices the file disappearing (history stays, marked) and the file being
        truncated or recreated (reopened from scratch: the old history belongs to
        a different log).
        """
        if self.csv_reader is None:
            if time.time() - self._last_open_attempt >= WAIT_POLL_SECONDS:
                self.initialize()
            return

        state = self.csv_reader.file_state()
        if state == FILE_MISSING:
            self.file_gone = True
            return

        if state != FILE_OK or self.file_gone:
            logger.info("Log was restarted; reopening it")
            self._close_reader()
            self.sensors = {}
            self.waiting_reason = "HWiNFO restarted its log."
            self.initialize()

    def status_line(self) -> str | None:
        """The one-line warning shown above the chart, or None while data is live."""
        if self.file_gone:
            return f"Log file is gone: waiting for HWiNFO to log to {self.csv_path} again"
        if self.csv_reader:
            age = self.csv_reader.seconds_since_data()
            if age is not None and age > self.stale_after:
                return f"Stale: no new data for {int(age)}s, waiting for HWiNFO"
        return None

    def _on_new_data(self) -> None:
        """Callback for when new data is available."""
        if not self.paused.is_set():
            # Trigger display update by waking up the main loop
            pass

    def run(self) -> int:
        """Run the main application loop."""
        # A log that isn't usable yet is waited for on screen, not an error.
        self.initialize()

        self.running.set()

        try:
            with Live(
                self._create_initial_display(),
                console=self.console,
                refresh_per_second=max(1.0 / self.refresh_rate, 1),
                transient=False,
                screen=True,
                vertical_overflow="visible"
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

    def _create_initial_display(self) -> Any:
        """Create the initial display layout."""
        if self.csv_reader is None:
            return self.layout.waiting_screen(str(self.csv_path), self.waiting_reason)

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
            csv_path=str(self.csv_path),
            status=self.status_line()
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

                # Small sleep to prevent busy waiting
                time.sleep(0.05)

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(0.5)  # Prevent rapid error loops

    def _update_display(self, live: Live) -> None:
        """Update the display with current data."""
        try:
            self.check_log()
            if self.csv_reader is None:
                live.update(self.layout.waiting_screen(str(self.csv_path), self.waiting_reason))
                return

            # Read any new CSV data
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
                csv_path=str(self.csv_path),
                status=self.status_line()
            )

            # Update live display
            live.update(updated_layout)

        except Exception as e:
            logger.error(f"Failed to update display: {e}")

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
    stale_after: int = 15
) -> int:
    """Run the HWInfo TUI application."""
    app = HWInfoApp(
        csv_path=csv_path,
        sensor_names=sensor_names,
        refresh_rate=refresh_rate,
        time_window=time_window,
        stale_after=stale_after
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
