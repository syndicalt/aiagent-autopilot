# AI Agent Autopilot

A minimal Python prototype for an ambient file-organizing agent — now with a **Tauri menu-bar GUI**.

## What it does

Watches your `~/Downloads` folder and automatically moves new files into categorized subfolders inside `~/Downloads/Autopilot`.

- **Images** → `Autopilot/Images`
- **PDFs** → `Autopilot/Documents` (or `Autopilot/Receipts` if the filename looks like a receipt/invoice)
- **Audio/Video** → `Autopilot/Audio`, `Autopilot/Video`
- **Archives** → `Autopilot/Archives`
- **Code** → `Autopilot/Code`
- **Installers** → `Autopilot/Installers`
- Everything else → `Autopilot/Miscellaneous`

## Project structure

```
aiagent-autopilot/
├── main.py              # Python agent engine (file watcher)
├── undo.py              # CLI undo tool
├── classifier.py        # Heuristic file classifier
├── organizer.py         # File mover + SQLite logger
├── notifier.py          # Cross-platform desktop notifications
├── config.py            # Rules & mappings
├── requirements.txt     # Python deps
├── gui/                 # Tauri frontend (HTML/CSS/JS)
│   ├── index.html
│   ├── style.css
│   └── script.js
└── src-tauri/           # Tauri Rust backend
    ├── Cargo.toml
    ├── tauri.conf.json
    └── src/main.rs
```

## Run the Python agent (headless)

```bash
cd ~/Projects/Personal/aiagent-autopilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Undo (CLI)

Every move is reversible. Use the undo CLI to inspect the log and restore files:

```bash
# Show recent actions
python undo.py --list

# Undo the last move
python undo.py

# Undo the last 5 moves
python undo.py --last 5

# Preview what would be undone without touching anything
python undo.py --last 3 --dry-run
```

## Build & run the menu-bar GUI

The GUI is a **Tauri v2** app (Rust backend + web frontend) that lives in your system tray.

### Prerequisites

**macOS:** Nothing extra needed.  
**Windows:** Nothing extra needed.  
**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

### Build & run

```bash
cd ~/Projects/Personal/aiagent-autopilot/src-tauri

# Install Rust (if you haven't)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install Tauri CLI
cargo install tauri-cli --version "^2.0"

# Run in dev mode
cargo tauri dev

# Or build a release binary
cargo tauri build
```

### What the GUI gives you

- **System tray icon** — Click to show/hide the control window.
- **Start/Stop** — Toggle the Python agent without touching the terminal.
- **Live action feed** — See every file move as it happens.
- **One-click Undo** — Revert the last move from the GUI, no terminal needed.

## Features

- **Ambient:** Runs in the background. No chat window needed.
- **Trust-first:** Every move is logged to a local SQLite database (`~/Downloads/Autopilot/.autopilot.db`).
- **Safe:** Skips partial downloads (`.crdownload`, `.part`, etc.) and handles filename collisions.
- **Visual feedback:** Desktop notifications confirm each action.
- **Undo:** Full audit trail with one-command (or one-click) revert.
- **Menu-bar GUI:** Native-feeling tray app built with Tauri.

## Next steps

- Expand to other high-frequency folders (Desktop, Documents, Screenshots).
- Add LLM-based classification for ambiguous files.
- Package the GUI as a signed `.app` (macOS) or `.deb` / `.AppImage` (Linux) for distribution.
