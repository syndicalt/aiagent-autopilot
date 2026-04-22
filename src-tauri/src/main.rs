//! Autopilot Tauri v2 backend.
//!
//! Manages the Python agent lifecycle, exposes commands to the web frontend,
//! and sets up the system tray with close-to-tray behavior.

use std::path::PathBuf;
use tokio::sync::Mutex;
use tauri::menu::{Menu, MenuItem};
use tauri::tray::{TrayIconBuilder, TrayIconEvent};
use tauri::Manager;
use tauri::WindowEvent;
use serde::Serialize;

/// Shared application state: the spawned Python agent child process.
struct AgentState {
    child: Mutex<Option<tokio::process::Child>>,
}

/// Path to the agent's stderr log file.
fn log_path() -> PathBuf {
    dirs::home_dir().expect("home dir").join("Downloads/Autopilot/.agent.log")
}

/// Path to the PID file used for cross-instance agent detection.
fn pid_path() -> PathBuf {
    dirs::home_dir().expect("home dir").join("Downloads/Autopilot/.agent.pid")
}

/// Check whether a process with the given PID is still alive.
#[cfg(unix)]
fn is_pid_alive(pid: u32) -> bool {
    std::process::Command::new("kill")
        .arg("-0")
        .arg(pid.to_string())
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

#[cfg(windows)]
fn is_pid_alive(pid: u32) -> bool {
    match std::process::Command::new("tasklist")
        .args(["/FI", &format!("PID eq {}", pid), "/NH", "/FO", "CSV"])
        .output()
    {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            stdout.contains(&pid.to_string())
        }
        Err(_) => false,
    }
}

/// Read the agent PID from the PID file, if it exists.
fn read_agent_pid() -> Option<u32> {
    let path = pid_path();
    if !path.exists() {
        return None;
    }
    std::fs::read_to_string(&path).ok()?.trim().parse().ok()
}

/// Write the agent PID to the PID file.
fn write_agent_pid(pid: u32) {
    let path = pid_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let _ = std::fs::write(&path, pid.to_string());
}

/// Remove the PID file.
fn clear_agent_pid() {
    let _ = std::fs::remove_file(pid_path());
}

/// Locate the bundled autopilot-agent sidecar binary, if it exists.
/// Searches next to the current executable and in platform-specific
/// resource directories (e.g. macOS app bundle Resources/).
fn agent_binary_path() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;

    for name in &["autopilot-agent", "autopilot-agent.exe"] {
        let candidate = dir.join(name);
        if candidate.exists() {
            return Some(candidate);
        }
    }

    // macOS app bundle: Resources is sibling to MacOS
    #[cfg(target_os = "macos")]
    {
        let candidate = dir.parent()?.join("Resources").join("autopilot-agent");
        if candidate.exists() {
            return Some(candidate);
        }
    }

    None
}

/// Resolve the command and arguments for running an agent subcommand.
/// Returns (binary_path, args, optional_cwd).
///
/// In release/bundled mode, uses the frozen sidecar binary.
/// In dev mode, falls back to the system Python interpreter.
fn resolve_agent_command(subcommand: Option<&str>, extra_args: Vec<String>) -> (PathBuf, Vec<String>, Option<PathBuf>) {
    if let Some(agent_bin) = agent_binary_path() {
        let mut args = Vec::new();
        if let Some(cmd) = subcommand {
            args.push(cmd.to_string());
        }
        args.extend(extra_args);
        (agent_bin, args, None)
    } else {
        // Dev mode fallback: spawn from the local repo venv
        let proj = project_dir();
        let python = python_exe(&proj);
        let script = match subcommand {
            Some(cmd) => proj.join(format!("{}.py", cmd)),
            None => proj.join("main.py"),
        };
        let mut args = vec![script.to_string_lossy().to_string()];
        args.extend(extra_args);
        (python, args, Some(proj))
    }
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

/// Path to the Python interpreter inside the project virtualenv.
#[cfg(unix)]
fn python_exe(proj: &PathBuf) -> PathBuf {
    proj.join(".venv/bin/python")
}

#[cfg(windows)]
fn python_exe(proj: &PathBuf) -> PathBuf {
    proj.join(".venv/Scripts/python.exe")
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

    // System-level guard: check PID file for surviving agent processes
    if let Some(pid) = read_agent_pid() {
        if is_pid_alive(pid) {
            return Ok("Already running".into());
        }
        clear_agent_pid();
    }

    // Resolve command: bundled sidecar in release, system Python in dev
    let (cmd, args, cwd) = resolve_agent_command(None, vec![]);

    // Ensure log dir exists
    let log = log_path();
    if let Some(parent) = log.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let stderr_file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log)
        .map_err(|e| format!("Failed to open log file: {e}"))?;

    let mut command = tokio::process::Command::new(&cmd);
    command.args(&args).stdout(std::process::Stdio::null()).stderr(stderr_file);
    if let Some(dir) = cwd {
        command.current_dir(dir);
    }

    let child = command.spawn().map_err(|e| format!("Failed to start agent: {e}"))?;

    if let Some(id) = child.id() {
        write_agent_pid(id);
    }

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
    clear_agent_pid();
    Ok("Agent stopped".into())
}

