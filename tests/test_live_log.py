"""Following a live HWiNFO log: missing, half-written, restarted, stale or corrupted.

Spec: specs/live-log-recovery.md. Each test drives the app the way the refresh
loop does (initialize / check_log / read_new_data) against a temp CSV, no HWiNFO.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hwinfo_tui.cli import app as cli_app
from hwinfo_tui.data.csv_reader import FILE_REPLACED, CSVReader
from hwinfo_tui.main import HWInfoApp

HEADER = "Date,Time,CPU Temp [°C],GPU Load [%]\n"
SWAPPED_HEADER = "Date,Time,GPU Load [%],CPU Temp [°C]\n"


def row(second: int, cpu: float, gpu: float) -> str:
    return f"14.10.2026,10:00:{second:02d}.000,{cpu},{gpu}\n"


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def append(path: Path, text: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(text)


def delete(path: Path) -> None:
    """Delete the log, retrying while the reader's poll has it open (Windows)."""
    for _ in range(50):
        try:
            path.unlink()
            return
        except PermissionError:
            time.sleep(0.05)
    path.unlink()


def values(app: HWInfoApp, name: str = "CPU Temp [°C]") -> list[float]:
    return app.sensors[name].values


def make_app(path: Path, stale_after: int = 15) -> HWInfoApp:
    return HWInfoApp(path, ["CPU Temp", "GPU Load"], stale_after=stale_after)


def tick(app: HWInfoApp) -> None:
    """One refresh of the main loop, without waiting out the retry interval."""
    app._last_open_attempt = 0.0
    app.check_log()
    if app.csv_reader:
        app.csv_reader.read_new_data()


@pytest.fixture
def csv_path(tmp_path: Path) -> Path:
    return tmp_path / "sensors.csv"


def test_starts_before_the_log_exists(csv_path: Path) -> None:
    app = make_app(csv_path)
    assert not app.initialize()
    assert "doesn't exist" in (app.waiting_reason or "")

    write(csv_path, HEADER + row(1, 50, 10) + row(2, 51, 11))
    tick(app)

    assert app.csv_reader is not None
    assert app.waiting_reason is None
    assert values(app) == [50.0, 51.0]


def test_waits_for_a_header_and_rows(csv_path: Path) -> None:
    app = make_app(csv_path)
    write(csv_path, "")
    assert not app.initialize()

    write(csv_path, "Date,Time,CPU Te")  # header still being written
    assert not app.initialize()

    write(csv_path, HEADER)
    assert not app.initialize()
    assert "no data rows" in (app.waiting_reason or "")

    append(csv_path, row(1, 50, 10))
    assert app.initialize()


def test_truncated_log_is_reopened_without_old_rows(csv_path: Path) -> None:
    write(csv_path, HEADER + row(1, 50, 10) + row(2, 51, 11) + row(3, 52, 12))
    app = make_app(csv_path)
    assert app.initialize()

    write(csv_path, HEADER + row(1, 99, 90))
    tick(app)

    assert values(app) == [99.0]


def test_reader_never_reads_past_a_truncation(csv_path: Path) -> None:
    write(csv_path, HEADER + row(1, 50, 10) + row(2, 51, 11))
    reader = CSVReader(csv_path)
    reader.initialize_sensors(["CPU Temp [°C]"])
    reader.read_initial_data()

    write(csv_path, HEADER)
    assert reader.file_state() == FILE_REPLACED
    reader.read_new_data()
    assert reader.sensors["CPU Temp [°C]"].values == [50.0, 51.0]


def test_recreated_log_with_reordered_columns_maps_each_sensor(csv_path: Path) -> None:
    write(csv_path, HEADER + row(1, 50, 10))
    app = make_app(csv_path)
    assert app.initialize()

    delete(csv_path)
    write(csv_path, SWAPPED_HEADER + "14.10.2026,10:01:00.000,7,77\n")
    tick(app)

    assert values(app, "CPU Temp [°C]") == [77.0]
    assert values(app, "GPU Load [%]") == [7.0]


def test_deleted_log_keeps_history_until_it_returns(csv_path: Path) -> None:
    write(csv_path, HEADER + row(1, 50, 10))
    app = make_app(csv_path)
    assert app.initialize()

    delete(csv_path)
    tick(app)
    assert app.file_gone
    assert "gone" in (app.status_line() or "")
    assert values(app) == [50.0]

    write(csv_path, HEADER + row(1, 60, 20))
    tick(app)
    assert not app.file_gone
    assert values(app) == [60.0]


def test_stale_marker_shows_and_clears(csv_path: Path) -> None:
    write(csv_path, HEADER + row(1, 50, 10))
    app = make_app(csv_path, stale_after=5)
    assert app.initialize()
    assert app.csv_reader is not None

    app.csv_reader.last_data_time = time.time() - 60
    assert "Stale" in (app.status_line() or "")

    append(csv_path, row(2, 51, 11))
    tick(app)
    assert app.status_line() is None


def test_old_log_opens_marked_stale(csv_path: Path) -> None:
    write(csv_path, HEADER + row(1, 50, 10))
    old = time.time() - 600
    import os
    os.utime(csv_path, (old, old))

    app = make_app(csv_path)
    assert app.initialize()
    assert "Stale" in (app.status_line() or "")


def test_half_written_row_is_read_once_complete(csv_path: Path) -> None:
    write(csv_path, HEADER + row(1, 50, 10))
    app = make_app(csv_path)
    assert app.initialize()

    append(csv_path, "14.10.2026,10:00:02.000,5")
    tick(app)
    assert values(app) == [50.0]

    append(csv_path, "3,11\n")
    tick(app)
    assert values(app) == [50.0, 53.0]


def test_garbage_file_keeps_waiting_then_recovers(csv_path: Path) -> None:
    csv_path.write_bytes(bytes(range(256)) * 8 + b"\n" + bytes(range(256)))
    app = make_app(csv_path)
    assert not app.initialize()
    assert app.waiting_reason

    tick(app)  # still garbage: no exception, still waiting
    assert app.csv_reader is None

    write(csv_path, HEADER + row(1, 50, 10))
    tick(app)
    assert values(app) == [50.0]


def test_header_without_the_sensors_keeps_waiting(csv_path: Path) -> None:
    write(csv_path, "Date,Time,Fan [RPM]\n14.10.2026,10:00:01.000,1200\n")
    app = make_app(csv_path)
    assert not app.initialize()
    assert "CPU Temp" in (app.waiting_reason or "")


def test_monitor_accepts_a_missing_file(csv_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(**kwargs: object) -> int:
        calls.append(kwargs)
        return 0

    monkeypatch.setattr("hwinfo_tui.main.run_application", fake_run)
    result = CliRunner().invoke(cli_app, ["monitor", str(csv_path), "CPU Temp"])

    assert result.exit_code == 0, result.output
    assert calls and calls[0]["stale_after"] == 15
