import os
import subprocess
import threading
import signal
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib


class ToolRunner:
    """Runs Python scripts asynchronously, capturing output to the Output panel."""

    def __init__(self, app):
        self.app = app
        self._process = None

    def run(self, filepath):
        filepath = Path(filepath)
        if not filepath.exists():
            self._write_output(f"File not found: {filepath}\n", "error")
            return

        if self._process and self._process.poll() is None:
            self.stop()

        interpreter = self._find_interpreter(filepath)
        self._write_output(f">>> Running: {interpreter} {filepath.name}\n", "info")

        threading.Thread(target=self._run_subprocess,
                         args=(interpreter, filepath), daemon=True).start()

    def stop(self):
        if self._process and self._process.poll() is None:
            try:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
            except OSError:
                self._process.kill()
            self._write_output("\n--- Process terminated ---\n", "info")

    def _find_interpreter(self, filepath):
        # Check for workspace venv
        workspace = filepath.parent
        for venv_dir in ("venv", ".venv", "env"):
            venv_python = workspace / venv_dir / "bin" / "python"
            if venv_python.exists():
                return str(venv_python)
        # Walk up parents
        for parent in filepath.parents:
            for venv_dir in ("venv", ".venv", "env"):
                venv_python = parent / venv_dir / "bin" / "python"
                if venv_python.exists():
                    return str(venv_python)
        return "python3"

    def _run_subprocess(self, interpreter, filepath):
        try:
            self._process = subprocess.Popen(
                [interpreter, str(filepath)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=str(filepath.parent),
                preexec_fn=os.setsid,
                bufsize=1,
                universal_newlines=True
            )

            for line in self._process.stdout:
                self._write_output(line)

            self._process.wait()
            code = self._process.returncode
            if code != 0:
                self._write_output(f"\n--- Process exited with code {code} ---\n", "error")
            else:
                self._write_output("\n--- Process finished ---\n", "info")

        except OSError as e:
            self._write_output(f"Failed to run: {e}\n", "error")

    def _write_output(self, text, tag=None):
        if self.app.output_panel:
            GLib.idle_add(self.app.output_panel.append, text, tag)
