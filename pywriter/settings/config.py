import json
from pathlib import Path

DEFAULT_SETTINGS = {
    "tab_width": 4,
    "lint_on_save": True,
    "format_on_save": False,
    "font_size": 12,
    "font_family": "Monospace",
    "show_line_numbers": True,
    "highlight_current_line": True,
    "wrap_text": False,
    "theme": "classic",
    "lint_debounce_ms": 500,
    "large_file_threshold": 10000,
}

CONFIG_DIR = Path.home() / ".config" / "pywriter"
CONFIG_FILE = CONFIG_DIR / "settings.json"


class Config:
    def __init__(self):
        self._data = dict(DEFAULT_SETTINGS)
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    user = json.load(f)
                self._data.update(user)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
