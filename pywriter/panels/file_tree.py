import os
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Gdk, Gio, GLib

IGNORE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache",
               ".ruff_cache", ".pytest_cache", "*.egg-info", ".tox", "build", "dist"}
IGNORE_FILES = {".pyc", ".pyo", ".so", ".o"}


class FileTree(Gtk.Box):
    """Left-side file browser panel."""

    COL_NAME = 0
    COL_PATH = 1
    COL_IS_DIR = 2
    COL_ICON = 3

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self._root = None
        self._monitor = None

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        header.set_name("panel-header")
        header.set_margin_start(4)
        header.set_margin_end(4)
        header.set_margin_top(2)
        header.set_margin_bottom(2)
        lbl = Gtk.Label(label="FILES")
        lbl.set_xalign(0)
        header.pack_start(lbl, True, True, 0)

        btn_refresh = Gtk.Button()
        btn_refresh.set_image(Gtk.Image.new_from_icon_name("view-refresh-symbolic",
                                                            Gtk.IconSize.SMALL_TOOLBAR))
        btn_refresh.set_relief(Gtk.ReliefStyle.NONE)
        btn_refresh.set_tooltip_text("Refresh")
        btn_refresh.connect("clicked", lambda b: self.refresh())
        header.pack_end(btn_refresh, False, False, 0)

        btn_new_file = Gtk.Button()
        btn_new_file.set_image(Gtk.Image.new_from_icon_name("document-new-symbolic",
                                                             Gtk.IconSize.SMALL_TOOLBAR))
        btn_new_file.set_relief(Gtk.ReliefStyle.NONE)
        btn_new_file.set_tooltip_text("New File")
        btn_new_file.connect("clicked", self._on_new_file)
        header.pack_end(btn_new_file, False, False, 0)

        btn_new_folder = Gtk.Button()
        btn_new_folder.set_image(Gtk.Image.new_from_icon_name("folder-new-symbolic",
                                                               Gtk.IconSize.SMALL_TOOLBAR))
        btn_new_folder.set_relief(Gtk.ReliefStyle.NONE)
        btn_new_folder.set_tooltip_text("New Folder")
        btn_new_folder.connect("clicked", self._on_new_folder)
        header.pack_end(btn_new_folder, False, False, 0)

        self.pack_start(header, False, False, 0)

        # Tree store: name, full_path, is_dir, icon_name
        self.store = Gtk.TreeStore(str, str, bool, str)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_headers_visible(False)
        self.tree.set_enable_tree_lines(True)

        col = Gtk.TreeViewColumn()
        icon_renderer = Gtk.CellRendererPixbuf()
        col.pack_start(icon_renderer, False)
        col.add_attribute(icon_renderer, "icon-name", self.COL_ICON)

        name_renderer = Gtk.CellRendererText()
        col.pack_start(name_renderer, True)
        col.add_attribute(name_renderer, "text", self.COL_NAME)

        self.tree.append_column(col)
        self.tree.connect("row-activated", self._on_row_activated)
        self.tree.connect("button-press-event", self._on_button_press)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.tree)
        self.pack_start(scrolled, True, True, 0)

    def set_root(self, path):
        self._root = Path(path) if path else None
        self.refresh()
        self._setup_monitor()

    def _setup_monitor(self):
        if self._monitor:
            self._monitor.cancel()
            self._monitor = None
        if self._root and self._root.is_dir():
            gfile = Gio.File.new_for_path(str(self._root))
            self._monitor = gfile.monitor_directory(Gio.FileMonitorFlags.NONE, None)
            self._monitor.connect("changed", self._on_fs_changed)

    def _on_fs_changed(self, monitor, file, other_file, event_type):
        if event_type in (Gio.FileMonitorEvent.CREATED,
                          Gio.FileMonitorEvent.DELETED,
                          Gio.FileMonitorEvent.MOVED_IN,
                          Gio.FileMonitorEvent.MOVED_OUT):
            GLib.timeout_add(300, self.refresh)

    def refresh(self):
        self.store.clear()
        if self._root and self._root.is_dir():
            self._populate(self._root, None)
        return False

    def _populate(self, dirpath, parent_iter):
        try:
            entries = sorted(dirpath.iterdir(),
                             key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return

        for entry in entries:
            if entry.name.startswith(".") and entry.name in IGNORE_DIRS:
                continue
            if entry.is_dir():
                if entry.name in IGNORE_DIRS:
                    continue
                icon = "folder-symbolic"
                it = self.store.append(parent_iter,
                                       [entry.name, str(entry), True, icon])
                self._populate(entry, it)
            else:
                if entry.suffix in IGNORE_FILES:
                    continue
                icon = self._get_file_icon(entry)
                self.store.append(parent_iter,
                                  [entry.name, str(entry), False, icon])

    def _get_file_icon(self, path):
        if path.suffix == ".py":
            return "text-x-python-symbolic"
        return "text-x-generic-symbolic"

    def _on_row_activated(self, tree, treepath, column):
        it = self.store.get_iter(treepath)
        is_dir = self.store.get_value(it, self.COL_IS_DIR)
        filepath = self.store.get_value(it, self.COL_PATH)
        if not is_dir:
            self.app.editor_manager.open_document(filepath)

    def _on_button_press(self, widget, event):
        if event.button == 3:
            path_info = self.tree.get_path_at_pos(int(event.x), int(event.y))
            if path_info:
                treepath, col, cx, cy = path_info
                self.tree.set_cursor(treepath, col, False)
                self._show_context_menu(event, treepath)
            return True
        return False

    def _show_context_menu(self, event, treepath):
        it = self.store.get_iter(treepath)
        filepath = self.store.get_value(it, self.COL_PATH)
        is_dir = self.store.get_value(it, self.COL_IS_DIR)

        menu = Gtk.Menu()

        if is_dir:
            item_new_file = Gtk.MenuItem(label="New File Here")
            item_new_file.connect("activate", lambda w: self._create_file_in(filepath))
            menu.append(item_new_file)

            item_new_folder = Gtk.MenuItem(label="New Folder Here")
            item_new_folder.connect("activate", lambda w: self._create_folder_in(filepath))
            menu.append(item_new_folder)

        item_rename = Gtk.MenuItem(label="Rename")
        item_rename.connect("activate", lambda w: self._rename_item(filepath))
        menu.append(item_rename)

        item_delete = Gtk.MenuItem(label="Delete")
        item_delete.connect("activate", lambda w: self._delete_item(filepath, is_dir))
        menu.append(item_delete)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _prompt_name(self, title, default=""):
        dialog = Gtk.Dialog(title=title, parent=self.app.window,
                            flags=Gtk.DialogFlags.MODAL)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OK, Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_text(default)
        entry.set_activates_default(True)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.get_content_area().pack_start(entry, True, True, 8)
        dialog.get_content_area().show_all()
        resp = dialog.run()
        name = entry.get_text().strip()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK and name:
            return name
        return None

    def _on_new_file(self, btn):
        if self._root:
            self._create_file_in(str(self._root))

    def _on_new_folder(self, btn):
        if self._root:
            self._create_folder_in(str(self._root))

    def _create_file_in(self, dirpath):
        name = self._prompt_name("New File")
        if name:
            p = Path(dirpath) / name
            try:
                p.touch()
                self.refresh()
                self.app.editor_manager.open_document(str(p))
            except OSError as e:
                self._error_dialog(str(e))

    def _create_folder_in(self, dirpath):
        name = self._prompt_name("New Folder")
        if name:
            p = Path(dirpath) / name
            try:
                p.mkdir(parents=True, exist_ok=True)
                self.refresh()
            except OSError as e:
                self._error_dialog(str(e))

    def _rename_item(self, filepath):
        p = Path(filepath)
        name = self._prompt_name("Rename", p.name)
        if name and name != p.name:
            try:
                new_path = p.parent / name
                p.rename(new_path)
                self.refresh()
            except OSError as e:
                self._error_dialog(str(e))

    def _delete_item(self, filepath, is_dir):
        dialog = Gtk.MessageDialog(
            parent=self.app.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Delete '{Path(filepath).name}'?")
        resp = dialog.run()
        dialog.destroy()
        if resp == Gtk.ResponseType.YES:
            try:
                p = Path(filepath)
                if is_dir:
                    import shutil
                    shutil.rmtree(p)
                else:
                    p.unlink()
                self.refresh()
            except OSError as e:
                self._error_dialog(str(e))

    def _error_dialog(self, msg):
        dialog = Gtk.MessageDialog(
            parent=self.app.window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=msg)
        dialog.run()
        dialog.destroy()
