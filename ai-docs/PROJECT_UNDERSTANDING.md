# HWInfo TUI – Project Understanding

Last updated: 2025-10-30

## 1) Overview

HWInfo TUI is a terminal-based monitoring tool that visualizes selected HWInfo sensor streams from a CSV file. It presents a stats table over a single scrolling chart, updating as HWInfo appends rows to the CSV.

- **Language/runtime**: Python 3.8+
- **CLI framework**: Typer (with rich_markup_mode for formatted help and auto-completion support)
- **TUI/rendering**: Rich (Live, Layout, Table) + Plotext for terminal charts (custom PlotextMixin implementing JupyterMixin)
- **Data ingestion**: pandas for initial window load, csv module for incremental tail parsing, watchdog + polling thread for file change detection
- **Data storage**: collections.deque with maxlen=3600 for efficient circular buffering per sensor
- **Version management**: Dynamic version via `importlib.metadata.version("hwinfo-tui")` from pyproject.toml
- **Entry point**: Console script `hwinfo-tui` → `hwinfo_tui.main:app`
- **Distribution**: PyPI (pip install), WinGet (Windows Package Manager), and standalone executables via PyInstaller
- **Unit rules**: Only the first two unique units among selected sensors are shown; dual Y-axes when two units present

## 2) Core goals and behaviors

- Focused sensor selection via CLI arguments (with fuzzy matching against CSV headers).
- Live updates: follow-append on a HWInfo CSV file, render stats and a time-series chart.
- gping-like layout: stats table on top; single chart below.
- Rolling stats per sensor over a time window: Last, Min, Max, Avg, P95.
- Unit-aware display: one or two Y-axes based on up to two allowed units.
- Compact mode for small terminals.

## 3) Architecture at a glance

**Source layout**: `src/hwinfo_tui/` with submodules for data, display, and utilities.

**Layers**:
- **CLI layer** (`cli.py`): Typer-based argument parsing/validation, multi-encoding CSV validation, unit filtering at startup, dispatch to app
- **App orchestration** (`main.py`): HWInfoApp class managing lifecycle, Rich Live loop, signal handlers (SIGINT/SIGTERM), resource cleanup
- **Data layer** (`data/`): CSVReader with watchdog+polling, Sensor models with deque storage, SensorGroup for unit-based grouping
- **Display layer** (`display/`): HWInfoLayout with responsive sizing, StatsTable/CompactTable, PlotextMixin for chart integration
- **Utilities** (`utils/`): UnitFilter for unit extraction/filtering, StatsCalculator for rolling statistics

**Key modules**:
- `data/csv_reader.py`: Multi-encoding header read (utf-8-sig/utf-8/latin1/cp1252/iso-8859-1); pandas for initial load; csv module for incremental tail parsing; CSVFileHandler with watchdog Observer + backup polling thread (500ms)
- `data/sensors.py`: SensorInfo (unit extraction via regex), SensorReading (with Yes/No→1.0/0.0 conversion), Sensor (deque-based storage with time-window filtering), SensorGroup (unit-based grouping)
- `display/table.py`: StatsTable (6 columns: Sensor, Last, Min, Max, Avg, P95) and CompactTable (2 columns: Sensor, Value); both use Rich Table with sensor color coding
- `display/chart.py`: PlotextMixin implementing Rich JupyterMixin protocol; dual-axis support (left/right Y-axes); HH:MM:SS time tick formatting; unit-aware Y-axis labels; braille markers; plt.limit_size(False) for tall charts
- `display/layout.py`: Terminal size detection; compact mode heuristics (< 100 width or < 20 height); deterministic RGB color assignment (8 colors, sorted sensor names); layout splitting (minimized table, maximized chart)
- `utils/units.py`: UnitFilter class with extract_unit(), normalize mappings (C→°C, percent→%, etc.), filter_sensors_by_unit() enforcing max 2 units, create_sensor_groups()
- `utils/stats.py`: SensorStats dataclass with rounding/formatting; StatsCalculator with percentile calculation (linear interpolation), threshold-based coloring (°C: 75/85, %: 80/90, W: 100/200)

**Not present in source tree** (mentioned in earlier specs but not implemented):
- `utils/config.py`, `utils/logging.py`, `utils/controls.py` — logging is configured directly in main.py; keyboard controls are spec'd but not implemented

## 4) Data flow

1. **CLI validation** (`cli.py`):
   - Validates CSV file existence and readability with multiple encoding attempts
   - CSVReader reads headers and provides available sensors (excluding Date/Time)
   - Fuzzy matching resolves sensor names (case-insensitive, partial match with suggestions)
   - Unit filtering via validate_sensor_compatibility() filters to max 2 units; excluded sensors reported with clear messages

