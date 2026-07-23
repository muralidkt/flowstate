"""Session continuity: which SDK session a conversation resumes.

The resume-only-if-the-file-exists guard matters (PLAN.md §8): passing
``resume`` for a session whose JSONL is missing makes the CLI exit silently
mid-init, and the user sees nothing.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_FILE = "conversation.json"


def find_session_file(claude_home: Path, session_id: str) -> Path | None:
    """Locate a session JSONL under any project dir — deliberately agnostic to
    the CLI's cwd-encoding scheme, which is not a documented contract."""
    if not session_id:
        return None
    matches = list(claude_home.glob(f"projects/*/{session_id}.jsonl"))
    return matches[0] if matches else None


class SessionPointer:
    """Persists the current session id per conversation.

    Single ``default`` conversation until the Telegram channel lands (T2.x);
    the SDK may rotate session ids, so callers must save the id reported at
    turn end, not the one they resumed with.
    """

    def __init__(self, state_dir: Path, conversation: str = "default") -> None:
        self._path = state_dir / _STATE_FILE
        self._conversation = conversation

    def load(self) -> str | None:
        try:
            data = json.loads(self._path.read_text())
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, OSError):
            logger.warning("unreadable conversation state at %s — starting fresh", self._path)
            return None
        value = data.get(self._conversation)
        return value if isinstance(value, str) and value else None

    def save(self, session_id: str) -> None:
        try:
            data = json.loads(self._path.read_text())
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            data = {}
        data[self._conversation] = session_id
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(self._path)
