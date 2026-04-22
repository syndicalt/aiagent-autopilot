"""
Thin HTTP client for the Autopilot Brain embedding service.

When the brain is running on localhost:8765, this module delegates
to it. When the brain is unavailable, it falls back to Miscellaneous
so the agent never blocks on network failures.

The brain service (brain/main.py) must be started separately or via
auto-launch from main.py.
"""

import urllib.request
import urllib.error
import json
from pathlib import Path

BRAIN_URL = "http://127.0.0.1:8765"


def _brain_available() -> bool:
    try:
        urllib.request.urlopen(f"{BRAIN_URL}/status", timeout=0.5)
        return True
    except Exception:
        return False


def classify_file(file_path: Path) -> str:
    """
    Ask the brain service to classify a file. Falls back to Miscellaneous
    if the brain is not running or returns an error.
    """
    if not _brain_available():
        return "Miscellaneous"

    try:
        req = urllib.request.Request(
            f"{BRAIN_URL}/classify-file",
            data=json.dumps({"path": str(file_path)}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            result = json.loads(resp.read().decode())
            return result.get("category", "Miscellaneous")
    except Exception:
        return "Miscellaneous"


def warm_up():
    """Ping the brain to trigger lazy model loading in the background."""
    try:
        urllib.request.urlopen(f"{BRAIN_URL}/status", timeout=2.0)
    except Exception:
        pass


def is_model_ready() -> bool:
    """Check whether the brain service has the model loaded."""
    try:
        with urllib.request.urlopen(f"{BRAIN_URL}/status", timeout=0.5) as resp:
            result = json.loads(resp.read().decode())
            return result.get("ready", False)
    except Exception:
        return False
