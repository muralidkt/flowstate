"""Agent backends: the real Claude Agent SDK backend behind a small protocol.

The SDK read loop must never block on a slow consumer (PLAN.md §8): run_turn
drains SDK messages into an unbounded in-process queue as fast as they arrive;
the caller (SSE writer, Telegram sender) consumes at its own pace.
"""

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Protocol

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from flowstate.config import Settings
from flowstate.core.events import WireEvent
from flowstate.core.translator import TurnState, translate_sdk_message

logger = logging.getLogger(__name__)

# Allowlist-first (STANDARDS.md §5): read-only until the approval gate lands (T5.1).
_ALLOWED_TOOLS = ["Read", "Grep", "Glob"]


class AgentBackend(Protocol):
    def run_turn(self, prompt: str, *, session_id: str | None = None) -> AsyncIterator[WireEvent]:
        """Run one conversation turn, yielding wire events as they happen."""
        ...


class SdkAgentBackend:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _options(self) -> ClaudeAgentOptions:
        env: dict[str, str] = {}
        if self._settings.anthropic_api_key:
            env["ANTHROPIC_API_KEY"] = self._settings.anthropic_api_key
        return ClaudeAgentOptions(
            model=self._settings.agent_model,
            tools=list(_ALLOWED_TOOLS),
            allowed_tools=list(_ALLOWED_TOOLS),
            max_turns=self._settings.agent_max_turns,
            include_partial_messages=True,  # token streaming (PLAN.md §8)
            setting_sources=[],  # fully explicit config; "project" arrives with T0.5 persona
            env=env,
            stderr=_log_cli_stderr,
        )

    async def run_turn(
        self, prompt: str, *, session_id: str | None = None
    ) -> AsyncIterator[WireEvent]:
        queue: asyncio.Queue[WireEvent | Exception | None] = asyncio.Queue()
        state = TurnState()

        async def drain(client: ClaudeSDKClient) -> None:
            try:
                async for message in client.receive_response():
                    for event in translate_sdk_message(message, state):
                        queue.put_nowait(event)
            except Exception as exc:  # surfaced to the consumer below, never swallowed
                queue.put_nowait(exc)
            finally:
                queue.put_nowait(None)

        async with ClaudeSDKClient(options=self._options()) as client:
            await client.query(prompt, session_id=session_id or "default")
            drain_task = asyncio.create_task(drain(client))
            try:
                while (item := await queue.get()) is not None:
                    if isinstance(item, Exception):
                        raise item
                    yield item
            finally:
                if not drain_task.done():
                    drain_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await drain_task


def _log_cli_stderr(line: str) -> None:
    # Without this callback SDK failures surface as useless placeholders (PLAN.md §8).
    logger.warning("[claude-cli] %s", line)
