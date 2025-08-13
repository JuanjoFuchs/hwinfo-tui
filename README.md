# HWInfo TUI

A gping-inspired terminal visualization tool for monitoring real-time hardware sensor data from HWInfo.

![HWInfo TUI Demo](demo.png)

## Features

- **Real-time Monitoring**: Live sensor data visualization with configurable refresh rates
- **gping-inspired UI**: Clean interface with statistics table and interactive chart
- **Unit-based Filtering**: Automatically groups sensors by units, supports up to 2 units simultaneously
- **Dual Y-axes**: Charts can display different units on left and right axes
- **Interactive Controls**: Pause, reset, theme switching, and zoom controls
- **Responsive Design**: Automatically adapts to terminal size with compact mode
- **Fuzzy Sensor Matching**: Partial sensor name matching with suggestions
- **Rich Statistics**: Min, max, average, and 95th percentile calculations

## Installation

### From PyPI (Recommended)

```bash
pip install hwinfo-tui
```

### From Source (Development)

#### Quick Setup (Recommended)

**Windows:**
```bash
git clone https://github.com/hwinfo-tui/hwinfo-tui.git
cd hwinfo-tui

# Command Prompt
setup.bat

# PowerShell
.\setup.ps1
```

**Linux/macOS:**
```bash
git clone https://github.com/hwinfo-tui/hwinfo-tui.git
cd hwinfo-tui
./setup.sh
```

#### Manual Setup

```bash
git clone https://github.com/hwinfo-tui/hwinfo-tui.git
cd hwinfo-tui

# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/macOS  
source venv/bin/activate

# Install in development mode
pip install -e .
```

## Quick Start

1. **Generate HWInfo CSV**: Configure HWInfo to log sensor data to a CSV file
2. **Run HWInfo TUI**: Monitor your desired sensors

```bash
# Basic usage - monitor CPU temperature
hwinfo-tui sensors.csv "CPU Package"

# Monitor multiple temperature sensors
hwinfo-tui sensors.csv "Core Temperatures (avg)" "GPU Temperature" "CPU Package"

# Mixed units - CPU usage and temperature
hwinfo-tui sensors.csv "Total CPU Usage" "Core Temperatures"

# Custom settings
hwinfo-tui sensors.csv "GPU Temperature" --refresh-rate 0.5 --time-window 600
```

## Usage Examples

### Single Unit Monitoring
```bash
# All temperature sensors
hwinfo-tui sensors.csv "Core Temperatures (avg) [°C]" "GPU Temperature [°C]" "CPU Package [°C]"

# All percentage sensors
hwinfo-tui sensors.csv "Total CPU Usage [%]" "GPU Core Load [%]" "GPU Memory Usage [%]"
```

### Dual Unit Monitoring
```bash
# Temperature and percentage
hwinfo-tui sensors.csv "Core Temperatures (avg) [°C]" "Total CPU Usage [%]" "GPU Temperature [°C]"

# Power and temperature
hwinfo-tui sensors.csv "CPU Package Power [W]" "CPU Package [°C]" "GPU Power [W]"
```

### Discover Available Sensors
```bash
# List all sensors in CSV
hwinfo-tui list-sensors sensors.csv

# Filter by unit
hwinfo-tui list-sensors sensors.csv --unit "°C"

# Limit results
hwinfo-tui list-sensors sensors.csv --limit 20
```

## Interactive Controls

| Key | Action |
|-----|---------|
| `Q` / `Ctrl+C` / `ESC` | Quit application |
| `Space` | Pause/resume real-time updates |
| `R` | Reset chart view and statistics |
| `C` | Cycle through color themes |
| `+` / `-` | Zoom in/out (change time window) |
| `T` | Toggle time format (relative/absolute) |
| `Ctrl+L` | Clear screen and reset |
| `H` / `?` | Show help |

## Command Line Options

```bash
hwinfo-tui [OPTIONS] CSV_FILE SENSOR_NAME [SENSOR_NAME...]

Options:
  --refresh-rate FLOAT    Update frequency in seconds (0.1-60.0) [default: 1.0]
  --time-window INTEGER   History window in seconds (10-7200) [default: 300]
  --theme TEXT           Color theme (default/dark/matrix) [default: default]
  --version              Show version and exit
  --help                 Show help message
```

