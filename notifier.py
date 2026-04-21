"""
Cross-platform desktop notifications for Autopilot.

Uses native notification APIs on each platform:
- Linux: notify-send
- macOS: osascript
- Windows: PowerShell toast (no extra dependencies)
"""

import platform
import subprocess
from settings import are_notifications_muted


def notify(title: str, message: str):
    if are_notifications_muted():
        print(f"[MUTED] [{title}] {message}")
        return
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
                check=False,
            )
        elif system == "Linux":
            subprocess.run(["notify-send", title, message], check=False)
        elif system == "Windows":
            _notify_windows(title, message)
        else:
            print(f"[{title}] {message}")
    except Exception:
        print(f"[{title}] {message}")


def _notify_windows(title: str, message: str):
    """Show a Windows toast notification using PowerShell."""
    ps_script = (
        f'Add-Type -AssemblyName System.Windows.Forms; '
        f'$n = New-Object System.Windows.Forms.NotifyIcon; '
        f'$n.Icon = [System.Drawing.SystemIcons]::Information; '
        f'$n.BalloonTipTitle = "{title}"; '
        f'$n.BalloonTipText = "{message}"; '
        f'$n.Visible = $true; '
        f'$n.ShowBalloonTip(5000)'
    )
    subprocess.run(
        ["powershell", "-Command", ps_script],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
