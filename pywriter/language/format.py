import subprocess
import threading
import shutil
from pathlib import Path

from gi.repository import GLib


class FormatRunner:
    """Runs ruff format or black on a file asynchronously."""

    def __init__(self, app):
        self.app = app

    def run(self, filepath, callback):
        """Format filepath in background thread.
        callback(filepath, success) called on main thread."""
        filepath = Path(filepath)
        threading.Thread(target=self._run_format, args=(filepath, callback),
                         daemon=True).start()

    def _run_format(self, filepath, callback):
        success = False
        # Try ruff format first, then black
        if shutil.which("ruff"):
            try:
                result = subprocess.run(
                    ["ruff", "format", str(filepath)],
                    capture_output=True, text=True, timeout=30
                )
                success = result.returncode == 0
                if not success and self.app.output_panel:
                    GLib.idle_add(self.app.output_panel.write_line,
                                  f"ruff format error: {result.stderr}", "error")
            except (subprocess.TimeoutExpired, OSError) as e:
                if self.app.output_panel:
                    GLib.idle_add(self.app.output_panel.write_line,
                                  f"Format error: {e}", "error")
        elif shutil.which("black"):
            try:
                result = subprocess.run(
                    ["black", str(filepath)],
                    capture_output=True, text=True, timeout=30
                )
                success = result.returncode == 0
            except (subprocess.TimeoutExpired, OSError) as e:
                if self.app.output_panel:
                    GLib.idle_add(self.app.output_panel.write_line,
                                  f"Format error: {e}", "error")
        else:
            if self.app.output_panel:
                GLib.idle_add(self.app.output_panel.write_line,
                              "No formatter found. Install ruff or black.", "error")

        GLib.idle_add(callback, filepath, success)
