# Deployment Strategy

## Goal

Zero-setup installation for end users. No Python, no venv, no `pip install`.

## The Problem

Python ML dependencies (PyTorch, sentence-transformers) are **~2 GB**. Bundling them into every app creates an unacceptable install experience.

## The Solution: Three Artifacts

| Artifact | Size | Contents | When to Install |
|----------|------|----------|-----------------|
| **`autopilot`** | ~100 MB | File watcher, rules engine, heuristics, SQLite, GUI | Everyone |
| **`autopilot-brain`** | ~2 GB | Embedding model (all-MiniLM-L6-v2) + PyTorch | Users who want AI classification |
| **`autopilot-bus`** | ~2 GB | Multi-app inference hub (embeddings + optional LLM) | Power users / multi-app setups |

## Current State

- [x] `autopilot` — Lean agent bundle works via PyInstaller (no torch)
- [ ] `autopilot-brain` — Internal brain service exists but requires source venv
- [ ] `autopilot-bus` — Separate repo exists but requires source venv

## Deployment Targets

### Phase 1: Standalone Agent (DONE)
The Autopilot GUI + agent ships as `.deb`, `.AppImage`, `.dmg`, `.msi`. No Python required. Ambiguous files fall back to "Miscellaneous".

### Phase 2: Optional Brain Plugin
Package `brain/main.py` via PyInstaller as `autopilot-brain` — a single executable that drops into `/opt/autopilot-brain/` or `~/Library/Application Support/Autopilot/`. The agent auto-discovers it at runtime.

### Phase 3: Optional Bus Plugin
Package `autopilot-agent-bus` via PyInstaller as `autopilot-bus` — same pattern as the brain. For users who want multi-app inference.

### Phase 4: ONNX Runtime (long-term)
Convert `all-MiniLM-L6-v2` from PyTorch to ONNX. ONNX Runtime is **~50 MB** vs PyTorch's **1.5 GB**. This makes the brain/bus a reasonable single-package install (~150 MB total).

## Technical Approach

### For Autopilot Agent
Already solved via `scripts/build-agent.py` + PyInstaller. The agent bundle includes:
- Python runtime (from PyInstaller bootloader)
- `watchdog`, `sqlite3`, standard library
- NO torch, NO sentence-transformers

### For Brain / Bus
Same PyInstaller approach, but includes torch. Build spec:
```python
# brain.spec / bus.spec
a = Analysis(
    ['brain/main.py'],  # or bus/main.py
    hiddenimports=[
        'sentence_transformers',
        'torch',
        'transformers',
        'tokenizers',
        'huggingface_hub',
    ],
)
```

Output: `autopilot-brain` (single executable, ~2 GB)

### Discovery Protocol
The agent probes for AI capabilities in this order:
1. `http://127.0.0.1:8765/status` → Bus running? Use it.
2. `~/.local/share/autopilot-brain/autopilot-brain --status` → Brain binary installed? Launch it.
3. Neither → Rules + heuristics only.

### Platform Packages

**Linux (.deb):**
```
autopilot_*.deb          → agent only
autopilot-brain_*.deb    → optional, depends on autopilot
autopilot-bus_*.deb      → optional, conflicts with autopilot-brain
```

**macOS (.dmg):**
Single `.dmg` with optional "Install Brain" checkbox.

**Windows (.msi):**
Feature tree: Agent (required), Brain (optional), Bus (optional, conflicts with Brain).

## Venv-Free Dev Mode (Future)

For developers who also hate venvs:
```bash
# Using uv (modern Python package manager)
uv run --with watchdog,sentence-transformers,torch python main.py
```
`uv` manages dependencies in a global cache, no venv activation needed.

## Size Comparison

| Approach | Agent | +Brain | Install Experience |
|----------|-------|--------|-------------------|
| Current (source + venv) | ~15 MB | +2 GB | Clone repo, create venv, pip install |
| PyInstaller bundles | ~100 MB | +2 GB | Download .deb/.msi, double-click |
| ONNX Runtime (future) | ~100 MB | +50 MB | Download .deb/.msi, double-click |

## Decision Log

**Why not bundle brain into the agent?**
Makes the base install 2 GB. Most users don't need AI for PDFs and images. Rules + heuristics cover 90% of files.

**Why not skip PyInstaller and use system Python?**
System Python versions vary, packages conflict, and users can't be expected to `sudo apt install python3-pytorch`.

**Why HTTP instead of shared library / gRPC?**
HTTP is debuggable with `curl`, works from any language, no protobuf codegen, and the overhead of localhost HTTP is negligible compared to embedding inference time.

## Next Steps

1. [ ] Create `brain.spec` for PyInstaller brain build
2. [ ] Create `scripts/build-brain.py` similar to `build-agent.py`
3. [ ] Add brain discovery to agent (`~/.local/share/autopilot-brain/`)
4. [ ] Package brain as `.deb` / `.msi` / `.dmg`
5. [ ] Explore ONNX conversion for size reduction
