"""Interactive control handling for HWInfo TUI."""

from __future__ import annotations

import sys
import threading
import time
from enum import Enum
from typing import Callable

# Platform-specific imports
try:
    if sys.platform == "win32":
        import msvcrt
        _WINDOWS = True
    else:
        import termios
        import tty
        _WINDOWS = False
except ImportError:
    _WINDOWS = sys.platform == "win32"


class KeyAction(Enum):
    """Available key actions."""
    QUIT = "quit"
    PAUSE = "pause"
    RESET = "reset"
    THEME_CYCLE = "theme_cycle"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TOGGLE_TIME_FORMAT = "toggle_time_format"
    CLEAR_SCREEN = "clear_screen"
    HELP = "help"
    UNKNOWN = "unknown"


class KeyHandler:
    """Handles keyboard input for interactive controls."""

    def __init__(self) -> None:
        """Initialize the key handler."""
        self.callbacks: dict[KeyAction, Callable] = {}
        self.running = False
        self.input_thread: threading.Thread | None = None

        # Key mapping
        self.key_map = {
            'q': KeyAction.QUIT,
            'Q': KeyAction.QUIT,
            '\x03': KeyAction.QUIT,  # Ctrl+C
            '\x1b': KeyAction.QUIT,  # ESC
            ' ': KeyAction.PAUSE,    # Space
            'r': KeyAction.RESET,
            'R': KeyAction.RESET,
            'c': KeyAction.THEME_CYCLE,
            'C': KeyAction.THEME_CYCLE,
            '+': KeyAction.ZOOM_IN,
            '=': KeyAction.ZOOM_IN,  # + without shift
            '-': KeyAction.ZOOM_OUT,
            '_': KeyAction.ZOOM_OUT,  # - with shift
            't': KeyAction.TOGGLE_TIME_FORMAT,
            'T': KeyAction.TOGGLE_TIME_FORMAT,
            'h': KeyAction.HELP,
            'H': KeyAction.HELP,
            '?': KeyAction.HELP,
            '\x0c': KeyAction.CLEAR_SCREEN,  # Ctrl+L
        }

        # Arrow keys (platform specific)
        if not _WINDOWS:
            self.key_map.update({
                '\x1b[D': KeyAction.PAN_LEFT,   # Left arrow
                '\x1b[C': KeyAction.PAN_RIGHT,  # Right arrow
            })

    def register_callback(self, action: KeyAction, callback: Callable) -> None:
        """Register a callback for a key action."""
        self.callbacks[action] = callback

    def start_listening(self) -> None:
        """Start listening for keyboard input."""
        if self.running:
            return

        self.running = True
        self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
        self.input_thread.start()

    def stop_listening(self) -> None:
        """Stop listening for keyboard input."""
        self.running = False
        if self.input_thread and self.input_thread.is_alive():
            # Give thread time to finish
            self.input_thread.join(timeout=0.5)

    def _input_loop(self) -> None:
        """Main input loop running in separate thread."""
        if _WINDOWS:
            self._windows_input_loop()
        else:
            self._unix_input_loop()

    def _windows_input_loop(self) -> None:
        """Input loop for Windows systems."""
        while self.running:
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore')
                    self._handle_key(key)
                else:
                    time.sleep(0.01)  # Small delay to prevent busy waiting
            except (KeyboardInterrupt, EOFError):
                break
            except Exception:
                # Ignore input errors and continue
                time.sleep(0.01)

    def _unix_input_loop(self) -> None:
        """Input loop for Unix-like systems."""
        old_settings = None
        try:
            # Set terminal to raw mode
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())

            while self.running:
                try:
                    key = self._read_key()
                    if key:
                        self._handle_key(key)
                    else:
                        time.sleep(0.01)
                except (KeyboardInterrupt, EOFError):
                    break
                except Exception:
                    time.sleep(0.01)
        finally:
            # Restore terminal settings
            if old_settings:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass

    def _read_key(self) -> str | None:
        """Read a key from stdin (Unix)."""
        try:
            # Use select to check if input is available
            import select
            if select.select([sys.stdin], [], [], 0.01)[0]:
                key = sys.stdin.read(1)

                # Handle escape sequences (arrow keys, etc.)
                if key == '\x1b':
                    # Try to read the rest of the escape sequence
                    if select.select([sys.stdin], [], [], 0.01)[0]:
                        key += sys.stdin.read(1)
                        if key == '\x1b[' and select.select([sys.stdin], [], [], 0.01)[0]:
                            key += sys.stdin.read(1)

                return key
        except Exception:
            pass

        return None

    def _handle_key(self, key: str) -> None:
        """Handle a key press."""
        action = self.key_map.get(key, KeyAction.UNKNOWN)

        if action in self.callbacks:
            try:
                self.callbacks[action]()
            except Exception:
                # Log error but don't crash the input handler
                pass


