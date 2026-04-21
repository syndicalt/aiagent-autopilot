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
- Python 3.10+ with PyInstaller:
  ```bash
  pip install pyinstaller
  ```
  > PyInstaller is used to freeze the agent into a standalone binary bundled with the app.

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev libfuse2 dpkg fakeroot pkg-config
```

### macOS
```bash
xcode-select --install
```

### Windows
- Install [Rust](https://rustup.rs/)
- Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/) with the **Desktop development with C++** workload
- Ensure `python` is in your PATH

---

## Build Outputs

### Linux
- `.deb` — Install with `sudo dpkg -i autopilot_*.deb`
- `.AppImage` — Mark executable and double-click: `chmod +x autopilot_*.AppImage`

### macOS
- `.dmg` — Mount and drag Autopilot to Applications
- `.app` — Direct app bundle (can run unsigned with Right-click → Open)

**Note:** macOS builds are ad-hoc signed by default. Gatekeeper may warn on first launch — right-click the app and select **Open** to allow it.

### Windows
- `.msi` — Double-click to install. Autopilot appears in Start Menu and can be uninstalled from Settings → Apps.
- `.exe` — Portable binary (available alongside the `.msi` in the bundle directory)

**Note:** Windows builds are unsigned. SmartScreen may warn on first launch — click **More info** → **Run anyway**.

---

## Dev Mode

```bash
cd src-tauri
cargo tauri dev
```

Hot-reloads the frontend and restarts the Rust backend on change.

In dev mode, the Rust backend spawns the agent directly from your local repo's Python virtualenv (`.venv/bin/python`). No PyInstaller build is required.

---

## How Standalone Bundling Works

During `cargo tauri build`, Tauri runs `scripts/build-agent.py` **before** compiling the Rust backend. This script:

1. Runs PyInstaller on `agent.spec` to freeze the Python agent + all dependencies into a single binary (`autopilot-agent`)
2. Copies the binary into `src-tauri/resources/`
3. Tauri bundles the binary as a resource in the final package

At runtime, the Rust backend looks for the bundled sidecar next to the executable. If found, it spawns the sidecar directly. If not found (dev mode), it falls back to the system Python interpreter.

**Result:** Users install the `.deb`/`.msi`/`.dmg` and it just works — no repo clone, no venv, no `pip install`.

---

## Build Size

The standalone agent binary includes the full Python runtime + torch + sentence-transformers + all dependencies. Expect:

- Agent binary alone: **400–600 MB**
- Full Tauri bundle (app + agent): **500–700 MB**

The size is dominated by PyTorch. Future work may explore ONNX Runtime or quantization to shrink this.

---

## Manual Agent Build (optional)

If you want to build the agent binary separately:

```bash
python3 scripts/build-agent.py
```

Output: `src-tauri/resources/autopilot-agent`