2. **Initialization** (`main.py:HWInfoApp.initialize()`):
   - Creates CSVReader with validated CSV path (stores encoding for later use)
   - Initializes Sensor objects for accepted sensor names
   - Reads initial data via pandas (last N rows based on time_window, on_bad_lines='skip')
   - Starts file monitoring: watchdog Observer + backup polling thread

3. **Live loop** (`main.py:HWInfoApp._main_loop()`):
   - Runs until self.running.clear() (triggered by signal handlers or stop())
   - Checks refresh_rate timing (default 1.0s)
   - Calls read_new_data(): seeks to last_position, parses new lines with csv module, updates Sensor deques
   - Calculates rolling stats via StatsCalculator over time_window
   - Creates sensor groups by unit
   - Updates HWInfoLayout (table + chart) and Rich Live display
   - Sleeps 0.05s between iterations to prevent busy-waiting

4. **File monitoring** (`csv_reader.py`):
   - Watchdog CSVFileHandler triggers callback on file modification
   - Backup polling thread runs every 500ms in background
   - Incremental parsing: reads from last_position to end, parses CSV lines, skips malformed rows

5. **Graceful shutdown**:
   - Signal handlers (SIGINT/SIGTERM) call app.stop()
   - Cleanup: stops watchdog observer (5s timeout), joins threads

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

**Layout structure** (`display/layout.py`):
- No header/footer in current implementation (root_layout = body_layout directly)
- Dynamic mode selection: compact if terminal < 100 width or < 20 height, otherwise full mode
- Table height minimized (≤1/6 of available space), chart height maximized
- Two table types: StatsTable (full 6 columns) if width ≥ 100, CompactTable (2 columns) otherwise

**Stats table** (`display/table.py`):
- **Full mode**: Sensor, Last, Min, Max, Avg, P95 columns with units inline (e.g., "45.2°C")
- **Compact mode**: Sensor, Value columns only
- Sensor names color-coded using deterministic RGB colors (8 color palette, sorted sensor names)
- Values include units but NOT threshold-based coloring (uses sensor color instead)
- Rich Table with no borders/lines for clean appearance

**Chart display** (`display/chart.py`):
- Single Plotext chart rendered via PlotextMixin (implements Rich JupyterMixin protocol)
- **Dual-axis mode**: When 2 sensor groups present, left Y-axis for group 1, right Y-axis for group 2
- **Single-axis mode**: When 1 sensor group, left Y-axis only
- **X-axis**: 3 evenly-spaced time ticks showing HH:MM:SS format over time_window
- **Y-axis**: Unit-aware tick labels (e.g., "45.2°C", "80.0%"); special handling for Yes/No sensors (ticks at 0="No", 1="Yes")
- **Markers**: Braille Unicode characters for high-resolution line plots
- **Colors**: Deterministic RGB assignment matching table colors (8-color cycle)
- **Sizing**: plt.limit_size(False, False) to allow charts > 25 lines; explicit height passed to maximize chart space

**Color management**:
- 8 predefined RGB colors: bright red, green, blue, yellow, magenta, cyan, orange, purple
- Deterministic assignment: sorted sensor names → modulo color index
- Consistency: same sensor always gets same color across sessions

## 8) Configuration and logging