#[tauri::command]
async fn get_agent_status(state: tauri::State<'_, AgentState>) -> Result<bool, String> {
    let mut child_guard = state.child.lock().await;
    if let Some(ref mut child) = *child_guard {
        // Verify the process is actually alive, not just a stale handle
        match child.try_wait() {
            Ok(Some(_)) => {
                // Process has exited; clean up stale handle
                *child_guard = None;
                clear_agent_pid();
                return Ok(false);
            }
            Ok(None) => return Ok(true), // Still running
            Err(_) => return Ok(true),   // Can't determine; assume running
        }
    }
    // Fallback to PID file for cross-instance detection
    if let Some(pid) = read_agent_pid() {
        if is_pid_alive(pid) {
            return Ok(true);
        }
        clear_agent_pid();
    }
    Ok(false)
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
async fn get_smart_sort_status() -> Result<String, String> {
    // Probe the brain service on localhost:8765
    match reqwest::get("http://127.0.0.1:8765/status").await {
        Ok(resp) => {
            if let Ok(json) = resp.json::<serde_json::Value>().await {
                let ready = json.get("ready").and_then(|v| v.as_bool()).unwrap_or(false);
                let cloud_ready = json.get("cloud_ready").and_then(|v| v.as_bool()).unwrap_or(false);
                if ready && cloud_ready {
                    return Ok("cloud".into());
                }
                if ready {
                    return Ok("local".into());
                }
            }
        }
        Err(_) => {}
    }
    // No brain service detected — fall back to rules + heuristics
    Ok("rules".into())
}

#[tauri::command]
async fn toggle_notifications() -> Result<bool, String> {
    let (cmd, args, cwd) = resolve_agent_command(Some("settings"), vec!["--toggle".into()]);
    let mut command = tokio::process::Command::new(&cmd);
    command.args(&args);
    if let Some(dir) = cwd {
        command.current_dir(dir);
    }
    let output = command.output()
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
    let (cmd, args, cwd) = resolve_agent_command(
        Some("undo"),
        vec!["--last".into(), "1".into(), "--yes".into()],
    );
    let mut command = tokio::process::Command::new(&cmd);
    command.args(&args);
    if let Some(dir) = cwd {
        command.current_dir(dir);
    }
    let output = command.output()
        .await
        .map_err(|e| format!("Failed to run undo: {e}"))?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    if !output.status.success() {
        return Err(format!("Undo failed: {}", String::from_utf8_lossy(&output.stderr)));
    }
    Ok(stdout.to_string())
}

fn rules_path() -> PathBuf {
    dirs::home_dir().expect("home dir").join("Downloads/Autopilot/.rules.json")
}

#[tauri::command]
async fn get_rules() -> Result<serde_json::Value, String> {
    let path = rules_path();
    if !path.exists() {
        return Ok(serde_json::json!([]));
    }
    let content = std::fs::read_to_string(&path).unwrap_or_default();
    let rules: serde_json::Value = serde_json::from_str(&content).unwrap_or_else(|_| serde_json::json!([]));
    Ok(rules)
}

#[tauri::command]
async fn save_rules(rules: serde_json::Value) -> Result<(), String> {
    let path = rules_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let content = serde_json::to_string_pretty(&rules).map_err(|e| e.to_string())?;
    std::fs::write(&path, content).map_err(|e| e.to_string())?;
    Ok(())
}

#[tauri::command]
async fn test_rules(file_name: String, rules: serde_json::Value) -> Result<Vec<bool>, String> {
    let rules_json = serde_json::to_string(&rules).map_err(|e| e.to_string())?;
    let (cmd, args, cwd) = resolve_agent_command(
        Some("rules"),
        vec!["--test-each".into(), rules_json, file_name],
    );
    let mut command = tokio::process::Command::new(&cmd);
    command.args(&args);
    if let Some(dir) = cwd {
        command.current_dir(dir);
    }
    let output = command.output()
        .await
        .map_err(|e| format!("Failed to test rules: {e}"))?;
    if !output.status.success() {
        return Err(format!("Test failed: {}", String::from_utf8_lossy(&output.stderr)));
    }
    let stdout = String::from_utf8_lossy(&output.stdout);
    let results: Vec<bool> = serde_json::from_str(stdout.trim()).map_err(|e| format!("Invalid test output: {e}"))?;
    Ok(results)
}

fn app_icon() -> tauri::image::Image<'static> {
    let bytes = include_bytes!("../icons/32x32.png");
    let decoder = png::Decoder::new(std::io::Cursor::new(bytes));
    let mut reader = decoder.read_info().expect("valid png");
    let mut buf = vec![0; reader.output_buffer_size()];
    let info = reader.next_frame(&mut buf).expect("decode png");
    // Convert RGB/RGBA to RGBA if needed
    let rgba = match info.color_type {
        png::ColorType::Rgba => buf,
        png::ColorType::Rgb => {
            let mut rgba = Vec::with_capacity(buf.len() / 3 * 4);
            for chunk in buf.chunks_exact(3) {
                rgba.extend_from_slice(chunk);
                rgba.push(255);
            }
            rgba
        }
        _ => panic!("unsupported png color type"),
    };
    tauri::image::Image::new_owned(rgba, info.width, info.height)
}

