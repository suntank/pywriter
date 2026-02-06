import json
import subprocess
import threading
from pathlib import Path

from gi.repository import GLib

from ..panels.problems import Diagnostic


class LintRunner:
    """Runs ruff check asynchronously and parses JSON diagnostics."""

    def __init__(self, app):
        self.app = app

    def run(self, filepath, callback):
        """Run ruff on filepath in a background thread.
        callback(filepath, diagnostics) is called on the main thread."""
        filepath = Path(filepath)
        threading.Thread(target=self._run_ruff, args=(filepath, callback),
                         daemon=True).start()

    def _run_ruff(self, filepath, callback):
        diagnostics = []
        try:
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", str(filepath)],
                capture_output=True, text=True, timeout=30
            )
            if result.stdout.strip():
                items = json.loads(result.stdout)
                for item in items:
                    line = item.get("location", {}).get("row", 1)
                    col = item.get("location", {}).get("column", 1)
                    msg = item.get("message", "")
                    code = item.get("code", "")
                    severity = "error" if item.get("fix") is None else "warning"
                    diagnostics.append(Diagnostic(
                        file=str(filepath),
                        line=line,
                        column=col,
                        message=msg,
                        severity=severity,
                        code=code
                    ))
        except FileNotFoundError:
            diagnostics.append(Diagnostic(
                file=str(filepath), line=1, column=1,
                message="ruff not found - install with: pip install ruff",
                severity="warning", code="TOOL"
            ))
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
            diagnostics.append(Diagnostic(
                file=str(filepath), line=1, column=1,
                message=f"Lint error: {e}",
                severity="error", code="TOOL"
            ))

        GLib.idle_add(callback, filepath, diagnostics)
