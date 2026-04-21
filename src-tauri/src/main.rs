use std::path::PathBuf;
use std::fs::File;
use tokio::sync::Mutex;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{TrayIconBuilder, TrayIconEvent};
use tauri::Manager;
use tauri::WindowEvent;
use serde::Serialize;

struct AgentState {
    child: Mutex<Option<tokio::process::Child>>,
}

fn log_path() -> PathBuf {
    dirs::home_dir().expect("home dir").join("Downloads/Autopilot/.agent.log")
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
    dirs::home_dir().expect("home dir").join("Projects/Personal/aiagent-autopilot")
}

fn db_path() -> PathBuf {
    dirs::home_dir().expect("home dir").join("Downloads/Autopilot/.autopilot.db")
}

fn settings_path() -> PathBuf {
    dirs::home_dir().expect("home dir").join("Downloads/Autopilot/.settings.json")
}

fn read_notifications_muted() -> bool {
    let path = settings_path();
    if !path.exists() {
        return false;
    }
    let content = std::fs::read_to_string(&path).unwrap_or_default();
    let json: serde_json::Value = serde_json::from_str(&content).unwrap_or_default();
    json.get("notifications_muted").and_then(|v| v.as_bool()).unwrap_or(false)
}

#[tauri::command]
async fn start_agent(state: tauri::State<'_, AgentState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().await;
    if child_guard.is_some() {
        return Ok("Already running".into());
    }
    let proj = project_dir();
    let python = proj.join(".venv/bin/python");
    let script = proj.join("main.py");

    // Ensure log dir exists
    let log = log_path();
    if let Some(parent) = log.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let stderr_file = File::create(&log)
        .map_err(|e| format!("Failed to create log file: {e}"))?;

    let child = tokio::process::Command::new(&python)
        .arg(&script)
        .current_dir(&proj)
        .stdout(std::process::Stdio::null())
        .stderr(stderr_file)
        .spawn()
        .map_err(|e| format!("Failed to start agent: {e}"))?;
    *child_guard = Some(child);
    Ok("Agent started".into())
}

#[tauri::command]
async fn get_agent_logs() -> Result<String, String> {
    let log = log_path();
    if !log.exists() {
        return Ok("No logs yet.".into());
    }
    let content = std::fs::read_to_string(&log).unwrap_or_default();
    // Return last 50 lines
    let lines: Vec<&str> = content.lines().collect();
    let start = lines.len().saturating_sub(50);
    Ok(lines[start..].join("\n"))
}

#[tauri::command]
async fn stop_agent(state: tauri::State<'_, AgentState>) -> Result<String, String> {
    let mut child_guard = state.child.lock().await;
    if let Some(mut child) = child_guard.take() {
        let _ = child.kill().await;
    }
    Ok("Agent stopped".into())
}

#[tauri::command]
async fn get_agent_status(state: tauri::State<'_, AgentState>) -> Result<bool, String> {
    let child_guard = state.child.lock().await;
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
    for row in rows {
        actions.push(row.map_err(|e| e.to_string())?);
    }
    Ok(actions)
}

#[tauri::command]
async fn get_smart_sort_status() -> Result<bool, String> {
    let home = dirs::home_dir().ok_or("no home")?;
    let cache = home.join(".cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2");
    Ok(cache.exists())
}

#[tauri::command]
async fn toggle_notifications() -> Result<bool, String> {
    let proj = project_dir();
    let python = proj.join(".venv/bin/python");
    let script = proj.join("settings.py");
    let output = tokio::process::Command::new(&python)
        .arg(&script)
        .arg("--toggle")
        .current_dir(&proj)
        .output()
        .await
        .map_err(|e| format!("Failed to toggle notifications: {e}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let stderr = String::from_utf8_lossy(&output.stderr);
    if !output.status.success() {
        return Err(format!("Toggle failed: {stderr}"));
    }
    // Parse the boolean from stdout
    let muted = stdout.trim() == "True";
    Ok(muted)
}

#[tauri::command]
async fn get_notifications_muted() -> Result<bool, String> {
    Ok(read_notifications_muted())
}

#[tauri::command]
async fn undo_last() -> Result<String, String> {
    let proj = project_dir();
    let python = proj.join(".venv/bin/python");
    let script = proj.join("undo.py");
    let output = tokio::process::Command::new(&python)
        .arg(&script)
        .arg("--last")
        .arg("1")
        .arg("--yes")
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

fn blue_icon() -> tauri::image::Image<'static> {
    let rgba = vec![59u8, 130, 246, 255].repeat(32 * 32);
    tauri::image::Image::new_owned(rgba, 32, 32)
}

pub fn run() {
    tauri::Builder::default()
        .manage(AgentState { child: Mutex::new(None) })
        .invoke_handler(tauri::generate_handler![
            start_agent, stop_agent, get_agent_status, get_recent_actions, undo_last, get_smart_sort_status,
            toggle_notifications, get_notifications_muted, get_agent_logs
        ])
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .setup(|app| {
            let open_i = MenuItem::with_id(app, "open", "Open", true, None::<&str>)?;
            let muted = read_notifications_muted();
            let mute_label = if muted { "Unmute Notifications" } else { "Mute Notifications" };
            let mute_i = MenuItem::with_id(app, "mute", mute_label, true, None::<&str>)?;
            let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open_i, &mute_i, &quit_i])?;
            
            let icon = blue_icon();
            
            let _tray = TrayIconBuilder::with_id("main")
                .icon(icon)
                .tooltip("Autopilot Agent")
                .menu(&menu)
                .on_menu_event(|app, event| {
                    match event.id.as_ref() {
                        "quit" => { app.exit(0); }
                        "open" => {
                            if let Some(window) = app.get_webview_window("main") {
                                let _ = window.show();
                                let _ = window.set_focus();
                            }
                        }
                        "mute" => {
                            let proj = project_dir();
                            let python = proj.join(".venv/bin/python");
                            let script = proj.join("settings.py");
                            let _ = std::process::Command::new(&python)
                                .arg(&script)
                                .arg("--toggle")
                                .current_dir(&proj)
                                .output();
                        }
                        _ => {}
                    }
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::DoubleClick { .. } = event {
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
