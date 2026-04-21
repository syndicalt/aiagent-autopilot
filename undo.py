import argparse
import shutil
import sqlite3
from pathlib import Path
from organizer import ensure_db, ORGANIZED_ROOT

def list_actions(limit: int = 10):
    conn = ensure_db()
    rows = conn.execute(
        """
        SELECT id, timestamp, category, original_path, new_path, action
        FROM actions
        ORDER BY id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()

    if not rows:
        print("No actions found.")
        return []

    print(f"{'ID':>4} | {'Time':19} | {'Category':12} | {'Action':6} | Original → New")
    print("-" * 120)
    for row in rows:
        id_, ts, cat, orig, new, act = row
        orig_name = Path(orig).name
        new_name = Path(new).name
        print(f"{id_:>4} | {ts[:19]} | {cat:12} | {act:6} | {orig_name} → {new_name}")
    return rows

def undo_action(action_id: int) -> bool:
    conn = ensure_db()
    row = conn.execute(
        "SELECT original_path, new_path FROM actions WHERE id = ?",
        (action_id,),
    ).fetchone()

    if not row:
        print(f"Action {action_id} not found.")
        conn.close()
        return False

    original_path = Path(row[0])
    new_path = Path(row[1])

    if not new_path.exists():
        print(f"❌ Cannot undo {action_id}: file no longer exists at {new_path}")
        conn.close()
        return False

    # Ensure original directory exists
    original_path.parent.mkdir(parents=True, exist_ok=True)

    # Handle collisions at original path
    dest = original_path
    counter = 1
    stem = original_path.stem
    suffix = original_path.suffix
    while dest.exists():
        dest = original_path.parent / f"{stem}_restored_{counter}{suffix}"
        counter += 1

    try:
        shutil.move(str(new_path), str(dest))
        # Remove empty category folders
        try:
            new_path.parent.rmdir()
        except OSError:
            pass

        # Log the undo
        conn.execute(
            "INSERT INTO actions (timestamp, original_path, new_path, category, action) VALUES (datetime('now'), ?, ?, ?, ?)",
            (str(new_path), str(dest), "Undo", "undo"),
        )
        conn.commit()
        print(f"✅ Undone: {new_path.name} → {dest}")
        return True
    except Exception as e:
        print(f"❌ Error undoing {action_id}: {e}")
        return False
    finally:
        conn.close()

def undo_last(n: int = 1, dry_run: bool = False, yes: bool = False):
    conn = ensure_db()
    rows = conn.execute(
        """
        SELECT id FROM actions
        WHERE action = 'move'
        ORDER BY id DESC
        LIMIT ?
        """,
        (n,),
    ).fetchall()
    conn.close()

    if not rows:
        print("No move actions to undo.")
        return

    print(f"Will undo the last {len(rows)} move(s):\n")
    list_actions(len(rows))

    if dry_run:
        print("\n🔍 Dry run — no changes made.")
        return

    if not yes:
        confirm = input("\nProceed? [y/N]: ")
        if confirm.lower() not in ("y", "yes"):
            print("Cancelled.")
            return

    success = 0
    for (action_id,) in rows:
        if undo_action(action_id):
            success += 1

    print(f"\nDone. {success}/{len(rows)} action(s) undone.")

def main():
    parser = argparse.ArgumentParser(description="Undo Autopilot file moves.")
    parser.add_argument("--list", action="store_true", help="Show recent actions")
    parser.add_argument("--last", type=int, metavar="N", help="Undo the last N moves")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be undone without doing it")
    parser.add_argument("--yes", action="store_true", help="Auto-confirm undo without prompting")
    args = parser.parse_args()

    if args.list:
        list_actions()
    elif args.last is not None:
        if args.last < 1:
            print("N must be at least 1.")
            return
        undo_last(args.last, dry_run=args.dry_run, yes=args.yes)
    else:
        # Default: undo last 1
        undo_last(1, dry_run=args.dry_run, yes=args.yes)

if __name__ == "__main__":
    main()
