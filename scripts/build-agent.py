#!/usr/bin/env python3
"""
Build script for the standalone Autopilot agent binary.

This script is invoked by Tauri's beforeBuildCommand to produce the
autopilot-agent sidecar binary before the Rust app is bundled.
"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
DIST_DIR = ROOT / "dist"
RESOURCES_DIR = ROOT / "src-tauri" / "resources"
SPEC = ROOT / "agent.spec"


def main():
    # Ensure PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Install with: pip install pyinstaller")
        sys.exit(1)

    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)

    # Run PyInstaller
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm"],
        check=True,
        cwd=str(ROOT),
    )

    # Copy binary to Tauri resources
    binary_name = "autopilot-agent"
    if sys.platform == "win32":
        binary_name += ".exe"

    src = DIST_DIR / binary_name
    dst = RESOURCES_DIR / binary_name

    if not src.exists():
        print(f"ERROR: Expected binary not found at {src}")
        sys.exit(1)

    shutil.copy2(src, dst)
    size_mb = dst.stat().st_size / (1024 * 1024)
    print(f"Agent binary built: {dst} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
