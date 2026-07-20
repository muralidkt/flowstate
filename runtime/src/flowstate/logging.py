"""Structured logging: concise console format locally, JSON lines in production.

Fields passed via ``logger.info(..., extra={...})`` are emitted as top-level JSON keys.
Never log secrets or full document contents (STANDARDS.md §3).
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from flowstate.config import Settings

# Attributes present on every LogRecord — anything else came in via `extra`.
_RESERVED_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {"taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update({k: v for k, v in record.__dict__.items() if k not in _RESERVED_ATTRS})
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    if settings.environment == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s — %(message)s")
        )
    # force=True: create_app() may run several times in one process (tests).
    logging.basicConfig(level=settings.log_level.upper(), handlers=[handler], force=True)
