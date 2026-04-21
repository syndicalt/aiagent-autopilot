# Autopilot

An **ambient file-organizing agent** with a Tauri menu-bar GUI. Watches `~/Downloads`, automatically sorts files using a hybrid heuristic + local AI classifier, and provides a visual command center with live action feed, visual rules engine, and one-click undo.

> Built for the a16z "GUIs for Agents" thesis. Local-first, privacy-first, zero marginal cost.

![Status](https://img.shields.io/badge/status-alpha-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

---

## What it does

Drop a file into `~/Downloads`. Autopilot moves it to the right folder inside `~/Downloads/Autopilot` within seconds.

**Default categories:**
- **Images** → `Autopilot/Images` (jpg, png, gif, webp, svg)
- **Documents** → `Autopilot/Documents` (pdf, docx, txt, csv, xlsx, pptx)
- **Receipts** → `Autopilot/Receipts` (PDFs with "invoice", "receipt", "order" in the name)
- **Audio** → `Autopilot/Audio` (mp3, wav, flac, ogg)
- **Video** → `Autopilot/Video` (mp4, mov, mkv, avi)
- **Archives** → `Autopilot/Archives` (zip, tar, gz, 7z, rar)
- **Code** → `Autopilot/Code` (py, js, ts, rs, go, java, cpp)
- **Installers** → `Autopilot/Installers` (dmg, pkg, deb, rpm, AppImage)
- **Miscellaneous** → `Autopilot/Miscellaneous` (everything else)

### Sorting pipeline (priority order)

1. **User-defined rules** — Visual rule builder in the GUI. Highest priority.
2. **Heuristics** — Fast extension + filename keyword matching.
3. **Local AI embeddings** — `all-MiniLM-L6-v2` model for ambiguous files. Downloads once (~80MB), runs entirely offline.

---

## Features

| Feature | Description |
|---------|-------------|
| **Ambient** | Runs in the system tray. No chat window needed. |
| **Local AI** | Embedding classifier using `sentence-transformers`. No API keys. |
| **Visual Rules Engine** | Build custom sort rules from the GUI — no code required. |
| **Live Action Feed** | See every file move in real time with timestamps. |
| **One-Click Undo** | Full SQLite audit trail. Revert any move from the GUI or CLI. |
| **Notification Mute** | Toggle desktop notifications from the tray or GUI. |
| **Cross-Platform** | Native `.deb`, `.AppImage` (Linux), `.dmg`, `.app` (macOS), `.msi` (Windows). |

---

## Screenshots

*(Add screenshots of the GUI here)*

---

## Installation

### Linux

**`.deb` (recommended for Ubuntu/Debian):**

```bash
sudo dpkg -i Autopilot_0.1.0_amd64.deb
```

Autopilot appears in your applications menu and starts automatically in the system tray.

**`.AppImage` (portable, works on most distros):**

```bash
chmod +x Autopilot_0.1.0_amd64.AppImage
./Autopilot_0.1.0_amd64.AppImage
```

### macOS

**`.dmg`:**

1. Open the `.dmg`
2. Drag **Autopilot** into **Applications**
3. Launch from Launchpad or Finder

> **First launch:** The app is ad-hoc signed. If Gatekeeper blocks it, right-click the app → **Open** → confirm.

### Windows

**`.msi`:**

1. Double-click the `.msi`
2. Follow the installer prompts
3. Launch from the Start Menu

> **First launch:** Windows SmartScreen may warn since the app is unsigned. Click **More info** → **Run anyway**.

---

## Quick Start

### Run from source (developers)

**Python agent (headless):**

```bash
cd ~/Projects/Personal/aiagent-autopilot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

**GUI dev mode (hot reload):**

```bash
cd src-tauri
cargo tauri dev
```

**Build release packages:**

```bash
make build
```

See [BUILD.md](BUILD.md) for detailed platform-specific build instructions.

---

## Project Structure

```
aiagent-autopilot/
├── main.py                    # Agent entry point (watchdog + dedup)
├── classifier.py              # Three-tier classifier (rules → heuristics → AI)
├── rules_engine.py            # User-defined sort rules engine
├── embedding_classifier.py    # Local AI model (all-MiniLM-L6-v2)
├── organizer.py               # File mover + SQLite action logger
├── notifier.py                # Cross-platform desktop notifications
├── settings.py                # JSON settings persistence
├── undo.py                    # CLI undo tool
├── config.py                  # Paths, extension → category mappings
├── requirements.txt           # Python dependencies
├── gui/                       # Tauri frontend
│   ├── index.html
│   ├── style.css
│   └── script.js
├── src-tauri/                 # Tauri Rust backend
│   ├── src/main.rs            # Commands, tray setup, process mgmt
│   ├── Cargo.toml
│   └── tauri.conf.json
├── BUILD.md                   # Build instructions
├── Makefile                   # make build / make dev / make clean
└── README.md
```

---

## Undo

Every move is logged to `~/Downloads/Autopilot/.autopilot.db` and is reversible.

**CLI:**
```bash
python undo.py --list          # Show recent actions
python undo.py                 # Undo last move
python undo.py --last 5        # Undo last 5 moves
python undo.py --dry-run       # Preview without touching files
```

**GUI:** Click **Undo Last** in the Recent Actions panel.

---

## Rules Engine

Build custom sort rules from the GUI without writing code.

A rule consists of:
- **Name** — For your reference
- **Conditions** — All must match (AND logic). Fields: `filename`, `extension`, `path`, `mime_type`, `size`. Operators: `equals`, `contains`, `starts_with`, `ends_with`, `matches_regex`, `greater_than`, `less_than`.
- **Action** — `Move to <category>` or `Skip`

Rules are evaluated in order. The first matching rule wins.

**Test before saving:** Enter a filename in the test field and click **Test** to see which rules match.

---

## Smart Sort (Local AI)

The embedding classifier downloads `all-MiniLM-L6-v2` (~80MB) on first run. It classifies ambiguous files by comparing their filename embeddings against pre-computed category embeddings. Completely offline — no API calls, no keys.

Status badge in the GUI shows:
- **"Setting up..."** — Model not yet downloaded
- **"Local"** — Model ready, running offline

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **Tauri v2** over Electron | Smaller bundle, native tray, Rust safety |
| **Local embeddings** over cloud LLM | Zero marginal cost, zero latency, privacy |
| **SQLite audit log** | Simple, portable, reversible |
| **Rules as JSON** | Human-readable, easy to back up or version |
| **Hardcoded project path** | Dev convenience; will bundle Python for distribution |

---

## Known Limitations

- **Python path dependency:** The bundled app currently expects the repo at `~/Projects/Personal/aiagent-autopilot` with a working `.venv`. Standalone Python embedding is planned.
- **Single watch folder:** Only `~/Downloads` is watched. Desktop/Documents expansion is on the roadmap.
- **macOS signing:** Bundles are ad-hoc signed. Gatekeeper will warn on first launch — right-click → Open to allow.
- **Windows signing:** `.msi` is unsigned. SmartScreen will warn on first launch — click **More info** → **Run anyway**.

---

## Roadmap

- [ ] Bundle Python interpreter as a Tauri resource (fully standalone)
- [ ] Watch `~/Desktop` and `~/Documents`
- [ ] Drag-and-drop rule creation from Recent Actions
- [x] Windows support (`.msi`)
- [ ] Cloud LLM fallback tier for truly ambiguous files (optional, opt-in)

---

## License

MIT
