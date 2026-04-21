# Building Autopilot

## Quick Start

```bash
cd src-tauri
cargo tauri build
```

Packages are written to `src-tauri/target/release/bundle/`.

---

## Prerequisites

### All Platforms
- [Rust](https://rustup.rs/) (1.77+)
- Tauri CLI: `cargo install tauri-cli --version "^2.0"`

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev libfuse2 dpkg fakeroot pkg-config
```

### macOS
```bash
xcode-select --install
```

---

## Build Outputs

### Linux
- `.deb` — Install with `sudo dpkg -i autopilot_*.deb`
- `.AppImage` — Mark executable and double-click: `chmod +x autopilot_*.AppImage`

### macOS
- `.dmg` — Mount and drag Autopilot to Applications
- `.app` — Direct app bundle (can run unsigned with Right-click → Open)

**Note:** macOS builds are ad-hoc signed by default. Gatekeeper may warn on first launch — right-click the app and select **Open** to allow it.

---

## Dev Mode

```bash
cd src-tauri
cargo tauri dev
```

Hot-reloads the frontend and restarts the Rust backend on change.

---

## Cross-Platform Notes

Autopilot currently reads the Python agent from a hardcoded path:
```
~/Projects/Personal/aiagent-autopilot/.venv/bin/python
```

For the bundle to work, you must:
1. Have the repo cloned at that path
2. Have the Python virtualenv created and dependencies installed:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

Future releases will bundle Python as a resource for fully standalone distribution.
