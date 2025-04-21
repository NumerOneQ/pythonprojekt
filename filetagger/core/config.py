# core/config.py
import os
import sys
import json
import string
from dotenv import load_dotenv, find_dotenv

# Läs in .env-filen MER ROBUST
# find_dotenv() letar efter .env uppåt från denna fils katalog
dotenv_path = find_dotenv(raise_error_if_not_found=False) # raise_error=False gör att det inte kraschar om den inte hittas


if dotenv_path:
    # Ladda från den specifika sökvägen som hittades
    loaded = load_dotenv(dotenv_path=dotenv_path, override=True) # override=True kan hjälpa om variabler redan är satta i miljön
else:
    print("Warning: .env file not found by find_dotenv(). Will rely on existing environment variables if any.")
    # Programmet fortsätter, men os.getenv() kommer troligen returnera "" för nycklarna


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
    # Standardvärden för inställningar som *ska* sparas/laddas från JSON
    default_persistent_settings = {
        "last_folder": "",
        "shortcut_keys": list(DEFAULT_SHORTCUT_KEYS),
        "tags": [""] * len(DEFAULT_SHORTCUT_KEYS),
        "allowed_extensions": list(DEFAULT_ALLOWED_EXTENSIONS),
        "window_geometry": "800x600+100+100",
        "horizontal_sash_pos": 300,
        "vertical_sash_pos": 400,
        "metadata_sash_pos": 300,
        "archived_files": [],
        "external_viewer_path": ""
    }

    # Skapa en kopia att arbeta med
    settings = default_persistent_settings.copy()

    # Försök ladda inställningar från JSON-filen
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                loaded_settings = json.load(f)
                # Uppdatera bara de nycklar som finns i default_persistent_settings
                for key in default_persistent_settings:
                    if key in loaded_settings:
                        settings[key] = loaded_settings[key]
        except json.JSONDecodeError:
            print(f"Varning: Fel vid avkodning av {SETTINGS_FILE}. Använder standardvärden.")
        except Exception as e:
            print(f"Varning: Fel vid läsning av {SETTINGS_FILE}: {e}. Använder standardvärden.")

    # Läs ALLTID API-nycklar från miljövariabler (laddade från .env)
    # Ge tom sträng som standard om de inte finns
    settings["imgbb_api_key"] = os.getenv("IMGBB_API_KEY", "")
    settings["serpapi_api_key"] = os.getenv("SERPAPI_API_KEY", "")
    settings["google_maps_api_key"] = os.getenv("GOOGLE_MAPS_API_KEY", "")

    # Säkerställ att listlängderna stämmer överens efter laddning
    num_shortcuts = len(settings["shortcut_keys"])
    # Pad tags if needed
    if len(settings["tags"]) < num_shortcuts:
        settings["tags"].extend([""] * (num_shortcuts - len(settings["tags"])))
    # Truncate tags if needed (e.g., if shortcut_keys was shortened)
    elif len(settings["tags"]) > num_shortcuts:
        settings["tags"] = settings["tags"][:num_shortcuts]

    # Säkerställ att allowed_extensions inte är tom efter laddning
    if not settings.get("allowed_extensions"): # Använd .get() för säkerhets skull
         settings["allowed_extensions"] = list(DEFAULT_ALLOWED_EXTENSIONS)
         print("Varning: Laddade tillägg var tomma, återgår till standard.")


    return settings

def save_settings(app):
    window_geometry = app.root.geometry()
    horizontal_sash_pos = app.paned_window.sashpos(0)
    vertical_sash_pos = app.right_paned_window.sashpos(0)
    metadata_sash_pos = app.bottom_paned_window.sashpos(0)

    # Samla endast de inställningar som ska sparas i JSON
    settings_to_save = {
        "last_folder": app.folder,
        "shortcut_keys": app.shortcut_keys,
        "tags": app.tags,
        "allowed_extensions": app.allowed_extensions,
        "window_geometry": window_geometry,
        "horizontal_sash_pos": horizontal_sash_pos,
        "vertical_sash_pos": vertical_sash_pos,
        "metadata_sash_pos": metadata_sash_pos,
        # Inkludera INTE API-nycklarna här
        # "imgbb_api_key": app.imgbb_api_key,        # << BORTTAGEN
        # "serpapi_api_key": app.serpapi_api_key,    # << BORTTAGEN
        # "google_maps_api_key": app.google_maps_api_key, # << BORTTAGEN
        "archived_files": app.archived_files,
        "external_viewer_path": app.external_viewer_path,
    }

    try:
        # Säkerställ att katalogen finns
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings_to_save, f, indent=4) # Lägg till indent för läsbarhet
    except Exception as e:
         print(f"Fel vid sparande av inställningar till {SETTINGS_FILE}: {e}")
