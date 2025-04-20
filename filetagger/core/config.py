# core/config.py
import os
import sys
import json
import string

SETTINGS_FILE = "resources/config/settings.json" # Ny sökväg för inställningar
DEFAULT_SHORTCUT_KEYS = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"]
ALLOWED_SHORTCUT_KEYS = set(list(string.ascii_uppercase) + list(string.digits) + list(string.punctuation) +
                           ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12'])
DISALLOWED_KEYS = {"CAPSLOCK", "TAB", "ESCAPE"}
DEFAULT_ALLOWED_EXTENSIONS = [".jpg", ".png", ".jpeg", ".gif"]

# Funktion för att hitta resurser i både paketerad och opakterad miljö
def resource_path(relative_path):
    """Hämta absolut sökväg till resurs, fungerar både i dev och paketerad miljö."""
    try:
        # PyInstaller skapar en temporär mapp och lagrar sökvägen i _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Vi kör i en opakterad miljö (t.ex. under utveckling)
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "resources", "icons", relative_path) # Ändrat sökvägen till "resources/icons"

def load_settings():
    settings = {
        "last_folder": "",
        "shortcut_keys": list(DEFAULT_SHORTCUT_KEYS),
        "tags": [""] * len(DEFAULT_SHORTCUT_KEYS),
        "allowed_extensions": list(DEFAULT_ALLOWED_EXTENSIONS),
        "window_geometry": "800x600+100+100",
        "horizontal_sash_pos": 300,
        "vertical_sash_pos": 400,
        "metadata_sash_pos": 300,
        "imgbb_api_key": "",
        "serpapi_api_key": "",
        "google_maps_api_key": "",
        "archived_files": [],
        "external_viewer_path": ""
    }
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            loaded_settings = json.load(f)
            settings.update(loaded_settings) # Uppdatera default inställningar med de laddade
    return settings

def save_settings(app):
    window_geometry = app.root.geometry()
    horizontal_sash_pos = app.paned_window.sashpos(0)
    vertical_sash_pos = app.right_paned_window.sashpos(0)
    metadata_sash_pos = app.bottom_paned_window.sashpos(0)

    settings = {
        "last_folder": app.folder,
        "shortcut_keys": app.shortcut_keys,
        "tags": app.tags,
        "allowed_extensions": app.allowed_extensions,
        "window_geometry": window_geometry,
        "horizontal_sash_pos": horizontal_sash_pos,
        "vertical_sash_pos": vertical_sash_pos,
        "metadata_sash_pos": metadata_sash_pos,
        "imgbb_api_key": app.imgbb_api_key,
        "serpapi_api_key": app.serpapi_api_key,
        "archived_files": app.archived_files,
        "external_viewer_path": app.external_viewer_path,
        "google_maps_api_key": app.google_maps_api_key
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)
