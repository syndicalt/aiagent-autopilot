import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import DOWNLOADS_DIR, ORGANIZED_ROOT
from classifier import classify_file
from organizer import organize
from notifier import notify
from embedding_classifier import warm_up

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
            pass  # Not inside Autopilot, proceed

        # Debounce: wait for partial downloads to finish
        time.sleep(0.5)
        if not file_path.exists():
            return  # Already moved by a concurrent handler

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
            # Race condition: another handler already moved it
            print(f"[RACE] File already moved: {file_path.name}")
        except Exception as e:
            notify("Autopilot Error", f"Could not move {file_path.name}: {e}")
            print(f"[ERROR] {e}")

def main():
    print(f"👀 Watching {DOWNLOADS_DIR} for new files...")
    print("Press Ctrl+C to stop.\n")

    # Proactive model warm-up in background so first classification is instant
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
