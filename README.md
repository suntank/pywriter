# PyWriter IDE

A lightweight Python IDE optimized for Raspberry Pi Zero 2 W.

## Features

- **GtkSourceView editor** with syntax highlighting, undo/redo, line numbers
- **Tabbed editing** with open/save/close support
- **File tree** browser with create/rename/delete
- **Python outline** panel (classes & functions via AST)
- **Ruff linting** with debounced, per-file analysis and inline error markers
- **Formatting** via ruff format or black
- **Run scripts** with output capture
- **Find/Replace** with regex support
- **Editor commands**: duplicate line, move line up/down, toggle comment
- **Problems panel** with clickable diagnostics
- **Status bar** with cursor position

## Requirements

- Python 3.7+
- GTK 3 and GtkSourceView 4 (PyGObject bindings)
- Linux (tested on Debian Buster ARM)

### System dependencies (Debian/Raspbian)

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gtksource-4
```

### Optional tools

```bash
pip install ruff    # linting + formatting
pip install black   # fallback formatter
```

## Running

```bash
python3 run.py [path_to_folder_or_file]
```

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| Ctrl+N | New File |
| Ctrl+O | Open File |
| Ctrl+S | Save |
| Ctrl+Shift+S | Save As |
| Ctrl+W | Close Tab |
| Ctrl+F | Find/Replace |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Ctrl+Shift+D | Duplicate Line |
| Alt+Up/Down | Move Line Up/Down |
| Ctrl+/ | Toggle Comment |
| Ctrl+Shift+B | Run File |
| Ctrl+Shift+I | Format Document |

## Project Structure

```
pywriter/
  main.py              # Entry point
  app.py               # App shell, UI layout, menu bar
  workspace.py         # Workspace folder manager
  editor/
    document.py        # Document model (GtkSourceBuffer)
    editor_view.py     # EditorManager, tabbed views, find bar
    commands.py        # Command registry and keybindings
  panels/
    file_tree.py       # File browser panel
    problems.py        # Lint diagnostics panel
    outline.py         # AST-based outline panel
    output.py          # Program output panel
  language/
    python_provider.py # Coordinates lint + format
    lint.py            # Ruff subprocess runner
    format.py          # Ruff/Black formatter
  tools/
    runner.py          # Python script runner
  settings/
    config.py          # JSON settings persistence
```