## Configuration

HWInfo TUI supports configuration files for customizing behavior:

### Configuration Locations
- `./config.toml` (current directory)
- `./hwinfo-tui.toml`
- `~/.config/hwinfo-tui/config.toml`
- `~/.hwinfo-tui.toml`

### Sample Configuration
```toml
[display]
refresh_rate = 1.0
theme = "default"
time_window = 300

[sensors]
cpu_temp_critical = 85
cpu_temp_warning = 75
gpu_temp_critical = 90
gpu_temp_warning = 80

[charts]
smooth_updates = true
auto_scale = true
dual_axis_threshold = 2

[ui]
compact_mode_width = 100
compact_mode_height = 20
show_legend = true
```

## HWInfo Setup

1. Download and install [HWInfo64](https://www.hwinfo.com/)
2. Run HWInfo64 and go to **Sensors**
3. Click **File → Start Logging**
4. Choose CSV format and select your desired location
5. Configure logging interval (1-2 seconds recommended)
6. Use the generated CSV file with HWInfo TUI

## Unit Filtering

HWInfo TUI automatically filters sensors based on their units to create clean, readable charts:

- **Single Unit**: All sensors with the same unit (e.g., all temperatures in °C)
- **Dual Units**: Up to 2 different units displayed on separate Y-axes
- **Auto-exclusion**: Sensors with incompatible units are automatically excluded with clear warnings

### Example Unit Filtering
```bash
# This command would exclude the [W] sensor and show a warning
hwinfo-tui sensors.csv "Core Temperatures [°C]" "Total CPU Usage [%]" "CPU Power [W]"
# Output: "Excluded sensor 'CPU Power [W]' with unit [W] - chart limited to units [°C] and [%]"
```

## System Requirements

- **Python**: 3.8 or higher
- **Terminal**: Any modern terminal with color support
- **Platform**: Windows, macOS, Linux
- **Dependencies**: typer, rich, plotext, pandas, watchdog

## Performance

- **Memory Usage**: < 50MB baseline, < 100MB with full data retention
- **CPU Overhead**: < 2% of single core during normal operation
- **Startup Time**: < 2 seconds from launch to first display
- **Update Frequency**: Configurable from 0.1 to 60 seconds

## Troubleshooting

### Common Issues

**"No matching sensors found"**
```bash
# Check available sensors first
hwinfo-tui list-sensors sensors.csv
# Use partial names for fuzzy matching
hwinfo-tui sensors.csv "CPU" "GPU"
```

**"Too many units excluded"**
- HWInfo TUI supports maximum 2 different units
- Group sensors by similar units for best results

**"File not found"**
- Ensure HWInfo is actively logging to the CSV file
- Check file path and permissions

**Poor performance**
- Reduce refresh rate: `--refresh-rate 2.0`
- Reduce time window: `--time-window 120`

### Debug Mode
```bash
# Enable verbose logging
HWINFO_TUI_LOG_LEVEL=DEBUG hwinfo-tui sensors.csv "CPU"
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

**Quick Setup:**
```bash
git clone https://github.com/hwinfo-tui/hwinfo-tui.git
cd hwinfo-tui

# Windows
setup.bat

# Linux/macOS
./setup.sh
```

**Manual Setup:**
```bash
python -m venv venv
# Activate venv (see above)
pip install -e ".[dev]"
pytest
```

**Daily Development:**
```bash
# Windows Command Prompt
activate.bat

# Windows PowerShell
.\activate.ps1

# Linux/macOS  
source ./activate.sh

# Run tests
pytest
# or: .\test.ps1 (PowerShell with extra features)

# Run the app
hwinfo-tui --help
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by [gping](https://github.com/orf/gping) for the clean TUI design
- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- Uses [plotext](https://github.com/piccolomo/plotext) for ASCII charts
- Powered by [Typer](https://github.com/tiangolo/typer) for the CLI interface

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.