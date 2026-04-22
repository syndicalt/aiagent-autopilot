# Autopilot Brain

Local embedding inference service for Autopilot.

Hosts the `all-MiniLM-L6-v2` sentence-transformers model and exposes
classification endpoints over HTTP. Designed to be consumed by Autopilot
and eventually other agents via a shared bus architecture.

## Why separate?

The embedding model + PyTorch runtime is ~2 GB. By running it as a
standalone service, the Autopilot agent binary stays lean (~15 MB) while
still being able to classify ambiguous files via HTTP.

## Install

```bash
cd brain
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn brain.main:app --host 127.0.0.1 --port 8765
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Returns `{ ready: bool, model: str }` |
| `/embed` | POST | Returns vector embedding for text |
| `/classify` | POST | Returns best category for text |
| `/classify-file` | POST | Returns category for a file path |

## Auto-start

Autopilot's `main.py` attempts to start the brain automatically if it's
not already running on port 8765. No manual step required in dev mode.

## Future

This will evolve into `autopilot-agent-bus` — a standalone repo with
multi-app support, plugin architecture, and optional cloud LLM fallback.
