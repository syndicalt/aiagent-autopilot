import os
from pathlib import Path

# Default Downloads folder
DOWNLOADS_DIR = Path.home() / "Downloads"

# Where organized folders live (inside Downloads by default)
ORGANIZED_ROOT = DOWNLOADS_DIR / "Autopilot"

# Extension-to-category mapping
CATEGORY_MAP = {
    # Images
    "jpg": "Images",
    "jpeg": "Images",
    "png": "Images",
    "gif": "Images",
    "bmp": "Images",
    "svg": "Images",
    "webp": "Images",
    # Documents
    "pdf": "Documents",
    "doc": "Documents",
    "docx": "Documents",
    "txt": "Documents",
    "rtf": "Documents",
    "odt": "Documents",
    "xls": "Documents",
    "xlsx": "Documents",
    "csv": "Documents",
    "ppt": "Documents",
    "pptx": "Documents",
    # Audio
    "mp3": "Audio",
    "wav": "Audio",
    "aac": "Audio",
    "flac": "Audio",
    "ogg": "Audio",
    # Video
    "mp4": "Video",
    "mov": "Video",
    "avi": "Video",
    "mkv": "Video",
    "wmv": "Video",
    # Archives
    "zip": "Archives",
    "tar": "Archives",
    "gz": "Archives",
    "bz2": "Archives",
    "7z": "Archives",
    "rar": "Archives",
    # Code
    "py": "Code",
    "js": "Code",
    "ts": "Code",
    "html": "Code",
    "css": "Code",
    "java": "Code",
    "cpp": "Code",
    "c": "Code",
    "go": "Code",
    "rs": "Code",
    # Executables
    "dmg": "Installers",
    "pkg": "Installers",
    "exe": "Installers",
    "msi": "Installers",
    "deb": "Installers",
    "rpm": "Installers",
    "appimage": "Installers",
}

# Files to ignore (partial matches)
IGNORE_PATTERNS = [
    ".crdownload",  # Chrome partial download
    ".part",        # Firefox partial download
    ".tmp",
    "~",
]
