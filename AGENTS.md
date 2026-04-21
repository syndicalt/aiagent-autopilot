# Agent Guide: Autopilot

This file contains context for coding agents working on the Autopilot project.

---

## Philosophy

- **Local-first, privacy-first, zero marginal cost.**
- **Simplicity first.** Surgical changes only. Goal-driven with verifiable success criteria.
- **Minimal intrusions.** Follow existing patterns. Don't over-engineer.

---

## Architecture

### Data Flow

```
~/Downloads
    ↓
watchdog (main.py)
    ↓
classifier.py
    ├── rules_engine.py    (highest priority — user-defined)
    ├── config.CATEGORY_MAP (heuristics — extension/filename)
    └── embedding_classifier.py (local AI — all-MiniLM-L6-v2)
    ↓
organizer.py
    ├── move_file()        → filesystem
    └── log_action()       → SQLite (~/.autopilot.db)
    ↓
notifier.py              → desktop notification (unless muted)
```

### Three-Tier Classification Priority

1. **Rules** (`rules_engine.py`) — JSON-backed user-defined conditions. First match wins.
2. **Heuristics** (`config.py` + `classifier.py`) — Fast extension/filename mapping.
3. **Embeddings** (`embedding_classifier.py`) — Offline AI for ambiguous files.

**Important:** When modifying the pipeline, maintain this priority order. Rules must always override heuristics and AI.

---

## File Responsibilities

| File | Role | Never Do |
|------|------|----------|
| `main.py` | Entry point, watchdog, dedup lock | Don't put classification logic here |
| `classifier.py` | Orchestrates the 3-tier pipeline | Don't hardcode categories here |
| `rules_engine.py` | User rule matching engine | Don't import embedding_classifier |
| `embedding_classifier.py` | Lazy-loaded local AI | Don't call from rules_engine |
| `organizer.py` | File moves + SQLite logging | Don't classify here |
| `notifier.py` | Desktop notifications | Don't call directly from GUI |
| `settings.py` | JSON settings persistence | Don't add complex schemas |
| `undo.py` | CLI undo tool | Don't depend on GUI |
| `config.py` | Paths + CATEGORY_MAP | Don't add runtime logic |
| `src-tauri/src/main.rs` | Tauri commands + tray | Don't duplicate Python logic |

---

## Coding Conventions

### Python
- Type hints on public functions.
- `pathlib.Path` for all filesystem operations.
- Use `try/except` around filesystem calls (files may disappear during processing).
- Thread-safe: `main.py` uses `threading.Lock()` for the dedup set. `embedding_classifier.py` uses its own `_lock` for lazy model loading.

### Rust (Tauri)
- Use `tokio::sync::Mutex` for state shared across await points (not `std::sync::Mutex`).
- Always capture Python stderr in `Command::output()` calls — swallowing errors makes debugging impossible.
- Use `try_wait()` to detect externally-killed agent processes in `get_agent_status`.
- Tray menu updates must be atomic: build the full `Menu` first, then `set_menu()`.

### Frontend (HTML/CSS/JS)
- CSS custom properties (`:root`) for the design system. No magic numbers.
- All dynamically created elements must use the same CSS classes as static ones.
- `escapeHtml()` before injecting user data (filenames, rule names) into the DOM.
- Use `crypto.randomUUID()` for client-side rule IDs.

---

## Key Design Decisions & Gotchas

### Tauri v2 Tray Events
`TrayIconEvent::DoubleClick` is a **struct variant** (`DoubleClick { .. }`), not a unit variant. Match with `if let TrayIconEvent::DoubleClick { .. } = event`.

### Tauri v2 Image API
`Image::from_path` does not exist. Use `Image::new_owned(rgba_bytes, width, height)`.

### watchdog Dedup
`watchdog` fires multiple `on_created` events for the same file. A thread-safe `_processing` set (`_processing_lock`) prevents duplicate handling. Always wrap handler logic in `_mark_processing` / `_unmark_processing`.

### Extension Normalization
Users type `.pdf` but the engine stores `pdf` (dot stripped by `Path.suffix`). The rules engine normalizes values with `.lstrip(".")` before comparison. The frontend also strips leading dots on save.

### Python Module Caching
The running agent caches imported modules. If you fix a bug in `rules_engine.py` or `classifier.py`, you **must restart the agent** for changes to take effect.

### Notification Mute
- Stored in `~/Downloads/Autopilot/.settings.json`
- Read by Python (`settings.py`) and Rust (`main.rs`)
- Tray mute toggle must refresh the full menu to update the label

---

## Build Commands

```bash
# Dev mode (hot reload)
make dev

# Release build (all platforms)
make build

# Clean
make clean
```

### Platform-Specific Dependencies

**Linux (Ubuntu/Debian):**
```bash
sudo apt install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev libfuse2 dpkg fakeroot pkg-config
```

**macOS:**
```bash
xcode-select --install
```

---

## Bundle Outputs

`make build` produces:
- `src-tauri/target/release/bundle/deb/*.deb`
- `src-tauri/target/release/bundle/appimage/*.AppImage`
- `src-tauri/target/release/bundle/dmg/*.dmg`
- `src-tauri/target/release/bundle/macos/*.app`

---

## Testing Checklist (Manual)

Before committing UI changes:
- [ ] Start/Stop agent toggles correctly
- [ ] Recent Actions list populates and refreshes
- [ ] Undo Last reverts a move
- [ ] Mute switch toggles notifications
- [ ] Add Rule → Save Rules → new file triggers rule
- [ ] Test filename shows correct match indicators
- [ ] Tray double-click opens window
- [ ] Close button hides to tray (not quits)
- [ ] Logs panel shows agent stderr

---

## Relevant Paths

| Path | Purpose |
|------|---------|
| `~/Downloads/Autopilot/` | Organized files root + hidden data |
| `~/Downloads/Autopilot/.autopilot.db` | SQLite action log |
| `~/Downloads/Autopilot/.settings.json` | Notification mute state |
| `~/Downloads/Autopilot/.rules.json` | User-defined sort rules |
| `~/Downloads/Autopilot/.agent.log` | Agent stderr |
| `~/Downloads/Autopilot/.agent.pid` | Running agent PID |
| `~/.cache/huggingface/` | Downloaded embedding model |

---

## Commit Message Style

- `feat:` — New feature
- `fix:` — Bug fix
- `polish:` — UI/UX refinement
- `refactor:` — Code change with no behavior change
- `docs:` — Documentation only

Example: `feat: add visual rules engine with live test preview`
