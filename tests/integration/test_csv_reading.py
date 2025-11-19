"""Integration tests for CSV reading and sensor initialization.

Tests verify CSV parsing, encoding handling, sensor matching, and data reading.
"""

import pytest
from pathlib import Path

from hwinfo_tui.data.csv_reader import CSVReader


class TestCSVEncoding:
    """Test CSV reading with different encodings."""

    def test_csv_reading_with_utf8_bom(self, tmp_path):
        """Test CSV reading with UTF-8-BOM encoding."""
        csv_path = tmp_path / "test.csv"
        content = "Date,Time,Temp [°C]\n13.08.2025,13:58:50.000,45.0\n"
        csv_path.write_text(content, encoding='utf-8-sig')

        reader = CSVReader(csv_path)
        sensors = reader.get_available_sensors()

        assert "Temp [°C]" in sensors
        assert reader.encoding == 'utf-8-sig'

    def test_csv_reading_with_latin1(self, tmp_path):
        """Test CSV reading with latin1 encoding."""
        csv_path = tmp_path / "test.csv"
        # Use degree symbol that's valid in latin1
        content = "Date,Time,Temp [°C]\n13.08.2025,13:58:50.000,45.0\n"
        csv_path.write_text(content, encoding='latin1')

        reader = CSVReader(csv_path)
        sensors = reader.get_available_sensors()

        assert len(sensors) > 0

    def test_csv_encoding_fallback_chain(self, tmp_path):
        """Test that CSV reader tries multiple encodings."""
        csv_path = tmp_path / "test.csv"
        content = "Date,Time,Temp [°C]\n13.08.2025,13:58:50.000,45.0\n"

        # Try with utf-8 (should work)
        csv_path.write_text(content, encoding='utf-8')

        reader = CSVReader(csv_path)
        sensors = reader.get_available_sensors()

        assert "Temp [°C]" in sensors


class TestSensorMatching:
    """Test sensor name matching strategies."""

    def test_exact_sensor_match(self, temp_csv):
        """Test exact sensor name matching."""
        csv_path = temp_csv([("CPU Temp", "°C")], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])

        assert "CPU Temp [°C]" in sensors
        assert len(sensors) == 1

    def test_exact_sensor_match_with_full_name(self, temp_csv):
        """Test exact sensor name matching with full name and unit."""
        csv_path = temp_csv([("CPU Package Temperature", "°C")], rows=5)

        reader = CSVReader(csv_path)

        # Use exact name with unit
        sensors = reader.initialize_sensors(["CPU Package Temperature [°C]"])

        assert len(sensors) == 1
        assert "CPU Package Temperature [°C]" in sensors

    def test_multiple_similar_sensors(self, temp_csv):
        """Test handling of sensors with similar names."""
        csv_path = temp_csv([
            ("CPU Package", "°C"),
            ("CPU Package Power", "W"),
        ], rows=5)

        reader = CSVReader(csv_path)

        # Request specific sensor by exact name
        sensors = reader.initialize_sensors(["CPU Package [°C]"])

        # Should match exactly one
        assert len(sensors) == 1
        assert "CPU Package [°C]" in sensors

    def test_sensor_not_found(self, temp_csv):
        """Test handling of non-existent sensor."""
        csv_path = temp_csv([("CPU Temp", "°C")], rows=5)

        reader = CSVReader(csv_path)

        # Try to initialize non-existent sensor
        sensors = reader.initialize_sensors(["NonExistent Sensor"])

        # Should return empty or raise error
        assert len(sensors) == 0 or "NonExistent Sensor" not in sensors


class TestDataReading:
    """Test data reading and parsing."""

    def test_initial_data_reading(self, temp_csv):
        """Test reading initial CSV data."""
        csv_path = temp_csv([("CPU Temp", "°C")], rows=10)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])
        reader.read_initial_data(window_seconds=30)

        sensor = sensors["CPU Temp [°C]"]
        assert len(sensor.readings) == 10, "Should read all 10 rows"

        # Verify readings have proper structure
        for reading in sensor.readings:
            assert reading.timestamp is not None
            assert isinstance(reading.value, float)

    def test_time_window_filtering(self, temp_csv):
        """Test that time window filters old data."""
        from datetime import datetime, timedelta

        # Create data spanning 20 seconds
        start_time = datetime.now() - timedelta(seconds=20)
        csv_path = temp_csv([("CPU Temp", "°C")], rows=20, start_time=start_time)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["CPU Temp [°C]"])

        # Only load last 10 seconds
        reader.read_initial_data(window_seconds=10)

        sensor = sensors["CPU Temp [°C]"]

        # Should only have readings from last 10 seconds
        if sensor.readings:
            latest_time = max(r.timestamp for r in sensor.readings)
            oldest_time = min(r.timestamp for r in sensor.readings)
            time_span = (latest_time - oldest_time).total_seconds()
            assert time_span <= 10, "Should only include data within time window"

    def test_malformed_csv_rows_skipped(self, tmp_path):
        """Test that malformed CSV rows are skipped gracefully."""
        csv_path = tmp_path / "test.csv"
        content = """Date,Time,Temp [°C]
13.08.2025,13:58:50.000,45.0
INVALID LINE WITH NO COMMAS
13.08.2025,13:58:51.000,46.0
13.08.2025,13:58:52.000,invalid_number
13.08.2025,13:58:53.000,47.0
"""
        csv_path.write_text(content, encoding='utf-8')

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["Temp [°C]"])
        reader.read_initial_data(window_seconds=30)

        sensor = sensors["Temp [°C]"]

        # Should have valid readings (CSV reader is resilient and parses what it can)
        valid_readings = [r for r in sensor.readings if r.value is not None]
        assert len(valid_readings) >= 3, \
            f"Should have at least 3 valid readings, got {len(valid_readings)}"

    def test_empty_values_handled(self, tmp_path):
        """Test that empty values are handled gracefully."""
        csv_path = tmp_path / "test.csv"
        content = """Date,Time,Temp [°C]
13.08.2025,13:58:50.000,
13.08.2025,13:58:51.000,45.0
13.08.2025,13:58:52.000,46.0
"""
        csv_path.write_text(content, encoding='utf-8')

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["Temp [°C]"])
        reader.read_initial_data(window_seconds=30)

        sensor = sensors["Temp [°C]"]

        # Should have 2 valid readings (skipping empty value)
        valid_readings = [r for r in sensor.readings
                         if r.value is not None and not str(r.value).isspace()]
        assert len(valid_readings) >= 2, "Should skip empty values"


