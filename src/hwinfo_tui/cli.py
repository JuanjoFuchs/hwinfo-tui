"""Command-line interface for HWInfo TUI using Typer."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from . import __version__
from .utils.units import validate_sensor_compatibility

# Initialize console for rich output
console = Console()

# Create Typer app
app = typer.Typer(
    name="hwinfo-tui",
    help="A gping-inspired terminal visualization tool for monitoring real-time hardware sensor data from HWInfo",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True
)


def version_callback(value: bool) -> None:
    """Show version information."""
    if value:
        console.print(f"HWInfo TUI v{__version__}")
        raise typer.Exit()


def validate_csv_file(csv_path: Path) -> Path:
    """Validate that the CSV file exists and is readable."""
    if not csv_path.exists():
        console.print(f"[red]Error:[/red] CSV file not found: {csv_path}")
        raise typer.Exit(1)

    if not csv_path.is_file():
        console.print(f"[red]Error:[/red] Path is not a file: {csv_path}")
        raise typer.Exit(1)

    if not csv_path.suffix.lower() == '.csv':
        console.print(f"[yellow]Warning:[/yellow] File does not have .csv extension: {csv_path}")

    try:
        # Try multiple encodings to handle different CSV exports
        encodings_to_try = ['utf-8-sig', 'utf-8', 'latin1', 'cp1252', 'iso-8859-1']

        for encoding in encodings_to_try:
            try:
                with open(csv_path, encoding=encoding) as f:
                    # Try to read the first line to check if file is readable
                    f.readline()
                break  # Success, exit the encoding loop
            except UnicodeDecodeError:
                continue  # Try next encoding
        else:
            # If all encodings failed
            raise Exception("Could not decode CSV file with any supported encoding")

    except PermissionError as e:
        console.print(f"[red]Error:[/red] Permission denied reading file: {csv_path}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read CSV file: {e}")
        raise typer.Exit(1) from e

    return csv_path


def validate_sensors_with_csv(csv_path: Path, sensor_names: list[str]) -> list[str]:
    """Validate sensor names against CSV headers and apply unit filtering."""
    # Import here to avoid circular imports
    from .data.csv_reader import CSVReader

    try:
        csv_reader = CSVReader(csv_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to read CSV file: {e}")
        raise typer.Exit(1) from e

    # Get available sensors
    available_sensors = csv_reader.get_available_sensors()

    if not available_sensors:
        console.print("[red]Error:[/red] No sensor columns found in CSV file")
        raise typer.Exit(1)

    # Find matching sensors
    matched_sensors = csv_reader.find_matching_sensors(sensor_names)

    if not matched_sensors:
        console.print("[red]Error:[/red] No matching sensors found in CSV file")
        console.print("\n[yellow]Available sensors:[/yellow]")
        for sensor in available_sensors[:10]:  # Show first 10
            console.print(f"  • {sensor}")
        if len(available_sensors) > 10:
            console.print(f"  ... and {len(available_sensors) - 10} more")
        console.print("\n[blue]Tip:[/blue] Use partial sensor names for fuzzy matching")
        raise typer.Exit(1)

    # Apply unit filtering
    accepted_sensors, excluded_messages, allowed_units = validate_sensor_compatibility(matched_sensors)

    if not accepted_sensors:
        console.print("[red]Error:[/red] No sensors passed unit filtering")
        raise typer.Exit(1)

    # Show information about filtering
    if excluded_messages:
        console.print(f"[yellow]Unit Filtering:[/yellow] Limited to {len(allowed_units)} unit(s)")
        for unit in sorted(unit for unit in allowed_units if unit is not None):
            if unit:
                console.print(f"  ✓ Accepted unit: [green][{unit}][/green]")

        console.print(f"\n[yellow]Excluded {len(excluded_messages)} sensor(s):[/yellow]")
        for message in excluded_messages:
            console.print(f"  • {message}")
        console.print()

    return accepted_sensors


@app.callback()
def cli_callback(
    ctx: typer.Context,
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version information and exit"
    )
) -> None:
    """HWInfo TUI - Hardware sensor monitoring tool."""
    pass


@app.command(name="monitor", help="Monitor hardware sensors in real-time")
def monitor(
    csv_file: Path = typer.Argument(
        ...,
        help="Path to HWInfo sensors.csv file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    sensor_names: list[str] = typer.Argument(
        ...,
        help="One or more sensor names to monitor (supports partial matching)"
    ),
    refresh_rate: float = typer.Option(
        1.0,
        "--refresh-rate", "-r",
        min=0.1,
        max=60.0,
        help="Update frequency in seconds (0.1-60.0)"
    ),
    time_window: int = typer.Option(
        300,
        "--time-window", "-w",
        min=10,
        max=7200,
        help="History window in seconds (10-7200)"
    ),
    theme: str = typer.Option(
        "default",
        "--theme", "-t",
        help="Color theme (default/dark/matrix)"
    )
) -> None:
    """
    Monitor hardware sensors in real-time with gping-inspired visualization.

    This tool reads HWInfo CSV sensor data and displays selected sensors in a live
    terminal interface with statistics table and interactive chart.

    [bold]Examples:[/bold]

    • Monitor CPU temperature:
      [cyan]hwinfo-tui monitor sensors.csv "CPU Package"[/cyan]

    • Monitor multiple temperature sensors:
      [cyan]hwinfo-tui monitor sensors.csv "Core Temperatures" "GPU Temperature" "CPU Package"[/cyan]

    • Monitor CPU usage and temperature (mixed units):
      [cyan]hwinfo-tui monitor sensors.csv "Total CPU Usage" "Core Temperatures"[/cyan]

    • Custom refresh rate and time window:
      [cyan]hwinfo-tui monitor sensors.csv "GPU Temperature" --refresh-rate 0.5 --time-window 600[/cyan]

    [bold]Unit Filtering:[/bold]

    The chart supports up to 2 different units simultaneously. If you specify
    sensors with more than 2 units, excess sensors will be automatically excluded
    with clear warning messages.

    [bold]Interactive Controls:[/bold]

    • [green]Q[/green] or [green]Ctrl+C[/green]: Quit application
    • [green]Space[/green]: Pause/resume real-time updates
    • [green]R[/green]: Reset chart view and statistics
    """
    # Validate CSV file
    csv_path = validate_csv_file(csv_file)

    # Validate and filter sensors
    validated_sensors = validate_sensors_with_csv(csv_path, sensor_names)

    # Show startup information
    console.print(f"[green]Starting HWInfo TUI v{__version__}[/green]")
    console.print(f"[blue]CSV File:[/blue] {csv_path}")
    console.print(f"[blue]Sensors:[/blue] {len(validated_sensors)} selected")
    console.print(f"[blue]Settings:[/blue] {refresh_rate}s refresh, {time_window}s window, {theme} theme")
    console.print()

    # Import and run the main application
    try:
        from .main import run_application
        run_application(
            csv_path=csv_path,
            sensor_names=validated_sensors,
            refresh_rate=refresh_rate,
            time_window=time_window,
            theme=theme
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(0) from None
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("list-sensors")
def list_sensors(
    csv_file: Path = typer.Argument(
        ...,
        help="Path to HWInfo sensors.csv file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    filter_unit: str | None = typer.Option(
        None,
        "--unit", "-u",
        help="Filter sensors by unit (e.g., '°C', '%', 'W')"
    ),
    limit: int = typer.Option(
        50,
        "--limit", "-l",
        min=1,
        max=1000,
        help="Maximum number of sensors to display"
    )
) -> None:
    """
    List all available sensors in the CSV file.

    This command helps you discover sensor names for monitoring.
    """
    # Validate CSV file
    csv_path = validate_csv_file(csv_file)

    # Import CSV reader
    from .data.csv_reader import CSVReader
    from .utils.units import UnitFilter

    try:
        csv_reader = CSVReader(csv_path)
        available_sensors = csv_reader.get_available_sensors()

        if not available_sensors:
            console.print("[red]No sensors found in CSV file[/red]")
            raise typer.Exit(1)

        # Filter by unit if requested
        filtered_sensors: list[tuple[str, str | None]] = []
        unit_filter = UnitFilter()

        for sensor_name in available_sensors:
            sensor_unit = unit_filter.extract_unit(sensor_name)

            if filter_unit:
                if sensor_unit == filter_unit:
                    filtered_sensors.append((sensor_name, sensor_unit))
            else:
                filtered_sensors.append((sensor_name, sensor_unit))

        # Apply limit
        filtered_sensors = filtered_sensors[:limit]

        # Display results
        if filter_unit:
            console.print(f"[green]Sensors with unit '[bold]{filter_unit}[/bold]' ({len(filtered_sensors)} found):[/green]")
        else:
            console.print(f"[green]Available sensors ({len(filtered_sensors)} of {len(available_sensors)}):[/green]")

        console.print()

        for sensor_name, sensor_unit in filtered_sensors:
            unit_display = f"[dim]\\[{sensor_unit}][/dim]" if sensor_unit else "[dim]\\[no unit][/dim]"
            console.print(f"  • {sensor_name} {unit_display}")

        if len(available_sensors) > limit:
            console.print(f"\n[yellow]... and {len(available_sensors) - limit} more sensors[/yellow]")
            console.print("[blue]Tip:[/blue] Use --limit to see more sensors")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1) from e


if __name__ == "__main__":
    app()
