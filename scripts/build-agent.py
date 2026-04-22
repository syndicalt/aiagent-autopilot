#!/usr/bin/env python3
"""
Build script for the standalone Autopilot agent binary.

This script is invoked by Tauri's beforeBuildCommand to produce the
autopilot-agent sidecar binary before the Rust app is bundled.

It also creates a platform-agnostic stub so that tauri.conf.json can
list both filenames under bundle.resources without breaking the build
on any platform.
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST_DIR = ROOT / "dist"
RESOURCES_DIR = ROOT / "src-tauri" / "resources"
SPEC = ROOT / "agent.spec"


def find_venv_python() -> Path:
    """
    Locate the project's virtualenv Python interpreter.
    Returns the venv python if found, otherwise falls back to sys.executable.
    """
    candidates = [
        ROOT / ".venv" / "bin" / "python",
        ROOT / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def main():
    python = find_venv_python()

    # Verify PyInstaller is available in the target interpreter
    result = subprocess.run(
        [str(python), "-c", "import PyInstaller; print('ok')"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"PyInstaller not found in {python}")
        print("Install with: .venv/bin/pip install pyinstaller")
        sys.exit(1)

    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

    # Run PyInstaller using the venv Python
    subprocess.run(
        [str(python), "-m", "PyInstaller", str(SPEC), "--noconfirm"],
        check=True,
        cwd=str(ROOT),
    )

    # Determine the real binary name for this platform
    real_name = "autopilot-agent"
    if sys.platform == "win32":
        real_name += ".exe"

    src = DIST_DIR / real_name
    dst = RESOURCES_DIR / real_name

    if not src.exists():
        print(f"ERROR: Expected binary not found at {src}")
        sys.exit(1)

    shutil.copy2(src, dst)
    size_mb = dst.stat().st_size / (1024 * 1024)
    print(f"Agent binary built: {dst} ({size_mb:.1f} MB)")

    # Create a stub for the OTHER platform's filename so tauri.conf.json
    # can list both resources without breaking the build on any OS.
    stub_name = "autopilot-agent.exe" if real_name == "autopilot-agent" else "autopilot-agent"
    stub_path = RESOURCES_DIR / stub_name
    if not stub_path.exists():
        # Write a tiny placeholder; Tauri only validates existence, not content
        stub_path.write_text("# placeholder for cross-platform resource validation\n")
        print(f"Created platform stub: {stub_path}")


if __name__ == "__main__":
    main()
