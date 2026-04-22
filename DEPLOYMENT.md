# Deployment Strategy

## Goal

Zero-setup installation for end users. No Python, no venv, no `pip install`.

## The Problem

Python ML dependencies (PyTorch, sentence-transformers) are **~2 GB**. Bundling them into every app creates an unacceptable install experience.

## The Solution: Two Products

| Product | Size | Contents | Required? |
|---------|------|----------|-----------|
| **Autopilot** | ~100 MB | File watcher, rules engine, heuristics, SQLite, GUI | Yes |
| **Autopilot Bus** | ~2 GB | Embedding model + optional LLM, HTTP API, plugin system | No |

The Bus is the canonical AI service. It subsumes the old "brain" concept — the brain was always just the bus without the plugin system and multi-app support.

## Architecture

```
Autopilot Agent (lean bundle)
    ├── Rules Engine
    ├── Heuristics
    └── Optional: HTTP client → localhost:8765
            ↓
    Autopilot Bus (optional install)
        ├── Embedding model (all-MiniLM-L6-v2)
        ├── Plugin registry
        ├── Cloud jet (OpenAI/Claude)
        └── HTTP API for any app
```

**Hub-and-spoke pattern:**
- **Hub (Bus):** Runs the models, handles plugin registry, optional cloud fallback
- **Spokes (Apps):** HTTP clients that send text and receive classifications
- **Standalone mode:** Apps work without the bus using rules + heuristics

## Current State

- [x] `autopilot` — Lean agent bundle works via PyInstaller (no torch)
- [ ] `autopilot-bus` — Separate repo, requires source venv for now

## Deployment Targets

### Phase 1: Standalone Agent (DONE)
The Autopilot GUI + agent ships as `.deb`, `.AppImage`, `.dmg`, `.msi`. No Python required. Ambiguous files fall back to "Miscellaneous".

### Phase 2: Optional Bus Plugin
Package `autopilot-agent-bus` via PyInstaller as `autopilot-bus` — a single executable that drops into `/opt/autopilot-bus/` or `~/Library/Application Support/Autopilot/`. Apps auto-discover it at runtime on `localhost:8765`.

### Phase 3: ONNX Runtime (long-term)
Convert `all-MiniLM-L6-v2` from PyTorch to ONNX. ONNX Runtime is **~50 MB** vs PyTorch's **1.5 GB**. This makes the bus a reasonable single-package install (~150 MB total).

## Technical Approach

### For Autopilot Agent
Already solved via `scripts/build-agent.py` + PyInstaller. The agent bundle includes:
- Python runtime (from PyInstaller bootloader)
- `watchdog`, `sqlite3`, standard library
- NO torch, NO sentence-transformers

### For Autopilot Bus
PyInstaller spec that packages the bus repo. Build spec:
```python
# bus.spec
a = Analysis(
    ['bus/main.py'],
    hiddenimports=[
        'sentence_transformers',
        'torch',
        'transformers',
        'tokenizers',
        'huggingface_hub',
        'fastapi',
        'uvicorn',
    ],
)
```

Output: `autopilot-bus` (single executable, ~2 GB)

### Discovery Protocol
The agent probes for AI capabilities in this order:
1. `http://127.0.0.1:8765/status` → Bus running? Use it.
2. `~/.local/share/autopilot-bus/autopilot-bus --status` → Bus binary installed? Launch it.
3. Neither → Rules + heuristics only.

### Platform Packages

**Linux (.deb):**
```
autopilot_*.deb          → agent only
autopilot-bus_*.deb      → optional, depends on autopilot
```

**macOS (.dmg):**
Single `.dmg` with optional "Install Autopilot Bus" checkbox.

**Windows (.msi):**
Feature tree: Agent (required), Bus (optional).

## Size Comparison

| Approach | Agent | +Bus | Install Experience |
|----------|-------|------|-------------------|
| Current (source + venv) | ~15 MB | +2 GB | Clone repo, create venv, pip install |
| PyInstaller bundles | ~100 MB | +2 GB | Download .deb/.msi, double-click |
| ONNX Runtime (future) | ~100 MB | +50 MB | Download .deb/.msi, double-click |

## Decision Log

**Why not bundle bus into the agent?**
Makes the base install 2 GB. Most users don't need AI for PDFs and images. Rules + heuristics cover 90% of files.

**Why not skip PyInstaller and use system Python?**
System Python versions vary, packages conflict, and users can't be expected to `sudo apt install python3-pytorch`.

**Why HTTP instead of shared library / gRPC?**
HTTP is debuggable with `curl`, works from any language, no protobuf codegen, and the overhead of localhost HTTP is negligible compared to embedding inference time.

## Next Steps

1. [ ] Create `bus.spec` for PyInstaller bus build
2. [ ] Create `scripts/build-bus.py` similar to `build-agent.py`
3. [ ] Add bus discovery to agent (`~/.local/share/autopilot-bus/`)
4. [ ] Package bus as `.deb` / `.msi` / `.dmg`
5. [ ] Explore ONNX conversion for size reduction