class ControlManager:
    """Manages interactive controls for the HWInfo TUI."""

    def __init__(self) -> None:
        """Initialize the control manager."""
        self.key_handler = KeyHandler()
        self.paused = False
        self.current_theme_index = 0
        self.themes = ["default", "dark", "matrix"]
        self.time_window_zoom = 300  # Current zoom level in seconds
        self.zoom_levels = [30, 60, 120, 300, 600, 1200, 3600]  # Available zoom levels
        self.current_zoom_index = 3  # Start at 300s

        # Callbacks
        self.on_quit: Callable | None = None
        self.on_pause_toggle: Callable | None = None
        self.on_reset: Callable | None = None
        self.on_theme_change: Callable[[str], None] | None = None
        self.on_zoom_change: Callable[[int], None] | None = None
        self.on_time_format_toggle: Callable | None = None
        self.on_clear_screen: Callable | None = None
        self.on_help_requested: Callable | None = None

        self._setup_key_handlers()

    def _setup_key_handlers(self) -> None:
        """Setup key event handlers."""
        self.key_handler.register_callback(KeyAction.QUIT, self._handle_quit)
        self.key_handler.register_callback(KeyAction.PAUSE, self._handle_pause_toggle)
        self.key_handler.register_callback(KeyAction.RESET, self._handle_reset)
        self.key_handler.register_callback(KeyAction.THEME_CYCLE, self._handle_theme_cycle)
        self.key_handler.register_callback(KeyAction.ZOOM_IN, self._handle_zoom_in)
        self.key_handler.register_callback(KeyAction.ZOOM_OUT, self._handle_zoom_out)
        self.key_handler.register_callback(KeyAction.TOGGLE_TIME_FORMAT, self._handle_time_format_toggle)
        self.key_handler.register_callback(KeyAction.CLEAR_SCREEN, self._handle_clear_screen)
        self.key_handler.register_callback(KeyAction.HELP, self._handle_help)

    def start(self) -> None:
        """Start the control manager."""
        self.key_handler.start_listening()

    def stop(self) -> None:
        """Stop the control manager."""
        self.key_handler.stop_listening()

    def _handle_quit(self) -> None:
        """Handle quit action."""
        if self.on_quit:
            self.on_quit()

    def _handle_pause_toggle(self) -> None:
        """Handle pause toggle action."""
        self.paused = not self.paused
        if self.on_pause_toggle:
            self.on_pause_toggle()

    def _handle_reset(self) -> None:
        """Handle reset action."""
        if self.on_reset:
            self.on_reset()

    def _handle_theme_cycle(self) -> None:
        """Handle theme cycling action."""
        self.current_theme_index = (self.current_theme_index + 1) % len(self.themes)
        new_theme = self.themes[self.current_theme_index]
        if self.on_theme_change:
            self.on_theme_change(new_theme)

    def _handle_zoom_in(self) -> None:
        """Handle zoom in action (shorter time window)."""
        if self.current_zoom_index > 0:
            self.current_zoom_index -= 1
            self.time_window_zoom = self.zoom_levels[self.current_zoom_index]
            if self.on_zoom_change:
                self.on_zoom_change(self.time_window_zoom)

    def _handle_zoom_out(self) -> None:
        """Handle zoom out action (longer time window)."""
        if self.current_zoom_index < len(self.zoom_levels) - 1:
            self.current_zoom_index += 1
            self.time_window_zoom = self.zoom_levels[self.current_zoom_index]
            if self.on_zoom_change:
                self.on_zoom_change(self.time_window_zoom)

    def _handle_time_format_toggle(self) -> None:
        """Handle time format toggle action."""
        if self.on_time_format_toggle:
            self.on_time_format_toggle()

    def _handle_clear_screen(self) -> None:
        """Handle clear screen action."""
        if self.on_clear_screen:
            self.on_clear_screen()

    def _handle_help(self) -> None:
        """Handle help request action."""
        if self.on_help_requested:
            self.on_help_requested()

    def get_current_theme(self) -> str:
        """Get the current theme name."""
        return self.themes[self.current_theme_index]

    def get_current_zoom(self) -> int:
        """Get the current zoom level (time window in seconds)."""
        return self.time_window_zoom

    def is_paused(self) -> bool:
        """Check if the display is paused."""
        return self.paused

    def set_callbacks(
        self,
        on_quit: Callable | None = None,
        on_pause_toggle: Callable | None = None,
        on_reset: Callable | None = None,
        on_theme_change: Callable[[str], None] | None = None,
        on_zoom_change: Callable[[int], None] | None = None,
        on_time_format_toggle: Callable | None = None,
        on_clear_screen: Callable | None = None,
        on_help_requested: Callable | None = None
    ) -> None:
        """Set all callbacks at once."""
        if on_quit is not None:
            self.on_quit = on_quit
        if on_pause_toggle is not None:
            self.on_pause_toggle = on_pause_toggle
        if on_reset is not None:
            self.on_reset = on_reset
        if on_theme_change is not None:
            self.on_theme_change = on_theme_change
        if on_zoom_change is not None:
            self.on_zoom_change = on_zoom_change
        if on_time_format_toggle is not None:
            self.on_time_format_toggle = on_time_format_toggle
        if on_clear_screen is not None:
            self.on_clear_screen = on_clear_screen
        if on_help_requested is not None:
            self.on_help_requested = on_help_requested


def get_help_text() -> str:
    """Get help text for interactive controls."""
    return """
Interactive Controls:

[green]Q[/green] or [green]Ctrl+C[/green] or [green]ESC[/green] - Quit application
[green]Space[/green] - Pause/resume real-time updates
[green]R[/green] - Reset chart view and statistics
[green]C[/green] - Cycle through color themes
[green]+ / -[/green] - Zoom in/out (change time window)
[green]T[/green] - Toggle time format (relative/absolute)
[green]Ctrl+L[/green] - Clear screen and reset
[green]H[/green] or [green]?[/green] - Show this help

Navigation (when paused):
[green]← / →[/green] - Pan through historical data

The application will automatically adjust the display based on your terminal size.
Smaller terminals will use compact mode with simplified layout.
"""
