import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class Diagnostic:
    def __init__(self, file, line, column, message, severity, code):
        self.file = file
        self.line = line
        self.column = column
        self.message = message
        self.severity = severity
        self.code = code


class ProblemsPanel(Gtk.Box):
    """Bottom panel displaying lint diagnostics."""

    COL_ICON = 0
    COL_FILE = 1
    COL_LINE = 2
    COL_MESSAGE = 3
    COL_CODE = 4
    COL_FULL_PATH = 5

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        header.set_name("panel-header")
        header.set_margin_start(4)
        header.set_margin_end(4)
        header.set_margin_top(2)

        lbl = Gtk.Label(label="PROBLEMS")
        lbl.set_xalign(0)
        header.pack_start(lbl, True, True, 0)

        self.count_label = Gtk.Label(label="0")
        header.pack_end(self.count_label, False, False, 4)

        self.pack_start(header, False, False, 0)

        # icon, filename, line, message, code, full_path
        self.store = Gtk.ListStore(str, str, int, str, str, str)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_headers_visible(True)

        col_icon = Gtk.TreeViewColumn("", Gtk.CellRendererPixbuf(), icon_name=self.COL_ICON)
        col_icon.set_fixed_width(30)
        self.tree.append_column(col_icon)

        col_file = Gtk.TreeViewColumn("File", Gtk.CellRendererText(), text=self.COL_FILE)
        col_file.set_resizable(True)
        col_file.set_min_width(120)
        self.tree.append_column(col_file)

        col_line = Gtk.TreeViewColumn("Line", Gtk.CellRendererText(), text=self.COL_LINE)
        col_line.set_min_width(50)
        self.tree.append_column(col_line)

        col_msg = Gtk.TreeViewColumn("Message", Gtk.CellRendererText(), text=self.COL_MESSAGE)
        col_msg.set_resizable(True)
        col_msg.set_expand(True)
        self.tree.append_column(col_msg)

        col_code = Gtk.TreeViewColumn("Code", Gtk.CellRendererText(), text=self.COL_CODE)
        col_code.set_min_width(70)
        self.tree.append_column(col_code)

        self.tree.connect("row-activated", self._on_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.tree)
        self.pack_start(scrolled, True, True, 0)

    def set_diagnostics(self, diagnostics):
        self.store.clear()
        for d in diagnostics:
            icon = "dialog-error-symbolic" if d.severity == "error" else "dialog-warning-symbolic"
            from pathlib import Path
            filename = Path(d.file).name if d.file else ""
            self.store.append([icon, filename, d.line, d.message, d.code, str(d.file)])
        self.count_label.set_text(str(len(diagnostics)))

    def clear(self):
        self.store.clear()
        self.count_label.set_text("0")

    def _on_row_activated(self, tree, treepath, column):
        it = self.store.get_iter(treepath)
        filepath = self.store.get_value(it, self.COL_FULL_PATH)
        line = self.store.get_value(it, self.COL_LINE)
        if filepath and self.app.editor_manager:
            self.app.editor_manager.goto_line(filepath, line)
