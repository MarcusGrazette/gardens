import json
from datetime import date, datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / ".data"
USER_FILE = DATA_DIR / "user.json"


def _ensure_dir():
    DATA_DIR.mkdir(exist_ok=True)


def load_user() -> dict | None:
    if not USER_FILE.exists():
        return None
    return json.loads(USER_FILE.read_text())


def save_user(user: dict) -> None:
    _ensure_dir()
    USER_FILE.write_text(json.dumps(user, indent=2))


def create_user(postcode: str, location: dict) -> dict:
    user = {
        "postcode": postcode,
        "location": location,
        "garden": {
            "orientation": None,
            "shade": None,
            "soil_type": None,
            "plants": [],
            "experience_level": None,
        },
        "tasks": {},
        "history": [],
        "created_at": datetime.now().isoformat(),
    }
    save_user(user)
    return user


def current_week() -> str:
    return date.today().strftime("%G-W%V")


def get_task_state(user: dict) -> dict:
    return user.get("tasks", {}).get(current_week(), {})


def set_task_status(user: dict, priority: int, status: str | None) -> dict:
    week = current_week()
    if "tasks" not in user:
        user["tasks"] = {}
    if week not in user["tasks"]:
        user["tasks"][week] = {}

    if status is None:
        user["tasks"][week].pop(str(priority), None)
    else:
        user["tasks"][week][str(priority)] = status

    save_user(user)
    return user


def update_history(user: dict, done: int, total: int) -> dict:
    week = current_week()
    if "history" not in user:
        user["history"] = []

    idx = next((i for i, h in enumerate(user["history"]) if h["week"] == week), None)
    entry = {"week": week, "done": done, "total": total}
    if idx is not None:
        user["history"][idx] = entry
    else:
        user["history"].append(entry)

    if len(user["history"]) > 8:
        user["history"] = user["history"][-8:]

    save_user(user)
    return user


def delete_user() -> None:
    if USER_FILE.exists():
        USER_FILE.unlink()
