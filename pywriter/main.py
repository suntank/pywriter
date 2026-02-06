#!/usr/bin/env python3
"""PyWriter — A lightweight Python IDE for Raspberry Pi."""

import sys
import signal

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkSource", "4")
from gi.repository import Gtk, GLib

from .app import PyWriterApp


def main():
    # Allow Ctrl+C to terminate
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    open_path = sys.argv[1] if len(sys.argv) > 1 else None
    app = PyWriterApp(open_path=open_path)
    app.run()


if __name__ == "__main__":
    main()
