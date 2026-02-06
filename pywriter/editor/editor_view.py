import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkSource", "4")
from gi.repository import Gtk, Gdk, GLib, GtkSource

from pathlib import Path
from .document import Document


class FindBar(Gtk.Revealer):
    """Inline find/replace bar for the editor."""

    def __init__(self, editor_manager):
        super().__init__()
        self.editor_manager = editor_manager
        self.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_name("find-bar")
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_margin_top(2)
        box.set_margin_bottom(2)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_size_request(250, -1)
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_entry.connect("activate", self._on_next)
        box.pack_start(self.search_entry, False, False, 0)

        btn_next = Gtk.Button(label="Next")
        btn_next.connect("clicked", self._on_next)
        box.pack_start(btn_next, False, False, 0)

        btn_prev = Gtk.Button(label="Prev")
        btn_prev.connect("clicked", self._on_prev)
        box.pack_start(btn_prev, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        box.pack_start(sep, False, False, 4)

        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("Replace")
        self.replace_entry.set_size_request(200, -1)
        box.pack_start(self.replace_entry, False, False, 0)

        btn_replace = Gtk.Button(label="Replace")
        btn_replace.connect("clicked", self._on_replace)
        box.pack_start(btn_replace, False, False, 0)

        btn_replace_all = Gtk.Button(label="All")
        btn_replace_all.connect("clicked", self._on_replace_all)
        box.pack_start(btn_replace_all, False, False, 0)

        btn_close = Gtk.Button()
        btn_close.set_image(Gtk.Image.new_from_icon_name("window-close-symbolic",
                                                          Gtk.IconSize.BUTTON))
        btn_close.set_relief(Gtk.ReliefStyle.NONE)
        btn_close.connect("clicked", lambda b: self.hide_bar())
        box.pack_end(btn_close, False, False, 0)

        self.match_label = Gtk.Label(label="")
        box.pack_end(self.match_label, False, False, 4)

        self.add(box)
        self.show_all()
        self._search_context = None
        self._search_settings = GtkSource.SearchSettings()
        self._search_settings.set_wrap_around(True)

    def show_bar(self):
        self.set_reveal_child(True)
        self.search_entry.grab_focus()
        buf = self._get_buffer()
        if buf and buf.get_has_selection():
            start, end = buf.get_selection_bounds()
            self.search_entry.set_text(buf.get_text(start, end, True))

    def hide_bar(self):
        self.set_reveal_child(False)
        view = self.editor_manager.get_active_view()
        if view:
            view.grab_focus()

    def _get_buffer(self):
        doc = self.editor_manager.active_document
        return doc.buffer if doc else None

    def _ensure_context(self):
        buf = self._get_buffer()
        if not buf:
            self._search_context = None
            return
        if self._search_context is None or self._search_context.get_buffer() != buf:
            self._search_context = GtkSource.SearchContext.new(buf, self._search_settings)
            self._search_context.set_highlight(True)

    def _on_search_changed(self, entry):
        text = entry.get_text()
        self._search_settings.set_search_text(text if text else None)
        self._ensure_context()
        if self._search_context and text:
            count = self._search_context.get_occurrences_count()
            if count >= 0:
                self.match_label.set_text(f"{count} matches")
            else:
                self.match_label.set_text("")
        else:
            self.match_label.set_text("")

    def _on_next(self, *args):
        self._ensure_context()
        buf = self._get_buffer()
        if not self._search_context or not buf:
            return
        mark = buf.get_insert()
        it = buf.get_iter_at_mark(mark)
        found, start, end, wrapped = self._search_context.forward(it)
        if found:
            buf.select_range(start, end)
            view = self.editor_manager.get_active_view()
            if view:
                view.scroll_to_mark(buf.get_insert(), 0.1, False, 0, 0)

    def _on_prev(self, *args):
        self._ensure_context()
        buf = self._get_buffer()
        if not self._search_context or not buf:
            return
        mark = buf.get_insert()
        it = buf.get_iter_at_mark(mark)
        found, start, end, wrapped = self._search_context.backward(it)
        if found:
            buf.select_range(start, end)
            view = self.editor_manager.get_active_view()
            if view:
                view.scroll_to_mark(buf.get_insert(), 0.1, False, 0, 0)

    def _on_replace(self, *args):
        self._ensure_context()
        buf = self._get_buffer()
        if not self._search_context or not buf:
            return
        if buf.get_has_selection():
            start, end = buf.get_selection_bounds()
            replacement = self.replace_entry.get_text()
            self._search_context.replace(start, end, replacement, len(replacement.encode()))
            self._on_next()

    def _on_replace_all(self, *args):
        self._ensure_context()
        if not self._search_context:
            return
        replacement = self.replace_entry.get_text()
        self._search_context.replace_all(replacement, len(replacement.encode()))


class EditorManager(Gtk.Box):
    """Manages tabbed editor views with find bar."""

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app
        self._documents = []
        self._views = {}
        self.active_document = None

        self.find_bar = FindBar(self)
        self.pack_start(self.find_bar, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.connect("switch-page", self._on_switch_page)
        self.pack_start(self.notebook, True, True, 0)

    def open_document(self, path):
        if path:
            path = Path(path)
            for i, doc in enumerate(self._documents):
                if doc.path and doc.path.resolve() == path.resolve():
                    self.notebook.set_current_page(i)
                    return doc

        doc = Document(path)
        self._documents.append(doc)
        view = self._create_view(doc)
        self._views[id(doc)] = view

        scrolled = Gtk.ScrolledWindow()
        scrolled.add(view)

        tab_label = self._make_tab_label(doc)
        page_num = self.notebook.append_page(scrolled, tab_label)
        self.notebook.set_tab_reorderable(scrolled, True)
        scrolled.show_all()
        self.notebook.set_current_page(page_num)

        doc.buffer.connect("modified-changed", lambda b, d=doc: self._update_tab_label(d))
        return doc

    def _create_view(self, doc):
        view = GtkSource.View.new_with_buffer(doc.buffer)
        config = self.app.config

        view.set_show_line_numbers(config.get("show_line_numbers", True))
        view.set_highlight_current_line(config.get("highlight_current_line", True))
        view.set_auto_indent(True)
        view.set_indent_on_tab(True)
        view.set_tab_width(config.get("tab_width", 4))
        view.set_insert_spaces_instead_of_tabs(True)
        view.set_smart_backspace(True)
        view.set_show_line_marks(True)

        if config.get("wrap_text", False):
            view.set_wrap_mode(Gtk.WrapMode.WORD)
        else:
            view.set_wrap_mode(Gtk.WrapMode.NONE)

        font_family = config.get('font_family', 'Monospace')
        font_size = config.get('font_size', 12)
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(
            f"textview {{ font-family: {font_family}; font-size: {font_size}pt; }}".encode()
        )
        view.get_style_context().add_provider(
            css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        view.set_left_margin(4)
        view.set_right_margin(4)

        space_drawer = view.get_space_drawer()
        space_drawer.set_enable_matrix(False)

        # Connect for lint debounce
        doc.buffer.connect("changed", self._on_buffer_changed)

        return view

    def _on_buffer_changed(self, buf):
        if self.app.python_provider and self.active_document:
            self.app.python_provider.schedule_lint(self.active_document)

    def _make_tab_label(self, doc):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        label = Gtk.Label(label=doc.title)
        label.set_name("tab-label")
        box.pack_start(label, True, True, 0)

        close_btn = Gtk.Button()
        close_btn.set_image(Gtk.Image.new_from_icon_name("window-close-symbolic",
                                                          Gtk.IconSize.MENU))
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect("clicked", lambda b, d=doc: self._close_document(d))
        box.pack_end(close_btn, False, False, 0)
        box.show_all()
        return box

    def _update_tab_label(self, doc):
        idx = self._documents.index(doc)
        page = self.notebook.get_nth_page(idx)
        tab_box = self.notebook.get_tab_label(page)
        if tab_box:
            label = tab_box.get_children()[0]
            label.set_text(doc.title)

    def _on_switch_page(self, notebook, page, page_num):
        if page_num < len(self._documents):
            self.active_document = self._documents[page_num]
            self.app.on_active_document_changed(self.active_document)

    def get_active_view(self):
        if self.active_document:
            return self._views.get(id(self.active_document))
        return None

    def show_find_bar(self):
        self.find_bar.show_bar()

    def save_current(self):
        doc = self.active_document
        if not doc:
            return
        if doc.path:
            doc.save()
            # Format on save if enabled
            if self.app.config.get("format_on_save") and str(doc.path).endswith(".py"):
                if self.app.python_provider:
                    self.app.python_provider.format_file(doc.path, self._on_format_after_save)
            elif self.app.config.get("lint_on_save"):
                if self.app.python_provider:
                    self.app.python_provider.schedule_lint(doc, immediate=True)
        else:
            self.save_current_as()

    def _on_format_after_save(self, path, success):
        if success:
            self.reload_document(path)
        doc = self.active_document
        if doc and self.app.config.get("lint_on_save"):
            if self.app.python_provider:
                self.app.python_provider.schedule_lint(doc, immediate=True)

    def save_current_as(self):
        doc = self.active_document
        if not doc:
            return
        dialog = Gtk.FileChooserDialog(
            title="Save As", parent=self.app.window,
            action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
        dialog.set_do_overwrite_confirmation(True)
        filt = Gtk.FileFilter()
        filt.set_name("Python files")
        filt.add_pattern("*.py")
        dialog.add_filter(filt)
        filt_all = Gtk.FileFilter()
        filt_all.set_name("All files")
        filt_all.add_pattern("*")
        dialog.add_filter(filt_all)

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            path = dialog.get_filename()
            doc.save(path)
            self._update_tab_label(doc)
        dialog.destroy()

    def open_file_dialog(self):
        dialog = Gtk.FileChooserDialog(
            title="Open File", parent=self.app.window,
            action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                           Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
        dialog.set_select_multiple(True)
        filt = Gtk.FileFilter()
        filt.set_name("Python files")
        filt.add_pattern("*.py")
        dialog.add_filter(filt)
        filt_all = Gtk.FileFilter()
        filt_all.set_name("All files")
        filt_all.add_pattern("*")
        dialog.add_filter(filt_all)

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            for path in dialog.get_filenames():
                self.open_document(path)
        dialog.destroy()

    def close_current_tab(self):
        doc = self.active_document
        if doc:
            self._close_document(doc)

    def _close_document(self, doc):
        if doc.dirty:
            dialog = Gtk.MessageDialog(
                parent=self.app.window,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.NONE,
                text=f"Save changes to {doc.title}?")
            dialog.add_buttons("Don't Save", Gtk.ResponseType.NO,
                               Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                               Gtk.STOCK_SAVE, Gtk.ResponseType.YES)
            resp = dialog.run()
            dialog.destroy()
            if resp == Gtk.ResponseType.CANCEL:
                return
            if resp == Gtk.ResponseType.YES:
                if doc.path:
                    doc.save()
                else:
                    self.save_current_as()
                    if doc.dirty:
                        return

        idx = self._documents.index(doc)
        self._documents.remove(doc)
        del self._views[id(doc)]
        self.notebook.remove_page(idx)

        if self._documents:
            new_idx = min(idx, len(self._documents) - 1)
            self.notebook.set_current_page(new_idx)
            self.active_document = self._documents[new_idx]
        else:
            self.active_document = None
            self.app.on_active_document_changed(None)

    def reload_document(self, path):
        path = Path(path)
        for doc in self._documents:
            if doc.path and doc.path.resolve() == path.resolve():
                doc._load_from_disk()
                self._update_tab_label(doc)
                break

    def goto_line(self, path, line):
        path = Path(path)
        doc = None
        for d in self._documents:
            if d.path and d.path.resolve() == path.resolve():
                doc = d
                break
        if not doc:
            doc = self.open_document(path)
        else:
            idx = self._documents.index(doc)
            self.notebook.set_current_page(idx)

        it = doc.buffer.get_iter_at_line(max(0, line - 1))
        doc.buffer.place_cursor(it)
        view = self._views.get(id(doc))
        if view:
            view.scroll_to_mark(doc.buffer.get_insert(), 0.1, True, 0, 0.5)
            view.grab_focus()
