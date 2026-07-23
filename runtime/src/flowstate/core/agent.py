"""Agent backends: the real Claude Agent SDK backend behind a small protocol.

The SDK read loop must never block on a slow consumer (PLAN.md §8): run_turn
drains SDK messages into an unbounded in-process queue as fast as they arrive;
the caller (SSE writer, Telegram sender) consumes at its own pace.
"""

import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from claude_agent_sdk.types import SystemPromptPreset

from flowstate.config import Settings
from flowstate.core.events import TurnEnd, WireEvent
from flowstate.core.persona import load_persona
from flowstate.core.sessions import SessionPointer, find_session_file
from flowstate.core.translator import TurnState, translate_sdk_message
from flowstate.core.workspace import Workspace

logger = logging.getLogger(__name__)

# Allowlist-first (STANDARDS.md §5): read-only until the approval gate lands (T5.1).
_ALLOWED_TOOLS = ["Read", "Grep", "Glob"]


class AgentBackend(Protocol):
    def run_turn(
        self, prompt: str, *, session_id: str | None = None, new_session: bool = False
    ) -> AsyncIterator[WireEvent]:
        """Run one conversation turn, yielding wire events as they happen."""
        ...


def _effective_claude_home(settings: Settings, workspace: Workspace) -> Path:
    """Where the SDK keeps session files.

    Pinned inside the workspace when auth is self-contained (API key set, or
    production — where the key is mandatory), making sessions durable by
    construction. With a local subscription login the CLI must keep its
    default config dir: relocating it orphans the stored credentials and the
    CLI reports "Not logged in".
    """
    if settings.anthropic_api_key or settings.environment == "production":
        return workspace.claude_home
    # Respect an inherited CLAUDE_CONFIG_DIR (e.g. a ~/.claude-personal setup);
    # the CLI subprocess inherits it too, so sessions land there.
    inherited = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(inherited) if inherited else Path.home() / ".claude"


class SdkAgentBackend:
    def __init__(self, settings: Settings, workspace: Workspace) -> None:
        self._settings = settings
        self._workspace = workspace
        self._claude_home = _effective_claude_home(settings, workspace)
        self._pointer = SessionPointer(workspace.state_dir)
        self._persona = load_persona(settings.persona_path)

    def _resolve_resume(self, session_id: str | None, new_session: bool) -> str | None:
        if new_session:
            return None
        candidate = session_id or self._pointer.load()
        if candidate is None:
            return None
        if find_session_file(self._claude_home, candidate) is None:
            # Resume-only-if-exists guard (PLAN.md §8): a missing session file
            # makes the CLI exit silently mid-init.
            logger.warning("session %s has no local file — starting fresh", candidate)
            return None
        return candidate

    def _options(self, resume: str | None) -> ClaudeAgentOptions:
        # One memory system, not two (PLAN.md §5): the wiki is FlowState's
        # durable memory; the CLI's auto-memory would compete with it.
        env: dict[str, str] = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
        if self._claude_home == self._workspace.claude_home:
            env["CLAUDE_CONFIG_DIR"] = str(self._claude_home)
        if self._settings.anthropic_api_key:
            env["ANTHROPIC_API_KEY"] = self._settings.anthropic_api_key
        # Static system prompt (no cwd listing / git status) keeps the prompt
        # cacheable across turns; the persona carries the workspace map instead.
        system_prompt: SystemPromptPreset = {
            "type": "preset",
            "preset": "claude_code",
            "exclude_dynamic_sections": True,
        }
        if self._persona:
            system_prompt["append"] = self._persona
        return ClaudeAgentOptions(
            model=self._settings.agent_model,
            system_prompt=system_prompt,
            cwd=str(self._workspace.root),
            resume=resume,
            tools=list(_ALLOWED_TOOLS),
            allowed_tools=list(_ALLOWED_TOOLS),
            max_turns=self._settings.agent_max_turns,
            include_partial_messages=True,  # token streaming (PLAN.md §8)
            setting_sources=[],  # fully explicit config; skills opt in later (T3.x)
            env=env,
            stderr=_log_cli_stderr,
        )

    async def run_turn(
        self, prompt: str, *, session_id: str | None = None, new_session: bool = False
    ) -> AsyncIterator[WireEvent]:
        resume = self._resolve_resume(session_id, new_session)
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

        async with ClaudeSDKClient(options=self._options(resume)) as client:
            await client.query(prompt)
            drain_task = asyncio.create_task(drain(client))
            try:
                while (item := await queue.get()) is not None:
                    if isinstance(item, Exception):
                        raise item
                    yield item
                    if isinstance(item, TurnEnd) and not item.is_error:
                        # The SDK may rotate ids — always save the one reported
                        # at turn end (PLAN.md §8).
                        self._pointer.save(item.session_id)
            finally:
                if not drain_task.done():
                    drain_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await drain_task


def _log_cli_stderr(line: str) -> None:
    # Without this callback SDK failures surface as useless placeholders (PLAN.md §8).
    logger.warning("[claude-cli] %s", line)
