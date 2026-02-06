import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


class Command:
    def __init__(self, cmd_id, name, shortcut, callback):
        self.id = cmd_id
        self.name = name
        self.shortcut = shortcut
        self.callback = callback


class EditorCommands:
    """Registers and executes editor commands bound to the active editor view."""

    def __init__(self, app):
        self.app = app
        self._commands = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(Command("duplicate_line", "Duplicate Line",
                              "<Ctrl><Shift>d", self._duplicate_line))
        self.register(Command("move_line_up", "Move Line Up",
                              "<Alt>Up", self._move_line_up))
        self.register(Command("move_line_down", "Move Line Down",
                              "<Alt>Down", self._move_line_down))
        self.register(Command("comment_toggle", "Toggle Comment",
                              "<Ctrl>slash", self._comment_toggle))
        self.register(Command("find", "Find",
                              "<Ctrl>f", self._find))
        self.register(Command("save", "Save",
                              "<Ctrl>s", self._save))
        self.register(Command("save_as", "Save As",
                              "<Ctrl><Shift>s", self._save_as))
        self.register(Command("new_file", "New File",
                              "<Ctrl>n", self._new_file))
        self.register(Command("open_file", "Open File",
                              "<Ctrl>o", self._open_file))
        self.register(Command("close_tab", "Close Tab",
                              "<Ctrl>w", self._close_tab))
        self.register(Command("run_file", "Run File",
                              "<Ctrl><Shift>b", self._run_file))
        self.register(Command("format_document", "Format Document",
                              "<Ctrl><Shift>i", self._format_document))

    def register(self, command):
        self._commands[command.id] = command

    def get(self, cmd_id):
        return self._commands.get(cmd_id)

    def all(self):
        return list(self._commands.values())

    def bind_accel_group(self, window):
        accel_group = Gtk.AccelGroup()
        for cmd in self._commands.values():
            if cmd.shortcut:
                key, mods = Gtk.accelerator_parse(cmd.shortcut)
                if key:
                    accel_group.connect(key, mods, Gtk.AccelFlags.VISIBLE,
                                        lambda *a, c=cmd: (c.callback(), True))
        window.add_accel_group(accel_group)

    def _get_active_buffer(self):
        editor_mgr = self.app.editor_manager
        if editor_mgr and editor_mgr.active_document:
            return editor_mgr.active_document.buffer
        return None

    def _get_active_view(self):
        editor_mgr = self.app.editor_manager
        if editor_mgr:
            return editor_mgr.get_active_view()
        return None

    # --- Command Implementations ---

    def _duplicate_line(self):
        buf = self._get_active_buffer()
        if not buf:
            return
        mark = buf.get_insert()
        it = buf.get_iter_at_mark(mark)
        line = it.get_line()
        start = buf.get_iter_at_line(line)
        end = start.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        text = buf.get_text(start, end, True)
        buf.insert(end, "\n" + text)

    def _move_line_up(self):
        buf = self._get_active_buffer()
        if not buf:
            return
        mark = buf.get_insert()
        it = buf.get_iter_at_mark(mark)
        line = it.get_line()
        if line == 0:
            return
        start = buf.get_iter_at_line(line)
        end = start.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        text = buf.get_text(start, end, True)
        # Delete current line including preceding newline
        del_start = start.copy()
        del_start.backward_char()
        buf.begin_user_action()
        buf.delete(del_start, end)
        # Insert above previous line
        target = buf.get_iter_at_line(line - 1)
        buf.insert(target, text + "\n")
        # Place cursor
        new_iter = buf.get_iter_at_line(line - 1)
        buf.place_cursor(new_iter)
        buf.end_user_action()

    def _move_line_down(self):
        buf = self._get_active_buffer()
        if not buf:
            return
        mark = buf.get_insert()
        it = buf.get_iter_at_mark(mark)
        line = it.get_line()
        if line >= buf.get_line_count() - 1:
            return
        start = buf.get_iter_at_line(line)
        end = start.copy()
        if not end.ends_line():
            end.forward_to_line_end()
        text = buf.get_text(start, end, True)
        # Delete line including trailing newline
        del_end = end.copy()
        del_end.forward_char()
        buf.begin_user_action()
        buf.delete(start, del_end)
        # Insert below
        target = buf.get_iter_at_line(line + 1)
        if not target.ends_line():
            target.forward_to_line_end()
        buf.insert(target, "\n" + text)
        new_iter = buf.get_iter_at_line(line + 1)
        buf.place_cursor(new_iter)
        buf.end_user_action()

    def _comment_toggle(self):
        buf = self._get_active_buffer()
        if not buf:
            return
        if buf.get_has_selection():
            start, end = buf.get_selection_bounds()
        else:
            mark = buf.get_insert()
            start = buf.get_iter_at_mark(mark)
            end = start.copy()
        first_line = start.get_line()
        last_line = end.get_line()
        buf.begin_user_action()
        all_commented = True
        for ln in range(first_line, last_line + 1):
            it = buf.get_iter_at_line(ln)
            e = it.copy()
            if not e.ends_line():
                e.forward_to_line_end()
            line_text = buf.get_text(it, e, True)
            stripped = line_text.lstrip()
            if stripped and not stripped.startswith("#"):
                all_commented = False
                break
        for ln in range(first_line, last_line + 1):
            it = buf.get_iter_at_line(ln)
            e = it.copy()
            if not e.ends_line():
                e.forward_to_line_end()
            line_text = buf.get_text(it, e, True)
            if all_commented:
                idx = line_text.find("# ")
                if idx >= 0:
                    ds = buf.get_iter_at_line_offset(ln, idx)
                    de = buf.get_iter_at_line_offset(ln, idx + 2)
                    buf.delete(ds, de)
                else:
                    idx = line_text.find("#")
                    if idx >= 0:
                        ds = buf.get_iter_at_line_offset(ln, idx)
                        de = buf.get_iter_at_line_offset(ln, idx + 1)
                        buf.delete(ds, de)
            else:
                buf.insert(it, "# ")
        buf.end_user_action()

    def _find(self):
        if self.app.editor_manager:
            self.app.editor_manager.show_find_bar()

    def _save(self):
        if self.app.editor_manager:
            self.app.editor_manager.save_current()

    def _save_as(self):
        if self.app.editor_manager:
            self.app.editor_manager.save_current_as()

    def _new_file(self):
        if self.app.editor_manager:
            self.app.editor_manager.open_document(None)

    def _open_file(self):
        if self.app.editor_manager:
            self.app.editor_manager.open_file_dialog()

    def _close_tab(self):
        if self.app.editor_manager:
            self.app.editor_manager.close_current_tab()

    def _run_file(self):
        if not self.app.runner or not self.app.editor_manager:
            return
        doc = self.app.editor_manager.active_document
        if not doc:
            return
        # Save first if dirty or untitled
        if not doc.path:
            self.app.editor_manager.save_current_as()
            if not doc.path:
                return
        elif doc.dirty:
            doc.save()
        # Switch to Output tab and clear
        if self.app.bottom_notebook:
            self.app.bottom_notebook.set_current_page(1)
        self.app.output_panel.clear()
        self.app.runner.run(doc.path)

    def _format_document(self):
        if self.app.python_provider:
            doc = self.app.editor_manager.active_document if self.app.editor_manager else None
            if doc and doc.path:
                doc.save()
                self.app.python_provider.format_file(doc.path, self._on_format_done)

    def _on_format_done(self, path, success):
        if success and self.app.editor_manager:
            self.app.editor_manager.reload_document(path)
