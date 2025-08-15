# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/JuanjoFuchs/hwinfo-tui/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/JuanjoFuchs/hwinfo-tui/releases/tag/v1.0.0