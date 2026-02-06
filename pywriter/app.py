import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkSource", "4")
from gi.repository import Gtk, Gdk, GLib, Gio

from .settings.config import Config
from .workspace import WorkspaceManager
from .editor.editor_view import EditorManager
from .editor.commands import EditorCommands
from .panels.file_tree import FileTree
from .panels.problems import ProblemsPanel
from .panels.outline import OutlinePanel
from .panels.output import OutputPanel
from .language.python_provider import PythonProvider
from .tools.runner import ToolRunner


CSS = b"""
/* --- Main window --- */
window {
    background-color: #1e1e1e;
}

/* --- Menu bar --- */
menubar {
    background-color: #2d2d2d;
    color: #cccccc;
    padding: 0;
    border-bottom: 1px solid #404040;
}
menubar > menuitem {
    color: #cccccc;
    padding: 4px 8px;
}
menubar > menuitem:hover {
    background-color: #094771;
}
menu {
    background-color: #2d2d2d;
    color: #cccccc;
    border: 1px solid #404040;
}
menu > menuitem {
    color: #cccccc;
    padding: 4px 12px;
}
menu > menuitem:hover {
    background-color: #094771;
}

/* --- Notebook tabs --- */
notebook {
    background-color: #1e1e1e;
}
notebook header {
    background-color: #252526;
    border-bottom: 1px solid #404040;
}
notebook tab {
    background-color: #2d2d2d;
    color: #969696;
    padding: 4px 8px;
    min-height: 0;
    border: none;
}
notebook tab:checked {
    background-color: #1e1e1e;
    color: #ffffff;
    border-bottom: 2px solid #007acc;
}
notebook tab label {
    font-size: 11px;
}

/* --- Side panels --- */
#panel-header {
    background-color: #252526;
    padding: 4px 8px;
    border-bottom: 1px solid #404040;
}
#panel-header label {
    color: #bbbbbb;
    font-family: Sans;
    font-weight: bold;
    font-size: 9px;
}
#output-text {
    font-family: Monospace;
    font-size: 10px;
}

/* --- Tree views --- */
treeview {
    background-color: #252526;
    color: #cccccc;
}
treeview:selected {
    background-color: #094771;
    color: #ffffff;
}
treeview:hover {
    background-color: #2a2d2e;
}
treeview header button {
    background-color: #252526;
    color: #cccccc;
    border-bottom: 1px solid #404040;
}

/* --- Text views (output) --- */
textview {
    background-color: #1e1e1e;
    color: #cccccc;
}
textview text {
    background-color: #1e1e1e;
    color: #cccccc;
}

/* --- Paned separators --- */
paned > separator {
    background-color: #404040;
    min-width: 2px;
    min-height: 2px;
}

/* --- Scrollbars --- */
scrollbar {
    background-color: #1e1e1e;
}
scrollbar slider {
    background-color: #424242;
    min-width: 8px;
    min-height: 8px;
    border-radius: 4px;
}
scrollbar slider:hover {
    background-color: #4f4f4f;
}

/* --- Buttons in panels --- */
#panel-header button {
    background: none;
    border: none;
    color: #cccccc;
    padding: 2px;
}
#panel-header button:hover {
    background-color: #404040;
    border-radius: 3px;
}

/* --- Status bar --- */
#status-bar {
    background-color: #007acc;
    color: white;
    padding: 2px 10px;
    font-size: 11px;
}
#status-bar label {
    color: white;
    font-size: 11px;
}

/* --- Find bar --- */
#find-bar {
    background-color: #252526;
    border-bottom: 1px solid #404040;
    padding: 4px;
}
#find-bar entry {
    background-color: #3c3c3c;
    color: #cccccc;
    border: 1px solid #555555;
    border-radius: 2px;
}
#find-bar button {
    background-color: #3c3c3c;
    color: #cccccc;
    border: 1px solid #555555;
    border-radius: 2px;
    padding: 2px 8px;
}
#find-bar button:hover {
    background-color: #4f4f4f;
}
#find-bar label {
    color: #cccccc;
}

/* --- Entry / search entry --- */
entry {
    background-color: #3c3c3c;
    color: #cccccc;
    border: 1px solid #555555;
}

/* --- General label color fallback --- */
label {
    color: #cccccc;
}

/* --- Dialog fixes --- */
dialog {
    background-color: #2d2d2d;
}
messagedialog {
    background-color: #2d2d2d;
}
"""


