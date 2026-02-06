import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkSource", "4")
from gi.repository import Gtk, GLib, GtkSource

from .lint import LintRunner
from .format import FormatRunner


class PythonProvider:
    """Coordinates Python language services: linting, formatting, outline."""

    def __init__(self, app):
        self.app = app
        self.lint_runner = LintRunner(app)
        self.format_runner = FormatRunner(app)
        self._lint_timeout_id = None
        self._debounce_ms = app.config.get("lint_debounce_ms", 500)
        self._large_threshold = app.config.get("large_file_threshold", 10000)

    def schedule_lint(self, doc, immediate=False):
        if not doc or not doc.path:
            return
        if doc.get_line_count() > self._large_threshold:
            return
        if not str(doc.path).endswith(".py"):
            return

        if self._lint_timeout_id:
            GLib.source_remove(self._lint_timeout_id)
            self._lint_timeout_id = None

        if immediate:
            self._run_lint(doc)
        else:
            self._lint_timeout_id = GLib.timeout_add(
                self._debounce_ms,
                self._run_lint_timeout, doc
            )

    def _run_lint_timeout(self, doc):
        self._lint_timeout_id = None
        self._run_lint(doc)
        return False

    def _run_lint(self, doc):
        if not doc.path or not doc.path.exists():
            return
        # Save to temp or use existing file
        self.lint_runner.run(doc.path, self._on_lint_done)

    def _on_lint_done(self, filepath, diagnostics):
        # Update problems panel
        if self.app.problems_panel:
            self.app.problems_panel.set_diagnostics(diagnostics)

        # Apply inline markers to the active document buffer
        doc = self.app.editor_manager.active_document if self.app.editor_manager else None
        if doc and doc.path and str(doc.path) == str(filepath):
            self._apply_markers(doc, diagnostics)

    def _apply_markers(self, doc, diagnostics):
        buf = doc.buffer
        # Clear existing error tags
        tag_table = buf.get_tag_table()
        error_tag = tag_table.lookup("lint-error")
        if not error_tag:
            from gi.repository import Pango
            error_tag = buf.create_tag("lint-error",
                                       underline=Pango.Underline.ERROR)

        warning_tag = tag_table.lookup("lint-warning")
        if not warning_tag:
            from gi.repository import Pango
            warning_tag = buf.create_tag("lint-warning",
                                         underline=Pango.Underline.SINGLE,
                                         foreground="#e5a50a")

        start = buf.get_start_iter()
        end = buf.get_end_iter()
        buf.remove_tag(error_tag, start, end)
        buf.remove_tag(warning_tag, start, end)

        for d in diagnostics:
            if d.code == "TOOL":
                continue
            line = max(0, d.line - 1)
            line_start = buf.get_iter_at_line(line)
            line_end = line_start.copy()
            if not line_end.ends_line():
                line_end.forward_to_line_end()
            tag = error_tag if d.severity == "error" else warning_tag
            buf.apply_tag(tag, line_start, line_end)

    def format_file(self, filepath, callback):
        self.format_runner.run(filepath, callback)
