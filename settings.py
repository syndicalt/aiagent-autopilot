import json
from pathlib import Path
from config import ORGANIZED_ROOT

SETTINGS_PATH = ORGANIZED_ROOT / ".settings.json"

def _ensure_settings():
    if not SETTINGS_PATH.exists():
        save_settings({"notifications_muted": False})

def load_settings() -> dict:
    _ensure_settings()
    try:
        with open(SETTINGS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {"notifications_muted": False}

def save_settings(settings: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)

def are_notifications_muted() -> bool:
    return load_settings().get("notifications_muted", False)

def toggle_notifications() -> bool:
    settings = load_settings()
    settings["notifications_muted"] = not settings.get("notifications_muted", False)
    save_settings(settings)
    return settings["notifications_muted"]

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--toggle":
        result = toggle_notifications()
        print(result)
    else:
        print(are_notifications_muted())
