from pathlib import Path

import gi
gi.require_version("GtkSource", "4")
from gi.repository import GtkSource, GLib


class Document:
    def __init__(self, path=None, encoding="utf-8", eol_mode="unix"):
        self.path = Path(path) if path else None
        self.encoding = encoding
        self.eol_mode = eol_mode

        self.buffer = GtkSource.Buffer()
        lang_manager = GtkSource.LanguageManager.get_default()
        self.buffer.set_language(lang_manager.get_language("python3"))
        self.buffer.set_highlight_syntax(True)

        style_manager = GtkSource.StyleSchemeManager.get_default()
        scheme = style_manager.get_scheme("oblivion")
        if scheme:
            self.buffer.set_style_scheme(scheme)

        self.buffer.set_max_undo_levels(-1)
        self.buffer.connect("modified-changed", self._on_modified_changed)

        self._dirty = False

        if self.path and self.path.exists():
            self._load_from_disk()

    @property
    def dirty(self):
        return self._dirty

    @property
    def title(self):
        name = self.path.name if self.path else "Untitled"
        return f"*{name}" if self._dirty else name

    def _on_modified_changed(self, buf):
        self._dirty = buf.get_modified()

    def _load_from_disk(self):
        try:
            text = self.path.read_text(encoding=self.encoding)
            self.buffer.begin_not_undoable_action()
            self.buffer.set_text(text)
            self.buffer.end_not_undoable_action()
            self.buffer.set_modified(False)
            self.buffer.place_cursor(self.buffer.get_start_iter())
        except (OSError, UnicodeDecodeError) as e:
            print(f"Error loading {self.path}: {e}")

    def save(self, path=None):
        if path:
            self.path = Path(path)
        if not self.path:
            return False
        try:
            start = self.buffer.get_start_iter()
            end = self.buffer.get_end_iter()
            text = self.buffer.get_text(start, end, True)
            self.path.write_text(text, encoding=self.encoding)
            self.buffer.set_modified(False)
            return True
        except OSError as e:
            print(f"Error saving {self.path}: {e}")
            return False

    def get_text(self):
        start = self.buffer.get_start_iter()
        end = self.buffer.get_end_iter()
        return self.buffer.get_text(start, end, True)

    def get_line_count(self):
        return self.buffer.get_line_count()
