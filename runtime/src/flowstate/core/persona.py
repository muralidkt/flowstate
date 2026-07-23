"""Load the FlowState persona that is appended to the SDK's system prompt."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_persona(path: Path) -> str | None:
    try:
        text = path.read_text().strip()
    except OSError:
        logger.warning("persona file missing at %s — running without persona", path)
        return None
    return text or None
