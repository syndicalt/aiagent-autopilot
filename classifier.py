from pathlib import Path
from config import CATEGORY_MAP, IGNORE_PATTERNS
import embedding_classifier
import rules_engine

def classify_file(file_path: Path) -> str:
    """Classify a file into a category using user rules first, then heuristics, then embeddings."""
    name = file_path.name.lower()
    suffix = file_path.suffix.lstrip(".").lower()

    # Skip incomplete downloads
    for pattern in IGNORE_PATTERNS:
        if pattern in name:
            return "Skip"

    # User-defined rules layer (highest priority)
    rule_category = rules_engine.match_file(file_path)
    if rule_category:
        return rule_category

    # Heuristic layer: fast, deterministic rules for known patterns
    if suffix == "pdf":
        if any(k in name for k in ["receipt", "invoice", "order", "purchase"]):
            return "Receipts"

    if suffix in CATEGORY_MAP:
        return CATEGORY_MAP[suffix]

    # Embedding layer: local AI for ambiguous / unknown files
    # Only if the model has been downloaded; otherwise fall through
    try:
        ai_category = embedding_classifier.classify_file(file_path)
        return ai_category
    except Exception:
        # Model not downloaded yet or other failure — fall back to Miscellaneous
        return "Miscellaneous"
