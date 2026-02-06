from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class WorkspaceManager:
    """Manages the current workspace root directory."""

    def __init__(self, app):
        self.app = app
        self._root = None

    @property
    def root(self):
        return self._root

    def open_folder(self, path=None):
        if path is None:
            path = self._choose_folder()
        if path:
            self._root = Path(path)
            self.app.on_workspace_changed(self._root)

    def _choose_folder(self):
        dialog = Gtk.FileChooserDialog(
            title="Open Folder",
            parent=self.app.window,
            action=Gtk.FileChooserAction.SELECT_FOLDER)
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)

        result = None
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            result = dialog.get_filename()
        dialog.destroy()
        return result

    def close_folder(self):
        self._root = None
        self.app.on_workspace_changed(None)
