from pathlib import Path
from config import CATEGORY_MAP, IGNORE_PATTERNS

def classify_file(file_path: Path) -> str:
    """Classify a file into a category based on extension and name heuristics."""
    name = file_path.name.lower()
    suffix = file_path.suffix.lstrip(".").lower()

    # Skip incomplete downloads
    for pattern in IGNORE_PATTERNS:
        if pattern in name:
            return "Skip"

    # Heuristic: receipts / invoices
    if suffix == "pdf":
        if any(k in name for k in ["receipt", "invoice", "order", "purchase"]):
            return "Receipts"

    # Default mapping
    if suffix in CATEGORY_MAP:
        return CATEGORY_MAP[suffix]

    return "Miscellaneous"
