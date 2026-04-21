"""
User-defined sort rules engine for Autopilot.

Rules are stored as JSON in ~/Downloads/Autopilot/.rules.json and evaluated
by classifier.py as the highest-priority tier in the classification pipeline.

A rule has the shape:
    {
        "id": "uuid",
        "name": "PDFs to Documents",
        "enabled": true,
        "conditions": [
            {"field": "extension", "operator": "equals", "value": "pdf"}
        ],
        "action": {"type": "move_to", "target": "Documents"}
    }

Supported fields: filename, extension, path, mime_type, size
Supported operators: equals, contains, starts_with, ends_with, matches_regex,
                     greater_than, less_than

All conditions in a rule must match (AND logic). Rules are evaluated in order;
the first matching rule wins.
"""

import json
import re
import mimetypes
from pathlib import Path

RULES_PATH = Path.home() / "Downloads/Autopilot/.rules.json"


def load_rules() -> list:
    """Load rules from disk. Returns empty list if file missing or corrupt."""
    if not RULES_PATH.exists():
        return []
    try:
        with open(RULES_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_rules(rules: list):
    """Persist rules to disk, creating parent directories if needed."""
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RULES_PATH, "w") as f:
        json.dump(rules, f, indent=2)


def _get_file_value(file_path: Path, field: str):
    """Extract a comparable value from a file path for rule matching."""
    if field == "filename":
        return file_path.name
    elif field == "extension":
        return file_path.suffix.lstrip(".").lower()
    elif field == "path":
        return str(file_path)
    elif field == "mime_type":
        return mimetypes.guess_type(str(file_path))[0] or ""
    elif field == "size":
        try:
            return file_path.stat().st_size
        except Exception:
            return 0
    return ""


def _matches_condition(file_path: Path, condition: dict) -> bool:
    """Evaluate a single condition against a file path."""
    field = condition.get("field", "")
    operator = condition.get("operator", "")
    value = condition.get("value", "")
    actual = _get_file_value(file_path, field)

    # Normalize extension values: users often type ".pdf" but the engine stores "pdf"
    if field == "extension" and isinstance(value, str):
        value = value.lstrip(".")

    if operator == "equals":
        return str(actual).lower() == str(value).lower()
    elif operator == "contains":
        return str(value).lower() in str(actual).lower()
    elif operator == "starts_with":
        return str(actual).lower().startswith(str(value).lower())
    elif operator == "ends_with":
        return str(actual).lower().endswith(str(value).lower())
    elif operator == "matches_regex":
        try:
            return bool(re.search(value, str(actual)))
        except re.error:
            return False
    elif operator == "greater_than":
        try:
            return float(actual) > float(value)
        except (ValueError, TypeError):
            return False
    elif operator == "less_than":
        try:
            return float(actual) < float(value)
        except (ValueError, TypeError):
            return False
    return False


def test_rule(rule: dict, file_path: Path) -> bool:
    """Test a single rule against a file path. Returns False if disabled."""
    if not rule.get("enabled", True):
        return False
    conditions = rule.get("conditions", [])
    if not conditions:
        return True
    return all(_matches_condition(file_path, c) for c in conditions)


def match_file(file_path: Path):
    """
    Evaluate all saved rules against a file.
    Returns the target category string if matched, "Skip" for skip actions,
    or None if no rules matched.
    """
    rules = load_rules()
    for rule in rules:
        if test_rule(rule, file_path):
            action = rule.get("action", {})
            if action.get("type") == "move_to":
                return action.get("target", "Miscellaneous")
            elif action.get("type") == "skip":
                return "Skip"
    return None


def test_all_rules(file_path: Path) -> list:
    """Return a list of booleans indicating which saved rules match."""
    rules = load_rules()
    return [test_rule(r, file_path) for r in rules]


if __name__ == "__main__":
    # CLI interface used by the Rust backend for live rule testing.
    import sys
    if len(sys.argv) >= 4 and sys.argv[1] == "--test-each":
        rules_data = json.loads(sys.argv[2])
        file_path = Path(sys.argv[3])
        results = []
        for rule in rules_data:
            if not rule.get("enabled", True):
                results.append(False)
                continue
            conditions = rule.get("conditions", [])
            match = all(_matches_condition(file_path, c) for c in conditions) if conditions else True
            results.append(match)
        print(json.dumps(results))
    elif len(sys.argv) >= 4 and sys.argv[1] == "--test":
        rule_data = json.loads(sys.argv[2])
        file_path = Path(sys.argv[3])
        print("True" if test_rule(rule_data, file_path) else "False")
    elif len(sys.argv) >= 3 and sys.argv[1] == "--match":
        file_path = Path(sys.argv[2])
        result = match_file(file_path)
        print(result if result else "")
