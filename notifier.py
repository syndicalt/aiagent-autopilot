import platform
import subprocess

def notify(title: str, message: str):
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(
                ["osascript", "-e", f'display notification "{message}" with title "{title}"'],
                check=False,
            )
        elif system == "Linux":
            subprocess.run(
                ["notify-send", title, message],
                check=False,
            )
        elif system == "Windows":
            # Fallback to PowerShell Toast
            subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"Add-Type -AssemblyName System.Windows.Forms; "
                    f"[System.Windows.Forms.MessageBox]::Show('{message}', '{title}')",
                ],
                check=False,
            )
        else:
            print(f"[{title}] {message}")
    except Exception:
        print(f"[{title}] {message}")