class PyWriterApp:
    def __init__(self, open_path=None):
        self.config = Config()
        self.window = None
        self.editor_manager = None
        self.file_tree = None
        self.problems_panel = None
        self.outline_panel = None
        self.output_panel = None
        self.python_provider = None
        self.runner = None
        self.workspace = None
        self.commands = None

        self._status_label = None
        self._cursor_label = None
        self._open_path = open_path

    def run(self):
        self._apply_css()
        self._build_window()
        self._build_ui()
        self._setup_services()

        self.commands = EditorCommands(self)
        self.commands.bind_accel_group(self.window)
        self._build_menu_bar()

        self.window.show_all()

        # Open workspace if provided, otherwise open current directory or welcome document
        if self._open_path:
            p = Path(self._open_path)
            if p.is_dir():
                self.workspace.open_folder(p)
            elif p.is_file():
                self.workspace.open_folder(p.parent)
                self.editor_manager.open_document(str(p))
        else:
            # Open current directory as workspace
            current_dir = Path.cwd()
            self.workspace.open_folder(current_dir)
            self._open_welcome()

        Gtk.main()

    def _apply_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _build_window(self):
        self.window = Gtk.Window(title="PyWriter")
        self.window.set_default_size(1920, 1080)
        self.window.connect("delete-event", self._on_quit)
        self.window.set_icon_name("accessories-text-editor")

    def _build_ui(self):
        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Menu bar placeholder (populated after commands init)
        self._menu_bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        main_vbox.pack_start(self._menu_bar_box, False, False, 0)

        # Main horizontal paned: file_tree | editor+outline
        outer_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)

        # File tree (left)
        self.file_tree = FileTree(self)
        self.file_tree.set_size_request(220, -1)
        outer_paned.pack1(self.file_tree, resize=False, shrink=False)

        # Right side: vertical paned (top: editor+outline, bottom: panels)
        right_vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)

        # Top section: editor + outline
        top_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)

        self.editor_manager = EditorManager(self)
        top_paned.pack1(self.editor_manager, resize=True, shrink=False)

        self.outline_panel = OutlinePanel(self)
        self.outline_panel.set_size_request(200, -1)
        top_paned.pack2(self.outline_panel, resize=False, shrink=True)
        top_paned.set_position(1400)

        right_vpaned.pack1(top_paned, resize=True, shrink=False)

        # Bottom panels notebook
        self.bottom_notebook = Gtk.Notebook()
        self.bottom_notebook.set_size_request(-1, 180)

        self.problems_panel = ProblemsPanel(self)
        self.bottom_notebook.append_page(self.problems_panel, Gtk.Label(label="Problems"))

        self.output_panel = OutputPanel(self)
        self.bottom_notebook.append_page(self.output_panel, Gtk.Label(label="Output"))

        right_vpaned.pack2(self.bottom_notebook, resize=False, shrink=True)
        right_vpaned.set_position(700)

        outer_paned.pack2(right_vpaned, resize=True, shrink=False)
        outer_paned.set_position(220)

        main_vbox.pack_start(outer_paned, True, True, 0)

        # Status bar
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        status_bar.set_name("status-bar")

        self._status_label = Gtk.Label(label="Ready")
        self._status_label.set_xalign(0)
        status_bar.pack_start(self._status_label, True, True, 0)

        self._cursor_label = Gtk.Label(label="Ln 1, Col 1")
        status_bar.pack_end(self._cursor_label, False, False, 0)

        self._encoding_label = Gtk.Label(label="UTF-8")
        status_bar.pack_end(self._encoding_label, False, False, 0)

        main_vbox.pack_end(status_bar, False, False, 0)

        self.window.add(main_vbox)

    def _build_menu_bar(self):
        menu_bar = Gtk.MenuBar()

        # File menu
        file_menu = Gtk.Menu()
        file_item = Gtk.MenuItem(label="File")
        file_item.set_submenu(file_menu)

        new_item = Gtk.MenuItem(label="New File  Ctrl+N")
        new_item.connect("activate", lambda w: self.commands.get("new_file").callback())
        file_menu.append(new_item)

        open_item = Gtk.MenuItem(label="Open File  Ctrl+O")
        open_item.connect("activate", lambda w: self.commands.get("open_file").callback())
        file_menu.append(open_item)

        open_folder_item = Gtk.MenuItem(label="Open Folder")
        open_folder_item.connect("activate", lambda w: self.workspace.open_folder())
        file_menu.append(open_folder_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        save_item = Gtk.MenuItem(label="Save  Ctrl+S")
        save_item.connect("activate", lambda w: self.commands.get("save").callback())
        file_menu.append(save_item)

        save_as_item = Gtk.MenuItem(label="Save As  Ctrl+Shift+S")
        save_as_item.connect("activate", lambda w: self.commands.get("save_as").callback())
        file_menu.append(save_as_item)

        file_menu.append(Gtk.SeparatorMenuItem())

        close_tab_item = Gtk.MenuItem(label="Close Tab  Ctrl+W")
        close_tab_item.connect("activate", lambda w: self.commands.get("close_tab").callback())
        file_menu.append(close_tab_item)

        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda w: self._on_quit(None, None))
        file_menu.append(quit_item)

        menu_bar.append(file_item)

        # Edit menu
        edit_menu = Gtk.Menu()
        edit_item = Gtk.MenuItem(label="Edit")
        edit_item.set_submenu(edit_menu)

        undo_item = Gtk.MenuItem(label="Undo  Ctrl+Z")
        undo_item.connect("activate", lambda w: self._undo())
        edit_menu.append(undo_item)

        redo_item = Gtk.MenuItem(label="Redo  Ctrl+Shift+Z")
        redo_item.connect("activate", lambda w: self._redo())
        edit_menu.append(redo_item)

        edit_menu.append(Gtk.SeparatorMenuItem())

        find_item = Gtk.MenuItem(label="Find  Ctrl+F")
        find_item.connect("activate", lambda w: self.commands.get("find").callback())
        edit_menu.append(find_item)

        edit_menu.append(Gtk.SeparatorMenuItem())

        dup_item = Gtk.MenuItem(label="Duplicate Line  Ctrl+Shift+D")
        dup_item.connect("activate", lambda w: self.commands.get("duplicate_line").callback())
        edit_menu.append(dup_item)

        comment_item = Gtk.MenuItem(label="Toggle Comment  Ctrl+/")
        comment_item.connect("activate", lambda w: self.commands.get("comment_toggle").callback())
        edit_menu.append(comment_item)

        menu_bar.append(edit_item)

        # Run menu
        run_menu = Gtk.Menu()
        run_item = Gtk.MenuItem(label="Run")
        run_item.set_submenu(run_menu)

        run_file_item = Gtk.MenuItem(label="Run File  Ctrl+Shift+B")
        run_file_item.connect("activate", lambda w: self.commands.get("run_file").callback())
        run_menu.append(run_file_item)

        stop_item = Gtk.MenuItem(label="Stop")
        stop_item.connect("activate", lambda w: self.runner.stop() if self.runner else None)
        run_menu.append(stop_item)

        menu_bar.append(run_item)

        # Tools menu
        tools_menu = Gtk.Menu()
        tools_item = Gtk.MenuItem(label="Tools")
        tools_item.set_submenu(tools_menu)

        format_item = Gtk.MenuItem(label="Format Document  Ctrl+Shift+I")
        format_item.connect("activate",
                            lambda w: self.commands.get("format_document").callback())
        tools_menu.append(format_item)

        menu_bar.append(tools_item)

        # Help menu
        help_menu = Gtk.Menu()
        help_item = Gtk.MenuItem(label="Help")
        help_item.set_submenu(help_menu)

        about_item = Gtk.MenuItem(label="About PyWriter")
        about_item.connect("activate", self._show_about)
        help_menu.append(about_item)

        menu_bar.append(help_item)

        for child in self._menu_bar_box.get_children():
            self._menu_bar_box.remove(child)
        self._menu_bar_box.pack_start(menu_bar, True, True, 0)
        menu_bar.show_all()

    def _setup_services(self):
        self.workspace = WorkspaceManager(self)
        self.python_provider = PythonProvider(self)
        self.runner = ToolRunner(self)

    def on_workspace_changed(self, root):
        if root:
            self.file_tree.set_root(root)
            self.window.set_title(f"PyWriter — {root.name}")
            self._status_label.set_text(str(root))
        else:
            self.file_tree.set_root(None)
            self.window.set_title("PyWriter")
            self._status_label.set_text("Ready")

    def on_active_document_changed(self, doc):
        if doc:
            # Update outline
            self.outline_panel.update_for_document(doc)

            # Update cursor tracking
            doc.buffer.connect("notify::cursor-position", self._on_cursor_moved)
            self._update_cursor_label(doc.buffer)

            # Trigger lint
            if doc.path and str(doc.path).endswith(".py"):
                self.python_provider.schedule_lint(doc, immediate=True)

            # Update status
            name = doc.path.name if doc.path else "Untitled"
            self._status_label.set_text(name)
        else:
            self.outline_panel.update_for_document(None)
            self._cursor_label.set_text("")
            self._status_label.set_text("Ready")
            self.problems_panel.clear()

    def _on_cursor_moved(self, buf, pspec):
        self._update_cursor_label(buf)

    def _update_cursor_label(self, buf):
        mark = buf.get_insert()
        it = buf.get_iter_at_mark(mark)
        line = it.get_line() + 1
        col = it.get_line_offset() + 1
        self._cursor_label.set_text(f"Ln {line}, Col {col}")

    def _undo(self):
        doc = self.editor_manager.active_document if self.editor_manager else None
        if doc and doc.buffer.can_undo():
            doc.buffer.undo()

    def _redo(self):
        doc = self.editor_manager.active_document if self.editor_manager else None
        if doc and doc.buffer.can_redo():
            doc.buffer.redo()

    def _show_about(self, widget):
        dialog = Gtk.AboutDialog(parent=self.window)
        dialog.set_program_name("PyWriter")
        dialog.set_version("0.1.0")
        dialog.set_comments("A lightweight Python IDE for Raspberry Pi")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.run()
        dialog.destroy()

    def _open_welcome(self):
        doc = self.editor_manager.open_document(None)
        welcome = '''# Welcome to PyWriter!
# A lightweight Python IDE for Raspberry Pi.
#
# Getting started:
#   - File > Open Folder to open a project
#   - File > Open File to edit a single file
#   - Ctrl+S to save, Ctrl+Shift+B to run
#
# Try writing some Python:

def hello():
    print("Hello from PyWriter!")

hello()
'''
        doc.buffer.set_text(welcome)
        doc.buffer.set_modified(False)

    def _on_quit(self, widget, event):
        # Check for unsaved documents
        if self.editor_manager:
            for doc in self.editor_manager._documents:
                if doc.dirty:
                    dialog = Gtk.MessageDialog(
                        parent=self.window,
                        flags=Gtk.DialogFlags.MODAL,
                        message_type=Gtk.MessageType.QUESTION,
                        buttons=Gtk.ButtonsType.NONE,
                        text="You have unsaved changes. Quit anyway?")
                    dialog.add_buttons(
                        Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                        "Quit Without Saving", Gtk.ResponseType.YES)
                    resp = dialog.run()
                    dialog.destroy()
                    if resp != Gtk.ResponseType.YES:
                        return True
                    break

        if self.runner:
            self.runner.stop()
        self.config.save()
        Gtk.main_quit()
        return False
