#!/bin/bash
set -e

echo "🛠️  Setting up AI Agent Autopilot..."

# Create project directory
mkdir -p ~/Projects/Personal/aiagent-autopilot
mkdir -p ~/Projects/Personal/aiagent-autopilot/src-tauri/src
mkdir -p ~/Projects/Personal/aiagent-autopilot/src-tauri/icons
mkdir -p ~/Projects/Personal/aiagent-autopilot/gui

cd ~/Projects/Personal/aiagent-autopilot

# Python virtual environment
echo "Creating Python venv..."
python3 -m venv .venv
source .venv/bin/activate

# requirements.txt
cat > requirements.txt << 'PYEOF'
watchdog
PYEOF

pip install -r requirements.txt

# config.py
cat > config.py << 'PYEOF'
import os
from pathlib import Path

DOWNLOADS_DIR = Path.home() / "Downloads"
ORGANIZED_ROOT = DOWNLOADS_DIR / "Autopilot"

CATEGORY_MAP = {
    "jpg": "Images", "jpeg": "Images", "png": "Images", "gif": "Images",
    "bmp": "Images", "svg": "Images", "webp": "Images",
    "pdf": "Documents", "doc": "Documents", "docx": "Documents", "txt": "Documents",
    "rtf": "Documents", "odt": "Documents", "xls": "Documents", "xlsx": "Documents",
    "csv": "Documents", "ppt": "Documents", "pptx": "Documents",
    "mp3": "Audio", "wav": "Audio", "aac": "Audio", "flac": "Audio", "ogg": "Audio",
    "mp4": "Video", "mov": "Video", "avi": "Video", "mkv": "Video", "wmv": "Video",
    "zip": "Archives", "tar": "Archives", "gz": "Archives", "bz2": "Archives",
    "7z": "Archives", "rar": "Archives",
    "py": "Code", "js": "Code", "ts": "Code", "html": "Code", "css": "Code",
    "java": "Code", "cpp": "Code", "c": "Code", "go": "Code", "rs": "Code",
    "dmg": "Installers", "pkg": "Installers", "exe": "Installers", "msi": "Installers",
    "deb": "Installers", "rpm": "Installers", "appimage": "Installers",
}

IGNORE_PATTERNS = [".crdownload", ".part", ".tmp", "~"]
PYEOF

# classifier.py
cat > classifier.py << 'PYEOF'
from pathlib import Path
from config import CATEGORY_MAP, IGNORE_PATTERNS

def classify_file(file_path: Path) -> str:
    name = file_path.name.lower()
    suffix = file_path.suffix.lstrip(".").lower()

    for pattern in IGNORE_PATTERNS:
        if pattern in name:
            return "Skip"

    if suffix == "pdf":
        if any(k in name for k in ["receipt", "invoice", "order", "purchase"]):
            return "Receipts"

    if suffix in CATEGORY_MAP:
        return CATEGORY_MAP[suffix]

    return "Miscellaneous"
PYEOF

# organizer.py
cat > organizer.py << 'PYEOF'
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from config import ORGANIZED_ROOT

