import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class OutputPanel(Gtk.Box):
    """Bottom panel for program output and tool messages."""

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        toolbar.set_name("panel-header")
        toolbar.set_margin_start(4)
        toolbar.set_margin_end(4)
        toolbar.set_margin_top(2)

        lbl = Gtk.Label(label="OUTPUT")
        lbl.set_xalign(0)
        toolbar.pack_start(lbl, True, True, 0)

        btn_clear = Gtk.Button()
        btn_clear.set_image(Gtk.Image.new_from_icon_name("edit-clear-symbolic",
                                                          Gtk.IconSize.SMALL_TOOLBAR))
        btn_clear.set_relief(Gtk.ReliefStyle.NONE)
        btn_clear.set_tooltip_text("Clear Output")
        btn_clear.connect("clicked", lambda b: self.clear())
        toolbar.pack_end(btn_clear, False, False, 0)

        btn_stop = Gtk.Button()
        btn_stop.set_image(Gtk.Image.new_from_icon_name("process-stop-symbolic",
                                                         Gtk.IconSize.SMALL_TOOLBAR))
        btn_stop.set_relief(Gtk.ReliefStyle.NONE)
        btn_stop.set_tooltip_text("Stop Running Process")
        btn_stop.connect("clicked", lambda b: self._on_stop())
        toolbar.pack_end(btn_stop, False, False, 0)

        self.pack_start(toolbar, False, False, 0)

        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.set_left_margin(6)
        self.textview.set_right_margin(6)
        self.textview.set_name("output-text")

        self.buffer = self.textview.get_buffer()
        self.buffer.create_tag("error", foreground="#f44747")
        self.buffer.create_tag("info", foreground="#888888")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.textview)
        self.pack_start(scrolled, True, True, 0)

    def append(self, text, tag_name=None):
        def _do():
            end = self.buffer.get_end_iter()
            if tag_name:
                tag = self.buffer.get_tag_table().lookup(tag_name)
                if tag:
                    self.buffer.insert_with_tags(end, text, tag)
                else:
                    self.buffer.insert(end, text)
            else:
                self.buffer.insert(end, text)
            # Auto-scroll
            end = self.buffer.get_end_iter()
            self.buffer.place_cursor(end)
            self.textview.scroll_to_mark(self.buffer.get_insert(), 0.0, False, 0, 0)
        GLib.idle_add(_do)

    def clear(self):
        self.buffer.set_text("")

    def write_line(self, text, tag_name=None):
        self.append(text + "\n", tag_name)

    def _on_stop(self):
        if self.app.runner:
            self.app.runner.stop()
