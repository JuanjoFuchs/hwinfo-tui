# HWInfo TUI – Project Understanding

Last updated: 2025-08-14

## 1) Overview

HWInfo TUI is a terminal-based monitoring tool that visualizes selected HWInfo sensor streams from a CSV file. It presents a stats table over a single scrolling chart, updating as HWInfo appends rows to the CSV.

- Language/runtime: Python 3.8+
- CLI framework: Typer
- TUI/rendering: Rich (Live, Layout, Table) + Plotext for terminal charts
- Data ingestion: pandas for initial window, csv module for incremental parsing, watchdog for file change detection
- Config: TOML-based configuration and thresholds
- Unit rules: Only the first two unique units among selected sensors are shown

## 2) Core goals and behaviors

- Focused sensor selection via CLI arguments (with fuzzy matching against CSV headers).
- Live updates: follow-append on a HWInfo CSV file, render stats and a time-series chart.
- gping-like layout: stats table on top; single chart below.
- Rolling stats per sensor over a time window: Last, Min, Max, Avg, P95.
- Unit-aware display: one or two Y-axes based on up to two allowed units.
- Compact mode for small terminals.

## 3) Architecture at a glance

- CLI layer (`hwinfo_tui/cli.py`): arguments/validation, startup info, dispatch to app.
- App orchestration (`hwinfo_tui/main.py`): lifecycle, Live loop, update cadence, resource cleanup.
- Data layer (`data/`): CSV reader and sensor data models.
- Display layer (`display/`): layout, table, and chart generation.
- Utilities (`utils/`): units logic, stats calculator, config loader, logging, controls.

Key modules:
- `data/csv_reader.py`: robust header read; initial load with pandas; incremental tail parsing; watchdog + polling.
- `data/sensors.py`: `SensorInfo`, `Sensor`, `SensorGroup` for modeling readings and grouping by unit.
- `display/table.py`: stats table rendering with Rich.
- `display/chart.py`: Plotext chart integration with Rich, single/dual Y-axis support.
- `display/layout.py`: determines compact/full layout and assigns deterministic colors to sensors.
- `utils/units.py`: extract/normalize units; filter sensors to at most two units; group sensors.
- `utils/stats.py`: compute rolling stats and formatting.
- `utils/config.py`: TOML config discovery/loading and thresholds.
- `utils/logging.py`: logging setup and safety wrappers.
- `utils/controls.py`: cross-platform keyboard control scaffolding (not yet wired).

## 4) Data flow

1. CLI validates CSV path and encodings, resolves user-provided sensor names via fuzzy matching against headers.
2. Unit filtering keeps sensors with only the first two unique units encountered (others excluded with messages).
3. App initializes `CSVReader`, loads an initial time-window of rows via pandas, and populates `Sensor` deques.
4. Live loop: periodically reads newly appended lines (incremental parsing), updates sensors, calculates stats, and refreshes the layout (table + chart) via Rich.
5. Watchdog and a polling thread detect file updates; graceful shutdown hooks handle SIGINT/SIGTERM.

## 5) CLI usage (per spec and current implementation)

- `hwinfo-tui monitor <sensors.csv> <sensor1> [sensor2 ...] [--refresh-rate FLOAT] [--time-window INT] [--theme TEXT]`
- `hwinfo-tui list-sensors <sensors.csv> [--unit TEXT] [--limit INT]`
- `--help` and `--version` provided by Typer and a version callback.

Highlights:
- CSV validation attempts multiple encodings (`utf-8-sig`, `utf-8`, `latin1`, `cp1252`, `iso-8859-1`).
- Lists available headers (excluding Date/Time) and supports unit filtering in `list-sensors`.

## 6) Unit management rules

- Extract unit from sensor name (e.g., "GPU Temperature [°C]").
- Accept sensors in provided order until two unique units are present; reject any others with different units.
- Group sensors by unit for display and Y-axes assignment.
- Normalization handles common aliases (e.g., %, °C, W, MHz, rpm, etc.).

## 7) Display behavior

- Stats table (top): columns Sensor, Last, Min, Max, Avg, P95; values color-coded by thresholds.
- Chart (bottom): single Plotext chart; when two units present, uses dual Y-axes (left/right) with unit labels.
- Time-based X-axis labels (e.g., HH:mm:ss) over the configured window.
- Sensor colors are deterministic RGB choices for consistency across sessions.
- Compact mode uses a condensed table or mini chart when terminal is small.

## 8) Configuration

- Default settings via `config.toml`; loader supports TOML modules (`tomllib`/`tomli`/`toml`).
- Thresholds for color coding, display defaults (refresh rate, theme, time window), and compact-mode heuristics.
- Searching for config across CWD/XDG/home is supported.

## 9) Logging and error handling

- Rich-friendly logging or plain stream handler; optional file logging support.
- Safe wrappers and categorized error helpers (startup/runtime/data/display/config).
- CSV parsing is resilient: skips malformed rows, tolerates encoding issues, and warns on ambiguous sensor matches.

## 10) Performance targets (from spec)

- Memory: < 50MB baseline, < 100MB with full retention (per `specs/v1.md`).
- CPU overhead: < 2% of one core during normal operation (per `specs/v1.md`).
- Refresh: 1–2s cadence; chart update responsiveness < 100ms (per `specs/v1.md`).
- Startup: < 2s to first display (per `specs/v1.md`).

## 11) Current implementation status

Implemented:
- CLI commands and validation; fuzzy sensor matching; multi-encoding CSV check.
- CSV reader: headers + encodings; pandas initial window; tail-following with watchdog + polling.
- Sensor models with reading conversion and time-window filtering.
- Unit filtering and grouping (cap at two units) with tests.
- Rolling statistics and formatting (with tests).
- Rich table and Plotext chart rendering with dual-axis capability; deterministic colors; compact mode.
- Config and logging utilities.

Not implemented or unused:
- Keyboard controls are defined in `utils/controls.py` but not integrated in `HWInfoApp`.
- Theme switching hooks exist but are not applied to chart/table styles.
- Header/footer methods exist in `display/layout.py` but are not used in the update flow.
- Encoding edge cases for the `°C` symbol appear in `ai-docs/sensors.CSV`; multiple-encoding handling is present in CSV validation and header loading.
- No CLI or end-to-end integration tests are present; unit tests cover units, sensors, and stats.

## 12) Testing

- `tests/test_units.py`: unit normalization, filtering to two units, grouping, and suggestions.
- `tests/test_sensors.py`: SensorInfo extraction; SensorReading conversion (including Yes/No → 1/0); Sensor behavior and SensorGroup validation.
- `tests/test_stats.py`: SensorStats rounding/formatting; StatsCalculator outputs; helpers like `format_time_window` and `calculate_data_rate`.

Gaps:
- No CLI tests (Typer runner) or integration tests for the full read → render loop.

## 13) Observations on current gaps

- Interactive controls are placeholders; non-blocking keyboard handling is not wired into `HWInfoApp`.
- Theme changes and header/footer features exist in code but are not connected to the display update path.
- HWInfo CSV encodings vary; the repository includes a sample (`ai-docs/sensors.CSV`) where the degree symbol appears garbled. CSV reading attempts multiple encodings.