pub fn run() {
    tauri::Builder::default()
        .manage(AgentState { child: Mutex::new(None) })
        .invoke_handler(tauri::generate_handler![
            start_agent, stop_agent, get_agent_status, get_recent_actions, undo_last, get_smart_sort_status,
            toggle_notifications, get_notifications_muted, get_agent_logs, get_rules, save_rules, test_rules
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
            
            let icon = app_icon();
            
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
                            let (cmd, args, cwd) = resolve_agent_command(Some("settings"), vec!["--toggle".into()]);
                            let mut command = std::process::Command::new(&cmd);
                            command.args(&args);
                            if let Some(dir) = cwd {
                                command.current_dir(dir);
                            }
                            match command.output()
                            {
                                Ok(output) => {
                                    if output.status.success() {
                                        let muted = read_notifications_muted();
                                        let mute_label = if muted { "Unmute Notifications" } else { "Mute Notifications" };
                                        let new_mute_i = MenuItem::with_id(app, "mute", mute_label, true, None::<&str>);
                                        let open_i = MenuItem::with_id(app, "open", "Open", true, None::<&str>);
                                        let quit_i = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>);
                                        if let (Ok(new_mute_i), Ok(open_i), Ok(quit_i)) = (new_mute_i, open_i, quit_i) {
                                            if let Ok(new_menu) = Menu::with_items(app, &[&open_i, &new_mute_i, &quit_i]) {
                                                if let Some(tray) = app.tray_by_id("main") {
                                                    let _ = tray.set_menu(Some(new_menu));
                                                }
                                            }
                                        }
                                    } else {
                                        let stderr = String::from_utf8_lossy(&output.stderr);
                                        eprintln!("Mute toggle failed: {}", stderr);
                                        if let Some(tray) = app.tray_by_id("main") {
                                            let _ = tray.set_tooltip(Some(&format!("Toggle failed: {}", stderr)));
                                        }
                                    }
                                }
                                Err(e) => {
                                    eprintln!("Failed to run mute toggle: {}", e);
                                    if let Some(tray) = app.tray_by_id("main") {
                                        let _ = tray.set_tooltip(Some(&format!("Toggle error: {}", e)));
                                    }
                                }
                            }
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