**Configuration** (spec'd but not fully implemented):
- Specs mention TOML config file support (config.toml) with XDG base directory search
- CLI parameters available: --refresh-rate, --time-window, --theme (theme accepted but not applied)
- Hardcoded defaults: refresh_rate=1.0, time_window=300, compact_mode thresholds (width<100, height<20)
- No config file loader in current source tree (utils/config.py not present)

**Logging** (`main.py`):
- Python logging configured at module level: WARNING default, StreamHandler to stderr
- Log level controllable via HWINFO_TUI_LOG_LEVEL environment variable
- Modules log to their own loggers (csv_reader, chart, table, etc.)
- No dedicated logging utility module (utils/logging.py not present)

**Error handling**:
- **CLI layer**: Validates file existence, permissions, encodings; exits with clear error messages
- **CSV parsing**: pandas on_bad_lines='skip' for initial load; try/except wrappers for incremental parsing
- **Data processing**: Ignores None/empty values, handles Yes/No→1.0/0.0 conversion, filters NaN/Inf in chart data
- **Display**: Logs chart/table errors; shows "N/A" for missing stats; gracefully handles missing sensors
- **Encoding resilience**: Tries 5 encodings (utf-8-sig, utf-8, latin1, cp1252, iso-8859-1) for CSV files
- **Fuzzy matching**: Warns on ambiguous sensor matches; suggests available sensors on no match

## 9) Performance targets and optimizations

**Targets** (from `specs/v1.md`):
- Memory: < 50MB baseline, < 100MB with full retention
- CPU overhead: < 2% of one core during normal operation
- Refresh: 1–2s cadence; chart update responsiveness < 100ms
- Startup: < 2s to first display

**Implemented optimizations**:
- **Circular buffering**: deque with maxlen=3600 prevents unbounded memory growth (auto-evicts oldest readings)
- **Incremental parsing**: Only reads CSV data appended since last_position (not entire file)
- **Update throttling**: Main loop checks timing (refresh_rate) before updating; sleeps 0.05s between checks to prevent busy-waiting
- **Pandas for initial load**: Efficient bulk loading of initial time window; csv module for line-by-line incremental updates
- **Chart size limits**: plt.limit_size(False) disabled plotext's default limiter; explicit height calculation maximizes chart usage
- **Dual monitoring**: Watchdog for event-driven updates + backup polling thread (500ms) ensures updates even if watchdog fails
- **Lazy chart generation**: Charts only created when layout updates (not continuously)
- **Background monitoring**: File monitoring runs in daemon thread; doesn't block main loop

## 10) Current implementation status

**Fully implemented**:
- ✅ Two CLI commands: `monitor` and `list-sensors` with Typer
- ✅ Multi-encoding CSV validation and reading (5 encoding fallbacks)
- ✅ Fuzzy sensor name matching (case-insensitive, partial, with suggestions)
- ✅ Unit filtering at CLI (max 2 units, clear exclusion messages)
- ✅ CSV reader with pandas initial load + csv incremental tail-following
- ✅ Watchdog + polling dual file monitoring (500ms backup polling)
- ✅ Sensor models: SensorInfo (unit extraction), SensorReading (Yes/No conversion), Sensor (deque storage), SensorGroup
- ✅ Time-window filtering for readings (configurable seconds)
- ✅ Rolling statistics: Last, Min, Max, Avg, P95 with custom percentile calculation
- ✅ Value formatting: dynamic precision based on magnitude
- ✅ Rich table rendering: StatsTable (6 cols) and CompactTable (2 cols)
- ✅ Plotext chart: dual-axis support, HH:MM:SS time ticks, unit-aware Y-axis, braille markers
- ✅ Deterministic RGB color assignment (8-color cycle, sorted sensor names)
- ✅ Responsive layout: compact mode (< 100 width or < 20 height), minimized table, maximized chart
- ✅ Signal handlers: graceful shutdown on SIGINT/SIGTERM
- ✅ PyInstaller compatibility: fallback imports (relative + absolute)
- ✅ Comprehensive unit tests: test_units.py, test_sensors.py, test_stats.py (pytest-based)

**Partially implemented or spec'd but not used**:
- ⚠️ Theme parameter: accepted in CLI but not applied to chart/table styles
- ⚠️ Config file: spec'd (config.toml, XDG search) but utils/config.py not in source tree
- ⚠️ Header/footer: code exists in layout.py but disabled (root_layout = body_layout)
- ⚠️ Keyboard controls: spec'd (Space=pause, R=reset, Q=quit, etc.) but not implemented; only programmatic toggle_pause() and reset_display() methods exist
- ⚠️ Logging utilities: utils/logging.py mentioned in specs but not in source; logging configured directly in main.py
- ⚠️ Controls module: utils/controls.py mentioned but not in source

**Not implemented**:
- ❌ Interactive keyboard handling: no non-blocking keyboard input wiring
- ❌ TOML config file loading: no runtime config file support
- ❌ CLI integration tests: no Typer CliRunner tests
- ❌ End-to-end tests: no full read→render loop tests

## 11) Testing strategy

**Unit tests** (pytest-based, located in `tests/`):
- `test_units.py`: UnitFilter.extract_unit() with normalization (C→°C, percent→%, etc.); filter_sensors_by_unit() enforcing max 2 units; create_sensor_groups(); suggest_sensor_names() fuzzy matching; validate_sensor_compatibility() integration
- `test_sensors.py`: SensorInfo unit extraction and display_name; SensorReading value conversion and Yes/No→1.0/0.0; Sensor.add_reading() with invalid values; get_readings_in_window() time filtering; SensorGroup add_sensor() with unit validation
- `test_stats.py`: SensorStats rounding/formatting; StatsCalculator for empty/single/multiple readings; time_window filtering; percentile calculation (linear interpolation); threshold colors (°C/% thresholds); format_time_window() and calculate_data_rate() helpers

**Test coverage**:
- ✅ Data models (sensors, readings, groups)
- ✅ Unit filtering logic
- ✅ Statistics calculation
- ✅ Helper functions
- ❌ CLI commands (no Typer CliRunner tests)
- ❌ CSV reading integration
- ❌ Display rendering
- ❌ End-to-end workflows

## 12) Packaging and distribution

**Build system** (`pyproject.toml`):
- Modern pyproject.toml with setuptools backend
- Entry point: `[project.scripts]` → `hwinfo-tui = hwinfo_tui.main:app`
- Version: single source in pyproject.toml, read dynamically via importlib.metadata
- Python support: 3.8–3.12
- Dependencies: typer, rich, plotext, pandas, watchdog

**Distribution channels** (per `specs/packaging.md`):
1. **PyPI**: `pip install hwinfo-tui` — builds sdist + wheel via `python -m build`
2. **WinGet**: Windows Package Manager — manifest for portable EXE installer
3. **GitHub Releases**: Tagged releases with attached Windows executables

**PyInstaller** (standalone Windows executable):
- Command: `pyinstaller --name hwinfo-tui --onefile --console --paths src src/hwinfo_tui/main.py`
- Output: `hwinfo-tui-<version>-windows-x64.exe`
- Fallback imports in main.py for PyInstaller compatibility (try relative, except absolute)

**CI/CD** (GitHub Actions workflows):
- `.github/workflows/ci.yml`: Matrix testing on Python 3.8–3.12; lint (ruff check), typecheck (mypy), test (pytest)
- `.github/workflows/release.yml`: Triggered on `v*` tags; builds sdist/wheel + Windows EXE; publishes to PyPI (PYPI_TOKEN secret); creates GitHub Release with artifacts; optionally submits to winget-pkgs (GH_PAT secret)

**Version enforcement**: CI verifies git tag `vX.Y.Z` matches pyproject.toml version

## 13) Key implementation patterns

**Import fallback for PyInstaller**:
```python
try:
    from .data.csv_reader import CSVReader  # Relative import
except ImportError:
    from hwinfo_tui.data.csv_reader import CSVReader  # Absolute fallback
```

**Time-window filtering**:
- Sensor.get_readings_in_window(seconds): filters readings by timestamp.timestamp() >= cutoff_timestamp
- StatsCalculator uses this for rolling window statistics

**Value formatting by magnitude**:
- < 0.01: 4 decimals (e.g., "0.0123")
- < 1.0: 3 decimals (e.g., "0.456")
- < 100.0: 2 decimals (e.g., "45.67")
- < 10000.0: 1 decimal (e.g., "1234.5")
- ≥ 10000: integer (e.g., "50000")

**Color-to-plotext mapping**:
- RGB tuples mapped to plotext named colors (red, green, blue, etc.) or passed as RGB
- Consistent between table and chart (same sensor → same color)

**Responsive layout calculation**:
- Compact mode: width < 100 OR height < 20
- Compact table: width < 100 (independent of height)
- Table height: min(num_sensors + 3, max(6, height // 6))
- Chart height: remaining space after table

## 14) Development workflows

**Setup** (per README):
- Quick: `setup.bat` (Windows) or `setup.sh` (Linux/macOS) — creates venv, installs editable package
- Manual: `python -m venv venv` → activate → `pip install -e .[dev]`

**Daily development**:
- Activate venv: `activate.bat`/`activate.ps1` (Windows) or `source activate.sh` (Linux/macOS)
- Run tests: `pytest` or `test.ps1` (PowerShell with extra features)
- Run app: `hwinfo-tui --help` or `hwinfo-tui monitor sensors.csv "CPU"`

**Dependencies**:
- Core: typer[all], rich, plotext, pandas, watchdog
- Dev: pytest, ruff, mypy (in `[project.optional-dependencies.dev]`)

## 15) Observations and future enhancements

**Current gaps**:
- Interactive keyboard controls: spec'd (Space=pause, R=reset, Q=quit, +/-=zoom, ←/→=pan, T=time format, C=theme cycle) but only programmatic methods exist
- Theme switching: parameter accepted but styles not applied
- Config file loading: spec'd with XDG support but not implemented
- Header/footer: layout methods exist but disabled (root_layout = body_layout)
- CLI/integration tests: no Typer CliRunner or end-to-end tests

**Encoding handling**:
- HWInfo CSVs vary in encoding (especially for °C symbol)
- Current implementation tries 5 encodings (utf-8-sig, utf-8, latin1, cp1252, iso-8859-1)
- Sample file `ai-docs/sensors.CSV` demonstrates encoding edge cases

**Potential optimizations**:
- Async I/O for file monitoring (currently sync watchdog + polling thread)
- Partial chart updates instead of full redraws
- Caching of statistics between refresh cycles if data unchanged
- Configurable deque maxlen based on time_window (currently fixed at 3600)

