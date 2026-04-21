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
        # Small debounce for partial downloads
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
        except Exception as e:
            notify("Autopilot Error", f"Could not move {file_path.name}: {e}")
            print(f"[ERROR] {e}")

def main():
    print(f"👀 Watching {DOWNLOADS_DIR} for new files...")
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