def ensure_db() -> sqlite3.Connection:
    db_path = ORGANIZED_ROOT / ".autopilot.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            original_path TEXT,
            new_path TEXT,
            category TEXT,
            action TEXT
        )
    """)
    conn.commit()
    return conn

def move_file(file_path: Path, category: str) -> Path:
    dest_dir = ORGANIZED_ROOT / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / file_path.name
    counter = 1
    stem = file_path.stem
    suffix = file_path.suffix
    while dest_path.exists():
        dest_path = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    shutil.move(str(file_path), str(dest_path))
    return dest_path

def log_action(conn: sqlite3.Connection, original: Path, new: Path, category: str):
    conn.execute(
        "INSERT INTO actions (timestamp, original_path, new_path, category, action) VALUES (?, ?, ?, ?, ?)",
        (datetime.utcnow().isoformat(), str(original), str(new), category, "move"),
    )
    conn.commit()

def organize(file_path: Path, category: str) -> Path:
    conn = ensure_db()
    try:
        new_path = move_file(file_path, category)
        log_action(conn, file_path, new_path, category)
        return new_path
    finally:
        conn.close()

def get_recent_actions(limit: int = 20):
    conn = ensure_db()
    cursor = conn.execute(
        "SELECT timestamp, original_path, new_path, category FROM actions ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
PYEOF

# notifier.py
cat > notifier.py << 'PYEOF'
import platform
import subprocess

def notify(title: str, message: str):
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], check=False)
        elif system == "Linux":
            subprocess.run(["notify-send", title, message], check=False)
        else:
            print(f"[{title}] {message}")
    except Exception:
        print(f"[{title}] {message}")
PYEOF

# main.py
cat > main.py << 'PYEOF'
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import DOWNLOADS_DIR
from classifier import classify_file
from organizer import organize
from notifier import notify

class DownloadsHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)
        time.sleep(0.5)
        if not file_path.exists():
            return
        category = classify_file(file_path)
        if category == "Skip":
            return
        try:
            new_path = organize(file_path, category)
            notify("Autopilot", f"Moved '{file_path.name}' → {category}")
            print(f"[MOVE] {file_path} -> {new_path}")
        except Exception as e:
            notify("Autopilot Error", f"Could not move {file_path.name}: {e}")
            print(f"[ERROR] {e}")

def main():
    print(f"Watching {DOWNLOADS_DIR} for new files...")
    print("Press Ctrl+C to stop.\n")
    observer = Observer()
    observer.schedule(DownloadsHandler(), str(DOWNLOADS_DIR), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
PYEOF

# undo.py
cat > undo.py << 'PYEOF'
import argparse
import shutil
import sqlite3
from pathlib import Path
from organizer import ensure_db, ORGANIZED_ROOT

def list_actions(limit: int = 10):
    conn = ensure_db()
    rows = conn.execute(
        """SELECT id, timestamp, category, original_path, new_path, action
           FROM actions ORDER BY id DESC LIMIT ?""", (limit,),
    ).fetchall()
    conn.close()
    if not rows:
        print("No actions found.")
        return []
    print(f"{'ID':>4} | {'Time':19} | {'Category':12} | {'Action':6} | Original → New")
    print("-" * 120)
    for row in rows:
        id_, ts, cat, orig, new, act = row
        print(f"{id_:>4} | {ts[:19]} | {cat:12} | {act:6} | {Path(orig).name} → {Path(new).name}")
    return rows

def undo_action(action_id: int) -> bool:
    conn = ensure_db()
    row = conn.execute(
        "SELECT original_path, new_path FROM actions WHERE id = ?", (action_id,),
    ).fetchone()
    if not row:
        print(f"Action {action_id} not found.")
        conn.close()
        return False
    original_path = Path(row[0])
    new_path = Path(row[1])
    if not new_path.exists():
        print(f"Cannot undo {action_id}: file no longer exists at {new_path}")
        conn.close()
        return False
    original_path.parent.mkdir(parents=True, exist_ok=True)
    dest = original_path
    counter = 1
    stem = original_path.stem
    suffix = original_path.suffix
    while dest.exists():
        dest = original_path.parent / f"{stem}_restored_{counter}{suffix}"
        counter += 1
    try:
        shutil.move(str(new_path), str(dest))
        try:
            new_path.parent.rmdir()
        except OSError:
            pass
        conn.execute(
            "INSERT INTO actions (timestamp, original_path, new_path, category, action) VALUES (datetime('now'), ?, ?, ?, ?)",
            (str(new_path), str(dest), "Undo", "undo"),
        )
        conn.commit()
        print(f"Undone: {new_path.name} → {dest}")
        return True
    except Exception as e:
        print(f"Error undoing {action_id}: {e}")
        return False
    finally:
        conn.close()

def undo_last(n: int = 1, dry_run: bool = False, yes: bool = False):
    conn = ensure_db()
    rows = conn.execute(
        """SELECT id FROM actions WHERE action = 'move' ORDER BY id DESC LIMIT ?""", (n,),
    ).fetchall()
    conn.close()
    if not rows:
        print("No move actions to undo.")
        return
    print(f"Will undo the last {len(rows)} move(s):\n")
    list_actions(len(rows))
    if dry_run:
        print("\nDry run — no changes made.")
        return
    if not yes:
        confirm = input("\nProceed? [y/N]: ")
        if confirm.lower() not in ("y", "yes"):
            print("Cancelled.")
            return
    success = 0
    for (action_id,) in rows:
        if undo_action(action_id):
            success += 1
    print(f"\nDone. {success}/{len(rows)} action(s) undone.")

def main():
    parser = argparse.ArgumentParser(description="Undo Autopilot file moves.")
    parser.add_argument("--list", action="store_true", help="Show recent actions")
    parser.add_argument("--last", type=int, metavar="N", help="Undo the last N moves")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be undone without doing it")
    parser.add_argument("--yes", action="store_true", help="Auto-confirm undo without prompting")
    args = parser.parse_args()
    if args.list:
        list_actions()
    elif args.last is not None:
        if args.last < 1:
            print("N must be at least 1.")
            return
        undo_last(args.last, dry_run=args.dry_run, yes=args.yes)
    else:
        undo_last(1, dry_run=args.dry_run, yes=args.yes)

if __name__ == "__main__":
    main()
PYEOF

# Generate simple icons
cd src-tauri/icons
python3 -c "
from PIL import Image
Image.new('RGBA', (32, 32), (59, 130, 246, 255)).save('32x32.png')
Image.new('RGBA', (128, 128), (59, 130, 246, 255)).save('128x128.png')
Image.new('RGBA', (256, 256), (59, 130, 246, 255)).save('128x128@2x.png')
print('Icons created')
"
cd ../..

# GUI files
cat > gui/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Autopilot</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <div class="container">
    <header>
      <div class="status-badge" id="status-badge">Stopped</div>
      <h1>Autopilot</h1>
      <p class="subtitle">Your Downloads agent</p>
    </header>
    <section class="controls">
      <button id="btn-start" class="btn primary">Start Agent</button>
      <button id="btn-stop" class="btn danger" disabled>Stop Agent</button>
    </section>
    <section class="actions">
      <div class="actions-header">
        <h2>Recent Actions</h2>
        <button id="btn-refresh" class="btn ghost">Refresh</button>
      </div>
      <ul id="action-list" class="action-list">
        <li class="empty">No actions yet.</li>
      </ul>
      <button id="btn-undo" class="btn secondary" disabled>Undo Last</button>
    </section>
    <footer>
      <p>Runs in the background. Click the tray icon to hide/show.</p>
    </footer>
  </div>
  <script src="script.js"></script>
</body>
</html>
HTMLEOF

cat > gui/style.css << 'CSSEOF'
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #e2e8f0; font-size: 14px; line-height: 1.5; }
.container { max-width: 420px; margin: 0 auto; padding: 20px; }
header { text-align: center; margin-bottom: 24px; }
.status-badge { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; background: #334155; color: #94a3b8; margin-bottom: 10px; }
.status-badge.running { background: #064e3b; color: #34d399; }
h1 { font-size: 22px; font-weight: 700; margin-bottom: 4px; }
.subtitle { color: #94a3b8; font-size: 13px; }
.controls { display: flex; gap: 10px; margin-bottom: 24px; }
.btn { flex: 1; padding: 10px 14px; border: none; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: opacity 0.15s ease; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn.primary { background: #3b82f6; color: white; }
.btn.danger { background: #ef4444; color: white; }
.btn.secondary { background: #334155; color: #e2e8f0; width: 100%; margin-top: 12px; }
.btn.ghost { background: transparent; color: #94a3b8; font-weight: 500; padding: 4px 8px; flex: 0 0 auto; }
.actions { background: #1e293b; border-radius: 12px; padding: 16px; }
.actions-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.actions-header h2 { font-size: 14px; font-weight: 600; }
.action-list { list-style: none; max-height: 300px; overflow-y: auto; }
.action-list li { padding: 10px 12px; border-radius: 8px; background: #0f172a; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }
.action-list li:last-child { margin-bottom: 0; }
.action-list li.empty { background: transparent; color: #64748b; justify-content: center; font-size: 13px; }
.action-meta { display: flex; flex-direction: column; gap: 2px; }
.action-name { font-weight: 500; font-size: 13px; }
.action-detail { font-size: 11px; color: #64748b; }
.action-cat { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; color: #3b82f6; background: rgba(59,130,246,0.1); padding: 2px 8px; border-radius: 999px; }
footer { text-align: center; margin-top: 20px; color: #475569; font-size: 12px; }
CSSEOF

cat > gui/script.js << 'JSEOF'
const { invoke } = window.__TAURI__.core;
const statusBadge = document.getElementById('status-badge');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnUndo = document.getElementById('btn-undo');
const btnRefresh = document.getElementById('btn-refresh');
const actionList = document.getElementById('action-list');

async function updateStatus() {
  try {
    const running = await invoke('get_agent_status');
    if (running) {
      statusBadge.textContent = 'Running';
      statusBadge.classList.add('running');
      btnStart.disabled = true;
      btnStop.disabled = false;
    } else {
      statusBadge.textContent = 'Stopped';
      statusBadge.classList.remove('running');
      btnStart.disabled = false;
      btnStop.disabled = true;
    }
  } catch (e) { console.error('Status error:', e); }
}

async function loadActions() {
  try {
    const actions = await invoke('get_recent_actions', { limit: 20 });
    actionList.innerHTML = '';
    if (!actions || actions.length === 0) {
      actionList.innerHTML = '<li class="empty">No actions yet.</li>';
      btnUndo.disabled = true;
      return;
    }
    btnUndo.disabled = false;
    for (const a of actions) {
      const li = document.createElement('li');
      li.innerHTML = `<div class="action-meta"><span class="action-name">${a.original_name.replace(/</g,'&lt;')}</span><span class="action-detail">${new Date(a.timestamp).toLocaleString()}</span></div><span class="action-cat">${a.category}</span>`;
      actionList.appendChild(li);
    }
  } catch (e) {
    console.error('Actions error:', e);
    actionList.innerHTML = '<li class="empty">Error loading actions.</li>';
  }
}

btnStart.addEventListener('click', async () => {
  btnStart.disabled = true;
  try { await invoke('start_agent'); } catch (e) { alert('Failed to start: ' + e); }
  await updateStatus();
});

btnStop.addEventListener('click', async () => {
  btnStop.disabled = true;
  try { await invoke('stop_agent'); } catch (e) { alert('Failed to stop: ' + e); }
  await updateStatus();
});

btnUndo.addEventListener('click', async () => {
  btnUndo.disabled = true;
  try { await invoke('undo_last'); await loadActions(); }
  catch (e) { alert('Undo failed: ' + e); btnUndo.disabled = false; }
});

btnRefresh.addEventListener('click', loadActions);
setInterval(() => { updateStatus(); loadActions(); }, 3000);
updateStatus(); loadActions();
JSEOF

# Rust backend
cat > src-tauri/Cargo.toml << 'CARGOEOF'
[package]
name = "autopilot-gui"
version = "0.1.0"
description = "AI Agent Autopilot Menu Bar GUI"
edition = "2021"
rust-version = "1.77"

[build-dependencies]
tauri-build = { version = "2", features = [] }

[dependencies]
tauri = { version = "2", features = ["tray-icon"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["process", "time"] }
rusqlite = { version = "0.32", features = ["bundled"] }
dirs = "6"
CARGOEOF

cat > src-tauri/build.rs << 'BUILDEOF'
fn main() {
    tauri_build::build()
}
BUILDEOF

cat > src-tauri/tauri.conf.json << 'TAURIEOF'
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "Autopilot",
  "version": "0.1.0",
  "identifier": "com.autopilot.app",
  "build": {
    "beforeDevCommand": "",
    "beforeBuildCommand": "",
    "frontendDist": "../gui"
  },
  "app": {
    "withGlobalTauri": true,
    "windows": [
      {
        "label": "main",
        "title": "Autopilot",
        "width": 420,
        "height": 640,
        "resizable": false,
        "fullscreen": false,
        "visible": false,
        "decorations": true,
        "alwaysOnTop": false
      }
    ],
    "trayIcon": {
      "id": "main",
      "iconPath": "icons/32x32.png",
      "iconAsTemplate": true,
      "tooltip": "Autopilot Agent"
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png"
    ]
  }
}
TAURIEOF

cat > src-tauri/src/main.rs << 'RUSTEOF'
use std::sync::Mutex;
use std::path::PathBuf;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::Manager;
use serde::Serialize;

struct AgentState {
    child: Mutex<Option<tokio::process::Child>>,
}

#[derive(Serialize)]
struct Action {
    id: i64,
    timestamp: String,
    category: String,
    original_name: String,
    new_name: String,
}

fn project_dir() -> PathBuf {
    let home = dirs::home_dir().expect("home dir");
    home.join("Projects/Personal/aiagent-autopilot")
}

fn db_path() -> PathBuf {
    let home = dirs::home_dir().expect("home dir");
    home.join("Downloads/Autopilot/.autopilot.db")
}

#[tauri::command]
async fn start_agent(state: tauri::State<'_, AgentState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;
    if child_guard.is_some() {
        return Ok("Already running".into());
    }
    let proj = project_dir();
    let python = proj.join(".venv/bin/python");
    let script = proj.join("main.py");
    let child = tokio::process::Command::new(&python)
        .arg(&script)
        .current_dir(&proj)
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null())
        .spawn()
        .map_err(|e| format!("Failed to start agent: {e}"))?;
    *child_guard = Some(child);
    Ok("Agent started".into())
}

#[tauri::command]
async fn stop_agent(state: tauri::State<'_, AgentState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;
    if let Some(mut child) = child_guard.take() {
        let _ = child.kill().await;
    }
    Ok("Agent stopped".into())
}

#[tauri::command]
async fn get_agent_status(state: tauri::State<'_, AgentState>) -> Result<bool, String> {
    let child_guard = state.child.lock().map_err(|e| e.to_string())?;
    Ok(child_guard.is_some())
}

#[tauri::command]
async fn get_recent_actions(limit: i64) -> Result<Vec<Action>, String> {
    let db = db_path();
    if !db.exists() {
        return Ok(vec![]);
    }
    let conn = rusqlite::Connection::open(&db).map_err(|e| e.to_string())?;
    let mut stmt = conn.prepare(
        "SELECT id, timestamp, category, original_path, new_path FROM actions ORDER BY id DESC LIMIT ?"
    ).map_err(|e| e.to_string())?;
    let rows = stmt.query_map([limit], |row| {
        let orig: String = row.get(3)?;
        let new: String = row.get(4)?;
        Ok(Action {
            id: row.get(0)?,
            timestamp: row.get(1)?,
            category: row.get(2)?,
            original_name: PathBuf::from(orig).file_name().unwrap_or_default().to_string_lossy().to_string(),
            new_name: PathBuf::from(new).file_name().unwrap_or_default().to_string_lossy().to_string(),
        })
    }).map_err(|e| e.to_string())?;
    let mut actions = Vec::new();
    for row in rows { actions.push(row.map_err(|e| e.to_string())?); }
    Ok(actions)
}

#[tauri::command]
async fn undo_last() -> Result<String, String> {
    let proj = project_dir();
    let python = proj.join(".venv/bin/python");
    let script = proj.join("undo.py");
    let output = tokio::process::Command::new(&python)
        .args([&script, "--last", "1", "--yes"])
        .current_dir(&proj)
        .output()
        .await
        .map_err(|e| format!("Failed to run undo: {e}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    if !output.status.success() {
        return Err(format!("Undo failed: {}", String::from_utf8_lossy(&output.stderr)));
    }
    Ok(stdout.to_string())
}

pub fn run() {
    tauri::Builder::default()
        .manage(AgentState { child: Mutex::new(None) })
        .invoke_handler(tauri::generate_handler![
            start_agent, stop_agent, get_agent_status, get_recent_actions, undo_last
        ])
        .setup(|app| {
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&quit_i])?;
            let home = dirs::home_dir().unwrap();
            let icon_path = home.join("Projects/Personal/aiagent-autopilot/src-tauri/icons/32x32.png");
            let icon = tauri::image::Image::from_path(&icon_path)
                .or_else(|_| app.default_window_icon().cloned())
                .expect("Failed to load tray icon");
            let _tray = TrayIconBuilder::with_id("main")
                .icon(icon)
                .tooltip("Autopilot Agent")
                .menu(&menu)
                .on_menu_event(|app, event| {
                    if event.id.as_ref() == "quit" { app.exit(0); }
                })
                .on_tray_icon_event(|tray, event| {
                    use tauri::tray::TrayIconEvent;
                    use tauri::MouseButton;
                    use tauri::MouseButtonState;
                    if let TrayIconEvent::Click { button: MouseButton::Left, button_state: MouseButtonState::Up, .. } = event {
                        let app = tray.app_handle();
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                })
                .build(app)?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn main() { run(); }
RUSTEOF

# README
cat > README.md << 'READMEEOF'
# AI Agent Autopilot

A minimal Python prototype for an ambient file-organizing agent — now with a **Tauri menu-bar GUI**.

## What it does

Watches your `~/Downloads` folder and automatically moves new files into categorized subfolders inside `~/Downloads/Autopilot`.

## Quick start (headless)

```bash
cd ~/Projects/Personal/aiagent-autopilot
source .venv/bin/activate
python main.py
```

## Build the menu-bar GUI

### 1. Fix apt dependencies (Ubuntu/Debian)

```bash
sudo apt --fix-broken install
sudo apt install -y libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev
```

### 2. Install Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source $HOME/.cargo/env
```

### 3. Install Tauri CLI

```bash
cargo install tauri-cli --version "^2.0"
```

### 4. Build & run

```bash
cd ~/Projects/Personal/aiagent-autopilot/src-tauri
cargo tauri dev
```

## Undo

```bash
python undo.py --list
python undo.py --last 5
```
READMEEOF

echo ""
echo "✅ Project created at ~/Projects/Personal/aiagent-autopilot"
echo ""
echo "Next steps on your local machine:"
echo "  1. sudo apt --fix-broken install"
echo "  2. sudo apt install -y libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev"
echo "  3. curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y"
echo "  4. source ~/.cargo/env && cargo install tauri-cli --version '^2.0'"
echo "  5. cd ~/Projects/Personal/aiagent-autopilot/src-tauri && cargo tauri dev"
