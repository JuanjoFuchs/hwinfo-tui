"""CSV reader with file monitoring capabilities for HWInfo sensor data."""

from __future__ import annotations

import csv
import logging
import time
from datetime import datetime
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable

import pandas as pd
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .sensors import Sensor, SensorInfo

logger = logging.getLogger(__name__)


class CSVFileHandler(FileSystemEventHandler):
    """Handler for CSV file changes."""

    def __init__(self, csv_path: Path, callback: Callable[[], None]) -> None:
        """Initialize the file handler."""
        self.csv_path = csv_path
        self.callback = callback
        super().__init__()

    def on_modified(self, event) -> None:
        """Handle file modification events."""
        if not event.is_directory and Path(event.src_path) == self.csv_path:
            self.callback()


class CSVReader:
    """CSV reader with real-time monitoring capabilities."""

    def __init__(self, csv_path: Path) -> None:
        """Initialize the CSV reader."""
        self.csv_path = csv_path
        self.sensors: dict[str, Sensor] = {}
        self.headers: list[str] = []
        self.last_position = 0
        self.observer: Observer | None = None
        self.monitoring = False
        self.stop_event = Event()
        self.encoding = 'utf-8-sig'  # Default encoding, will be set during header reading

        # Validate file exists
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Read headers
        self._read_headers()

    def _read_headers(self) -> None:
        """Read and store CSV headers."""
        try:
            # Try multiple encodings to handle different CSV exports
            encodings_to_try = ['utf-8-sig', 'utf-8', 'latin1', 'cp1252', 'iso-8859-1']

            for encoding in encodings_to_try:
                try:
                    with open(self.csv_path, encoding=encoding) as f:
                        # Read first line as string to avoid iterator issues
                        first_line = f.readline()
                        self.last_position = f.tell()

                        # Parse the header line manually
                        reader = csv.reader([first_line])
                        self.headers = next(reader)

                    # Store the successful encoding for later use
                    self.encoding = encoding
                    logger.info(f"Read {len(self.headers)} headers from {self.csv_path} using {encoding} encoding")
                    return

                except UnicodeDecodeError:
                    continue  # Try next encoding

            # If all encodings failed
            raise Exception("Could not decode CSV file with any supported encoding")

        except Exception as e:
            logger.error(f"Failed to read headers: {e}")
            raise

    def get_available_sensors(self) -> list[str]:
        """Get list of available sensor names."""
        # Skip Date and Time columns
        return [header for header in self.headers if header not in ['Date', 'Time']]

    def find_matching_sensors(self, sensor_patterns: list[str]) -> list[str]:
        """Find sensor names that match the given patterns."""
        available = self.get_available_sensors()
        matched = []

        for pattern in sensor_patterns:
            # Try exact match first
            if pattern in available:
                matched.append(pattern)
                continue

            # Try case-insensitive partial match
            pattern_lower = pattern.lower()
            partial_matches = [
                sensor for sensor in available
                if pattern_lower in sensor.lower()
            ]

            if len(partial_matches) == 1:
                matched.append(partial_matches[0])
            elif len(partial_matches) > 1:
                logger.warning(f"Multiple matches for '{pattern}': {partial_matches}")
                matched.append(partial_matches[0])  # Take first match
            else:
                logger.warning(f"No matches found for sensor pattern: '{pattern}'")

        return matched

    def initialize_sensors(self, sensor_names: list[str]) -> dict[str, Sensor]:
        """Initialize sensor objects for the given names."""
        self.sensors = {}

        for name in sensor_names:
            if name not in self.headers:
                logger.warning(f"Sensor '{name}' not found in CSV headers")
                continue

            sensor_info = SensorInfo(name=name)
            self.sensors[name] = Sensor(info=sensor_info)

        logger.info(f"Initialized {len(self.sensors)} sensors")
        return self.sensors

    def read_initial_data(self, window_seconds: int = 300) -> None:
        """Read initial data from the CSV file."""
        try:
            # Read the CSV file with error handling for malformed rows
            df = pd.read_csv(
                self.csv_path,
                encoding=self.encoding,
                on_bad_lines='skip',  # Skip malformed lines
                low_memory=False
            )

            if df.empty:
                logger.warning("CSV file is empty")
                return

            # Get the last N rows based on time window
            if len(df) > window_seconds:
                df = df.tail(window_seconds)

            # Process each row
            for _, row in df.iterrows():
                self._process_row(row)

            # Update file position to end
            with open(self.csv_path, 'rb') as f:
                f.seek(0, 2)  # Seek to end
                self.last_position = f.tell()

            logger.info(f"Read initial data: {len(df)} rows")

        except Exception as e:
            logger.error(f"Failed to read initial data: {e}")
            raise

    def _process_row(self, row: Any) -> None:
        """Process a single CSV row and update sensors."""
        try:
            # Parse timestamp
            if 'Date' in row and 'Time' in row:
                timestamp_str = f"{row['Date']} {row['Time']}"
                try:
                    timestamp = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M:%S.%f")
                except ValueError:
                    # Try without milliseconds
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%d.%m.%Y %H:%M:%S")
                    except ValueError:
                        logger.warning(f"Could not parse timestamp: {timestamp_str}")
                        timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # Update sensor readings
            for sensor_name, sensor in self.sensors.items():
                if sensor_name in row:
                    value = row[sensor_name]
                    sensor.add_reading(timestamp, value)

        except Exception as e:
            logger.warning(f"Failed to process row: {e}")

    def read_new_data(self) -> None:
        """Read any new data that has been added to the file."""
        try:
            with open(self.csv_path, encoding=self.encoding) as f:
                f.seek(self.last_position)
                new_content = f.read()

                if new_content.strip():
                    # Split into lines and process
                    lines = new_content.strip().split('\n')

                    for line in lines:
                        if line.strip():
                            try:
                                # Parse CSV line
                                reader = csv.reader([line])
                                values = next(reader)

                                if len(values) == len(self.headers):
                                    row_dict = dict(zip(self.headers, values))
                                    self._process_row(row_dict)

                            except Exception as e:
                                logger.warning(f"Failed to parse line: {line[:50]}... Error: {e}")

                # Update position
                self.last_position = f.tell()

        except Exception as e:
            logger.warning(f"Failed to read new data: {e}")

    def start_monitoring(self, callback: Callable[[], None] | None = None) -> None:
        """Start monitoring the CSV file for changes."""
        if self.monitoring:
            return

        self.monitoring = True
        self.stop_event.clear()

        # Set up file watcher
        if callback:
            handler = CSVFileHandler(self.csv_path, callback)
            self.observer = Observer()
            self.observer.schedule(handler, str(self.csv_path.parent), recursive=False)
            self.observer.start()

        # Start polling thread as backup
        monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()

        logger.info("Started CSV file monitoring")

    def _monitor_loop(self) -> None:
        """Background loop to monitor file changes."""
        while not self.stop_event.is_set():
            try:
                self.read_new_data()
                time.sleep(0.5)  # Check every 500ms
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(1.0)

    def stop_monitoring(self) -> None:
        """Stop monitoring the CSV file."""
        if not self.monitoring:
            return

        self.monitoring = False
        self.stop_event.set()

        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5.0)
            self.observer = None

        logger.info("Stopped CSV file monitoring")

    def get_sensors(self) -> dict[str, Sensor]:
        """Get all initialized sensors."""
        return self.sensors

    def close(self) -> None:
        """Clean up resources."""
        self.stop_monitoring()
