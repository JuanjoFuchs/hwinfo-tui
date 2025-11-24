"""Fixtures and utilities for integration tests."""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from rich.console import Console


@pytest.fixture
def temp_csv(tmp_path):
    """Create a temporary CSV file with test data.

    Usage:
        csv_path = temp_csv([("CPU Temp", "°C"), ("GPU Temp", "°C")], rows=10)
    """
    def _create_csv(sensors, rows=10, start_time=None, encoding='utf-8-sig'):
        """Create a CSV file with specified sensors and data.

        Args:
            sensors: List of (name, unit) tuples
            rows: Number of data rows to generate
            start_time: Starting timestamp (defaults to now)
            encoding: File encoding

        Returns:
            Path to the created CSV file
        """
        csv_path = tmp_path / "test_sensors.csv"

        if start_time is None:
            start_time = datetime.now()

        # Write header
        header = "Date,Time," + ",".join(
            f'"{name} [{unit}]"' for name, unit in sensors
        )

        # Write rows
        lines = [header]
        for i in range(rows):
            timestamp = start_time + timedelta(seconds=i)
            date_str = timestamp.strftime("%d.%m.%Y")
            time_str = timestamp.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds

            values = [date_str, time_str]
            for _name, unit in sensors:
                if unit == "Yes/No":
                    # Alternate between Yes and No
                    values.append("Yes" if i % 2 == 0 else "No")
                elif unit == "°C":
                    # Simulate temperature values (40-60°C)
                    values.append(f"{40.0 + (i * 2.0):.1f}")
                elif unit == "%":
                    # Simulate percentage values (0-100%)
                    values.append(f"{min(100.0, i * 10.0):.1f}")
                elif unit == "W":
                    # Simulate power values (50-150W)
                    values.append(f"{50.0 + (i * 10.0):.1f}")
                else:
                    # Generic numeric values
                    values.append(f"{10.0 + (i * 5.0):.1f}")

            lines.append(",".join(values))

        csv_path.write_text("\n".join(lines), encoding=encoding)
        return csv_path

    return _create_csv


@pytest.fixture
def mock_console():
    """Create a mock Rich Console for headless testing.

    Usage:
        console = mock_console()
        console.width = 120
        console.height = 30
    """
    console = Mock(spec=Console)
    console.width = 120
    console.height = 30
    return console


@pytest.fixture
def sample_sensors(temp_csv):
    """Create a set of sample sensors with data for testing.

    Returns a tuple of (csv_path, sensor_names).
    """
    csv_path = temp_csv([
        ("CPU Package", "°C"),
        ("CPU Usage", "%"),
        ("Thermal Throttling", "Yes/No"),
    ], rows=20)

    sensor_names = [
        "CPU Package [°C]",
        "CPU Usage [%]",
        "Thermal Throttling [Yes/No]",
    ]

    return csv_path, sensor_names
