"""Small append-only audit writer for agent activity."""

from datetime import datetime, timezone
import json
from pathlib import Path
from threading import Lock

AUDIT_PATH = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"
_LOCK = Lock()


def record(tool_name: str, args: object = None, result: object = None, stop_reason: str | None = None) -> None:
    """Append one safe, compact event without secrets or full message content."""
    def short(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).replace("\n", " ")
        return text[:240] + "…" if len(text) > 240 else text

    event = {
        "time": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "args": short(args),
        "result": short(result),
        "stop_reason": stop_reason,
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        try:
            history = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
            if not isinstance(history, list):
                history = []
        except (OSError, json.JSONDecodeError):
            history = []
        history.append(event)
        AUDIT_PATH.write_text(json.dumps(history, indent=2) + "\n")