class TestYesNoSensorConversion:
    """Test Yes/No sensor value conversion."""

    def test_yes_no_conversion(self, temp_csv):
        """Test that Yes/No values are converted to 1.0/0.0."""
        csv_path = temp_csv([("Throttling", "Yes/No")], rows=6)

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["Throttling [Yes/No]"])
        reader.read_initial_data(window_seconds=30)

        sensor = sensors["Throttling [Yes/No]"]

        # Verify values are converted to floats
        for reading in sensor.readings:
            assert isinstance(reading.value, float)
            assert reading.value in (0.0, 1.0), \
                f"Yes/No values should be 0.0 or 1.0, got {reading.value}"

    def test_yes_no_pattern_in_data(self, tmp_path):
        """Test Yes/No conversion with actual Yes/No strings."""
        csv_path = tmp_path / "test.csv"
        content = """Date,Time,Throttling [Yes/No]
13.08.2025,13:58:50.000,No
13.08.2025,13:58:51.000,Yes
13.08.2025,13:58:52.000,No
13.08.2025,13:58:53.000,Yes
"""
        csv_path.write_text(content, encoding='utf-8')

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["Throttling [Yes/No]"])
        reader.read_initial_data(window_seconds=30)

        sensor = sensors["Throttling [Yes/No]"]

        # Verify conversion pattern
        values = [r.value for r in sensor.readings]
        assert 0.0 in values, "Should have No (0.0) values"
        assert 1.0 in values, "Should have Yes (1.0) values"


class TestAvailableSensors:
    """Test sensor discovery."""

    def test_get_available_sensors(self, temp_csv):
        """Test getting list of available sensors."""
        csv_path = temp_csv([
            ("CPU Temp", "°C"),
            ("GPU Temp", "°C"),
            ("CPU Usage", "%"),
        ], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.get_available_sensors()

        assert len(sensors) >= 3
        assert "CPU Temp [°C]" in sensors
        assert "GPU Temp [°C]" in sensors
        assert "CPU Usage [%]" in sensors

    def test_sensors_include_units_in_names(self, temp_csv):
        """Test that sensor names include units."""
        csv_path = temp_csv([("Temperature", "°C")], rows=5)

        reader = CSVReader(csv_path)
        sensors = reader.get_available_sensors()

        # Should include unit in square brackets
        assert any("[°C]" in s for s in sensors), \
            "Sensor names should include units in brackets"


class TestTimestampParsing:
    """Test timestamp parsing from CSV."""

    def test_timestamp_with_milliseconds(self, tmp_path):
        """Test parsing timestamps with milliseconds."""
        csv_path = tmp_path / "test.csv"
        content = """Date,Time,Temp [°C]
13.08.2025,13:58:50.123,45.0
13.08.2025,13:58:51.456,46.0
"""
        csv_path.write_text(content, encoding='utf-8')

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["Temp [°C]"])
        reader.read_initial_data(window_seconds=30)

        sensor = sensors["Temp [°C]"]

        # Should parse successfully
        assert len(sensor.readings) == 2
        assert all(r.timestamp is not None for r in sensor.readings)

    def test_timestamp_without_milliseconds(self, tmp_path):
        """Test parsing timestamps without milliseconds."""
        csv_path = tmp_path / "test.csv"
        content = """Date,Time,Temp [°C]
13.08.2025,13:58:50,45.0
13.08.2025,13:58:51,46.0
"""
        csv_path.write_text(content, encoding='utf-8')

        reader = CSVReader(csv_path)
        sensors = reader.initialize_sensors(["Temp [°C]"])
        reader.read_initial_data(window_seconds=30)

        sensor = sensors["Temp [°C]"]

        # Should parse successfully
        assert len(sensor.readings) == 2
        assert all(r.timestamp is not None for r in sensor.readings)
