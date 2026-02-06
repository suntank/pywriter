import ast
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class OutlinePanel(Gtk.Box):
    """Right-side panel showing classes and functions from AST."""

    COL_ICON = 0
    COL_NAME = 1
    COL_LINE = 2
    COL_KIND = 3

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self._update_timeout_id = None
        self._connected_buffer = None

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        header.set_name("panel-header")
        header.set_margin_start(4)
        header.set_margin_end(4)
        header.set_margin_top(2)
        header.set_margin_bottom(2)

        lbl = Gtk.Label(label="OUTLINE")
        lbl.set_xalign(0)
        header.pack_start(lbl, True, True, 0)
        self.pack_start(header, False, False, 0)

        # icon, name, line, kind
        self.store = Gtk.TreeStore(str, str, int, str)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_headers_visible(False)

        col = Gtk.TreeViewColumn()
        icon_r = Gtk.CellRendererPixbuf()
        col.pack_start(icon_r, False)
        col.add_attribute(icon_r, "icon-name", self.COL_ICON)

        name_r = Gtk.CellRendererText()
        col.pack_start(name_r, True)
        col.add_attribute(name_r, "text", self.COL_NAME)

        self.tree.append_column(col)
        self.tree.connect("row-activated", self._on_row_activated)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.tree)
        self.pack_start(scrolled, True, True, 0)

    def update_for_document(self, doc):
        if not doc:
            self.store.clear()
            self._disconnect_buffer()
            return
        self._connect_buffer(doc.buffer)
        self._schedule_update(doc)

    def _connect_buffer(self, buf):
        if self._connected_buffer == buf:
            return
        self._disconnect_buffer()
        self._connected_buffer = buf
        self._handler_id = buf.connect("changed", self._on_buffer_changed)

    def _disconnect_buffer(self):
        if self._connected_buffer:
            try:
                self._connected_buffer.disconnect(self._handler_id)
            except Exception:
                pass
            self._connected_buffer = None

    def _on_buffer_changed(self, buf):
        doc = self.app.editor_manager.active_document if self.app.editor_manager else None
        if doc:
            self._schedule_update(doc)

    def _schedule_update(self, doc):
        if self._update_timeout_id:
            GLib.source_remove(self._update_timeout_id)
        self._update_timeout_id = GLib.timeout_add(800, self._do_update, doc)

    def _do_update(self, doc):
        self._update_timeout_id = None
        text = doc.get_text()
        threading.Thread(target=self._parse, args=(text,), daemon=True).start()
        return False

    def _parse(self, text):
        symbols = []
        try:
            tree = ast.parse(text)
            self._walk(tree, symbols, depth=0)
        except SyntaxError:
            pass
        GLib.idle_add(self._apply_symbols, symbols)

    def _walk(self, node, symbols, depth):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                children = []
                self._walk(child, children, depth + 1)
                symbols.append(("class", child.name, child.lineno, children))
            elif isinstance(child, ast.FunctionDef) or isinstance(child, ast.AsyncFunctionDef):
                symbols.append(("function", child.name, child.lineno, []))

    def _apply_symbols(self, symbols):
        self.store.clear()
        self._add_symbols(symbols, None)

    def _add_symbols(self, symbols, parent_iter):
        for kind, name, line, children in symbols:
            if kind == "class":
                icon = "dialog-information-symbolic"
            else:
                icon = "text-x-generic-symbolic"
            it = self.store.append(parent_iter, [icon, name, line, kind])
            if children:
                self._add_symbols(children, it)
        self.tree.expand_all()

    def _on_row_activated(self, tree, treepath, column):
        it = self.store.get_iter(treepath)
        line = self.store.get_value(it, self.COL_LINE)
        doc = self.app.editor_manager.active_document if self.app.editor_manager else None
        if doc:
            buf = doc.buffer
            target = buf.get_iter_at_line(max(0, line - 1))
            buf.place_cursor(target)
            view = self.app.editor_manager.get_active_view()
            if view:
                view.scroll_to_mark(buf.get_insert(), 0.1, True, 0, 0.5)
                view.grab_focus()
