import time
import threading
import subprocess
import sys
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import DOWNLOADS_DIR, ORGANIZED_ROOT
from classifier import classify_file
from organizer import organize
from notifier import notify
from embedding_classifier import warm_up


def _ensure_brain():
    """Start the brain service if it's not already running."""
    import urllib.request
    try:
        urllib.request.urlopen("http://127.0.0.1:8765/status", timeout=0.5)
        return  # Already running
    except Exception:
        pass

    proj_root = Path(__file__).parent
    brain_main = proj_root / "brain" / "main.py"
    python = sys.executable

    if not brain_main.exists():
        print("[BRAIN] brain/main.py not found; skipping brain launch")
        return

    print("[BRAIN] Starting embedding service...")
    try:
        subprocess.Popen(
            [python, str(brain_main)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        # Give it a moment to bind
        time.sleep(1.5)
    except Exception as e:
        print(f"[BRAIN] Failed to start: {e}")

# Thread-safe deduplication: tracks files currently being processed
_processing_lock = threading.Lock()
_processing = set()

def _mark_processing(path: str) -> bool:
    """Mark a file as being processed. Returns False if already being processed."""
    with _processing_lock:
        if path in _processing:
            return False
        _processing.add(path)
        return True

def _unmark_processing(path: str):
    """Remove a file from the processing set."""
    with _processing_lock:
        _processing.discard(path)

class DownloadsHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        file_path = Path(event.src_path)

        # Ignore files we already moved into Autopilot
        try:
            file_path.relative_to(ORGANIZED_ROOT)
            return
        except ValueError:
            pass

        # Skip if another handler is already processing this file
        if not _mark_processing(str(file_path)):
            return

        try:
            # Debounce: wait for partial downloads to finish
            time.sleep(0.5)
            if not file_path.exists():
                return

            category = classify_file(file_path)
            if category == "Skip":
                return

            try:
                new_path = organize(file_path, category)
                notify(
                    "Autopilot",
                    f"Moved '{file_path.name}' → {category}",
                )
                print(f"[MOVE] {file_path} -> {new_path}")
            except FileNotFoundError:
                print(f"[RACE] File already moved: {file_path.name}")
            except Exception as e:
                notify("Autopilot Error", f"Could not move {file_path.name}: {e}")
                print(f"[ERROR] {e}")
        finally:
            _unmark_processing(str(file_path))

def main():
    print(f"👀 Watching {DOWNLOADS_DIR} for new files...")
    print("Press Ctrl+C to stop.\n")

    # Start the brain service if available, then warm up the model
    _ensure_brain()
    threading.Thread(target=warm_up, daemon=True).start()

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
