"""
Autopilot Brain — Local embedding inference service.

A lightweight HTTP server that hosts the all-MiniLM-L6-v2 embedding model
and exposes classification endpoints. Designed to be consumed by Autopilot
and eventually other agents via the autopilot-agent-bus architecture.

Usage:
    python -m uvicorn brain.main:app --host 127.0.0.1 --port 8765

Or from the project root:
    python brain/main.py
"""

import threading
import json
from pathlib import Path
from typing import List
import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Autopilot Brain", version="0.1.0")

# Lazy-loaded model state
_model = None
_category_embeddings: np.ndarray | None = None
_category_names: List[str] | None = None
_lock = threading.Lock()

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

        _category_names = list(CATEGORY_DESCRIPTIONS.keys())
        texts = list(CATEGORY_DESCRIPTIONS.values())
        _category_embeddings = _model.encode(texts, convert_to_numpy=True)


def _classify_text(text: str) -> str:
    """Classify a piece of text into the closest category using embeddings."""
    _ensure_model()
    if _model is None or _category_embeddings is None:
        return "Miscellaneous"

    text_embedding = _model.encode([text], convert_to_numpy=True)
    similarities = np.dot(_category_embeddings, text_embedding.T).flatten()
    best_idx = int(np.argmax(similarities))
    return _category_names[best_idx]


class EmbedRequest(BaseModel):
    text: str


class ClassifyRequest(BaseModel):
    text: str
    categories: List[str] | None = None


class StatusResponse(BaseModel):
    ready: bool
    model: str
    cloud_ready: bool = False


@app.get("/status", response_model=StatusResponse)
def status():
    return StatusResponse(
        ready=_model is not None,
        model="all-MiniLM-L6-v2",
        cloud_ready=False,  # Internal brain has no cloud jet
    )


@app.post("/embed")
def embed(req: EmbedRequest):
    _ensure_model()
    vector = _model.encode([req.text], convert_to_numpy=True)
    return {"vector": vector.tolist()[0]}


@app.post("/classify")
def classify(req: ClassifyRequest):
    category = _classify_text(req.text)
    return {"category": category, "confidence": None}


@app.post("/classify-file")
def classify_file(path: str):
    from pathlib import Path as PyPath
    file_path = PyPath(path)
    name = file_path.stem.lower().replace("_", " ").replace("-", " ")
    ext = file_path.suffix.lstrip(".").lower()
    text = f"{name} {ext}"
    category = _classify_text(text)
    return {"category": category, "input": text}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
