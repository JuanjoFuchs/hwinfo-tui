"""CSV reader with file monitoring capabilities for HWInfo sensor data."""

from __future__ import annotations

import csv
import io
import logging
import os
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from threading import Event, Lock, Thread
from typing import Any

import pandas as pd
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer as WatchdogObserver

from .sensors import Sensor, SensorInfo

logger = logging.getLogger(__name__)

# HWiNFO headers run to a few KB; anything past this without a newline is not a header.
MAX_HEADER_BYTES = 1024 * 1024

# What file_state() reports about the log since this reader opened it.
FILE_OK = "ok"
FILE_MISSING = "missing"
FILE_REPLACED = "replaced"


def _birth_time(st: os.stat_result) -> float:
    """Creation time of a file: st_birthtime where available, else st_ctime (Windows)."""
    return float(getattr(st, "st_birthtime", st.st_ctime))


class CSVFileHandler(FileSystemEventHandler):
    """Handler for CSV file changes."""

    def __init__(self, csv_path: Path, callback: Callable[[], None]) -> None:
        """Initialize the file handler."""
        self.csv_path = csv_path
        self.callback = callback
        super().__init__()

    def on_modified(self, event: Any) -> None:
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
        self.observer: Any = None
        self.monitoring = False
        self.stop_event = Event()
        self.encoding = 'utf-8-sig'  # Default encoding, will be set during header reading
        # The log can be truncated or recreated under us (HWiNFO stops and restarts
        # logging), so remember what the file looked like when it was opened.
        self.header_bytes = b""
        self.birth_time: float | None = None
        # Wall-clock time the newest row arrived; drives the stale marker.
        self.last_data_time: float | None = None
        # The UI loop and the polling thread both call read_new_data.
        self._read_lock = Lock()

        # Validate file exists
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        # Read headers
        self._read_headers()

    def _read_headers(self) -> None:
        """Read and store CSV headers.

        Raises ValueError when the first line is not a usable header yet (empty file,
        no newline yet, a single column), so callers can keep waiting for the log.
        """
        try:
            with open(self.csv_path, 'rb') as f:
                st = os.fstat(f.fileno())
                head = f.read(MAX_HEADER_BYTES)

            newline = head.find(b'\n')
            if newline < 0:
                raise ValueError("CSV header is not complete yet")
            header_bytes = head[:newline + 1]

            # Try multiple encodings to handle different CSV exports
            encodings_to_try = ['utf-8-sig', 'utf-8', 'latin1', 'cp1252', 'iso-8859-1']

            for encoding in encodings_to_try:
                try:
                    first_line = header_bytes.decode(encoding)
                except UnicodeDecodeError:
                    continue  # Try next encoding

                headers = next(csv.reader([first_line.rstrip('\r\n')]), [])
                if len(headers) < 2:
                    raise ValueError("CSV header has fewer than two columns")

                self.headers = headers
                self.encoding = encoding
                self.header_bytes = header_bytes
                self.last_position = len(header_bytes)
                self.birth_time = _birth_time(st)
                logger.info(f"Read {len(self.headers)} headers from {self.csv_path} using {encoding} encoding")
                return

            # If all encodings failed
            raise ValueError("Could not decode CSV file with any supported encoding")

        except Exception as e:
            logger.error(f"Failed to read headers: {e}")
            raise

    def file_state(self) -> str:
        """Report whether the log is still the file this reader opened.

        FILE_MISSING: the path is gone. FILE_REPLACED: the file was truncated or
        recreated (shorter than what was already read, a different creation time, or
        a different first line). FILE_OK otherwise.
        """
        try:
            st = os.stat(self.csv_path)
            if st.st_size < self.last_position:
                return FILE_REPLACED
            if self.birth_time is not None and _birth_time(st) != self.birth_time:
                return FILE_REPLACED
            with open(self.csv_path, 'rb') as f:
                if f.read(len(self.header_bytes)) != self.header_bytes:
                    return FILE_REPLACED
        except OSError:
            return FILE_MISSING
        return FILE_OK

    def seconds_since_data(self) -> float | None:
        """Seconds since the newest row arrived, or None before the first row."""
        if self.last_data_time is None:
            return None
        return max(0.0, time.time() - self.last_data_time)

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
            with open(self.csv_path, 'rb') as f:
                st = os.fstat(f.fileno())
                data = f.read()

            # Stop at the last complete line: HWiNFO may be mid-way through writing
            # the next row, which read_new_data picks up once it is finished. A
            # finished file without a final newline (an archived log) still counts
            # its last line, when that line has every column.
            complete = data.rfind(b'\n') + 1
            tail = data[complete:]
            if tail.strip():
                last = next(csv.reader([tail.decode(self.encoding, errors='replace')]), [])
                if len(last) == len(self.headers):
                    complete = len(data)
            self.last_position = max(complete, len(self.header_bytes))
            if complete <= len(self.header_bytes):
                logger.warning("CSV file has no data rows yet")
                return

            # Read the CSV file with error handling for malformed rows
            df = pd.read_csv(
                io.BytesIO(data[:complete]),
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

            # The newest row is as old as the file's last write.
            self.last_data_time = st.st_mtime

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
        """Read any new data that has been added to the file.

        Only complete lines are consumed; a half-written last line stays for the next
        call. Nothing is read once the file has been truncated or recreated, since
        the old position means nothing in the new file (the app reopens it instead).
        """
        with self._read_lock:
            try:
                if self.file_state() != FILE_OK:
                    return

                with open(self.csv_path, 'rb') as f:
                    f.seek(self.last_position)
                    chunk = f.read()

                complete = chunk.rfind(b'\n') + 1
                if complete == 0:
                    return

                rows = 0
                text = chunk[:complete].decode(self.encoding, errors='replace')
                for line in text.splitlines():
                    if not line.strip():
                        continue
                    try:
                        # Parse CSV line
                        values = next(csv.reader([line]))

                        if len(values) == len(self.headers):
                            row_dict = dict(zip(self.headers, values, strict=True))
                            self._process_row(row_dict)
                            rows += 1

                    except Exception as e:
                        logger.warning(f"Failed to parse line: {line[:50]}... Error: {e}")

                # Update position
                self.last_position += complete
                if rows:
                    self.last_data_time = time.time()

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
            self.observer = WatchdogObserver()
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
