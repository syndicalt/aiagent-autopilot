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
            subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'], check=False)
        elif system == "Linux":
            subprocess.run(["notify-send", title, message], check=False)
        else:
            print(f"[{title}] {message}")
    except Exception:
        print(f"[{title}] {message}")
    except Exception:
        print(f"[{title}] {message}")
