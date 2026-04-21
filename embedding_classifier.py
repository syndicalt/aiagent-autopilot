import threading
from pathlib import Path
from typing import Optional
import numpy as np

# Lazy-loaded model state
_model = None
_category_embeddings: Optional[np.ndarray] = None
_category_names: Optional[list] = None
_lock = threading.Lock()

# Descriptions that capture the semantic space of each category
CATEGORY_DESCRIPTIONS = {
    "Images": "photos pictures screenshots jpg png gif images graphics",
    "Documents": "documents text pdf word doc txt essays articles reports",
    "Receipts": "receipts invoices bills purchases orders payments transactions",
    "Audio": "audio music mp3 wav sound podcasts recordings",
    "Video": "video movies mp4 mov clips recordings films",
    "Archives": "archives zip tar compressed backups packages",
    "Code": "code programming scripts source files software development",
    "Installers": "installers applications setup executables packages dmg",
    "Miscellaneous": "miscellaneous other unknown files assorted items",
}

def _ensure_model():
    """Lazily load the sentence-transformers model. Thread-safe."""
    global _model, _category_embeddings, _category_names
    if _model is not None:
        return

    with _lock:
        if _model is not None:
            return
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")

        # Pre-compute category embeddings
        _category_names = list(CATEGORY_DESCRIPTIONS.keys())
        texts = list(CATEGORY_DESCRIPTIONS.values())
        _category_embeddings = _model.encode(texts, convert_to_numpy=True)

def is_model_ready() -> bool:
    return _model is not None

def classify_text(text: str) -> str:
    """Classify a piece of text into the closest category using embeddings."""
    _ensure_model()
    if _model is None or _category_embeddings is None:
        return "Miscellaneous"

    text_embedding = _model.encode([text], convert_to_numpy=True)
    # Cosine similarity via dot product (vectors are normalized by the model)
    similarities = np.dot(_category_embeddings, text_embedding.T).flatten()
    best_idx = int(np.argmax(similarities))
    return _category_names[best_idx]

def classify_file(file_path: Path) -> str:
    """Create a rich text representation of a file and classify it."""
    name = file_path.stem.lower().replace("_", " ").replace("-", " ")
    ext = file_path.suffix.lstrip(".").lower()
    text = f"{name} {ext}"
    return classify_text(text)
