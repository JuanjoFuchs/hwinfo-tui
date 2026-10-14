# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- Python 3.8 and 3.9 support. `monitor` never started on them (its type hints need 3.10), so the package now requires Python 3.10 or higher

## [1.1.1] - 2026-10-14

### Fixed
- Pin plotext below 6. plotext 6 is a rewrite without the API the chart uses, so a fresh install drew an empty chart, and the Windows executable failed to start
- A duplicated `# type: ignore` that mypy 2 rejects

## [1.1.0] - 2026-10-14

### Added
- `monitor` follows a live HWiNFO log: it waits on screen until the CSV exists and has a usable header, the requested sensors and data, instead of exiting on a missing, empty or corrupted file
- `monitor` reopens the log when HWiNFO stops and restarts logging (the file is truncated or recreated), re-mapping sensors if the columns moved
- A yellow "Stale" bar when no new row has arrived for `--stale-after` seconds (default 15), cleared when rows resume; a "Log file is gone" bar when the file is deleted mid-run

### Fixed
- The chart froze for good after HWiNFO restarted its log, because the reader kept seeking past the new file's end
- A half-written last line is no longer read as a row; only complete lines are consumed

## [1.0.4] - 2025-01-19

### Fixed
- Color mismatch between stats table and chart - now uses RGB tuples consistently
- Yes/No sensor axis positioning - "No" now always appears at bottom (0) and "Yes" at top (1)

### Added
- Comprehensive integration test suite with 43 tests covering all critical code paths
- Test fixtures for reproducible testing scenarios
- Chart rendering tests that verify dual-axis and single-axis modes
- Color assignment tests ensuring consistency across components
- Layout integration tests for terminal size decisions
- CSV reading tests for edge cases and malformed data

### Changed
- Removed redundant color conversion function for cleaner code
- Simplified axis-side parameter handling in chart rendering

## [1.0.3] - 2025-01-XX

### Added
- Packaging infrastructure for PyPI and Windows executable distribution
- GitHub Actions workflows for CI/CD
- License file (MIT)
- Changelog file

### Changed
- Version management now uses pyproject.toml as single source of truth
- Repository URLs updated to point to JuanjoFuchs/hwinfo-tui

## [1.0.0] - 2024-08-15

### Added
- Real-time hardware sensor monitoring with gping-inspired interface
- Support for HWInfo CSV data visualization
- Dual Y-axis charts for different sensor units
- Yes/No sensor support with bar plot visualization
- Rich statistics table with min, max, average, and 95th percentile
- Fuzzy sensor name matching
- Configurable refresh rates and time windows
- Unit-based sensor filtering and grouping
- Responsive design adapting to terminal size
- Command-line interface with sensor discovery
- Comprehensive test suite
- Development environment setup scripts

### Features
- Monitor temperature, usage, power, and other hardware metrics
- Support for up to 2 different units simultaneously on dual axes
- Bar plots for binary sensors (Yes/No, thermal throttling)
- Line plots for continuous metrics
- Color-coded sensor visualization
- Real-time CSV file monitoring with watchdog
- Compact mode for smaller terminals
- Cross-platform support (Windows, macOS, Linux)

[Unreleased]: https://github.com/JuanjoFuchs/hwinfo-tui/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/JuanjoFuchs/hwinfo-tui/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/JuanjoFuchs/hwinfo-tui/compare/v1.0.4...v1.1.0
[1.0.0]: https://github.com/JuanjoFuchs/hwinfo-tui/releases/tag/v1.0.0