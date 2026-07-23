"""Translate Claude Agent SDK messages into wire events.

Dedupe rules (unit-tested):
- streamed text deltas win — the assembled AssistantMessage text block is
  suppressed once any delta was emitted, so text is never sent twice
- partial tool-input deltas are ignored; tool_call is emitted once from the
  assembled ToolUseBlock so it always carries complete input
"""

from dataclasses import dataclass
from dataclasses import field as dc_field

from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    ServerToolUseBlock,
    StreamEvent,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from flowstate.core.events import (
    TextDelta,
    ThinkingDelta,
    ToolCall,
    ToolResult,
    TurnEnd,
    TurnError,
    WireEvent,
)

_PREVIEW_CHARS = 300


@dataclass
class TurnState:
    """Per-turn dedupe/bookkeeping threaded through the translator."""

    emitted_text_via_stream: bool = False
    seen_tool_ids: set[str] = dc_field(default_factory=set)
    session_id: str | None = None


def translate_sdk_message(message: object, state: TurnState) -> list[WireEvent]:
    if isinstance(message, StreamEvent):
        return _translate_stream_event(message, state)
    if isinstance(message, AssistantMessage):
        return _translate_assistant(message, state)
    if isinstance(message, UserMessage):
        return _translate_user(message)
    if isinstance(message, ResultMessage):
        state.session_id = message.session_id
        return [
            TurnEnd(
                session_id=message.session_id,
                is_error=message.is_error,
                cost_usd=message.total_cost_usd,
                duration_ms=message.duration_ms,
                num_turns=message.num_turns,
                result=message.result,
            )
        ]
    # SystemMessage and anything unknown carries no user-facing signal.
    return []


def _translate_stream_event(message: StreamEvent, state: TurnState) -> list[WireEvent]:
    state.session_id = message.session_id
    event = message.event
    if event.get("type") != "content_block_delta":
        return []
    delta = event.get("delta", {})
    if delta.get("type") == "text_delta":
        state.emitted_text_via_stream = True
        return [TextDelta(text=delta.get("text", ""))]
    if delta.get("type") == "thinking_delta":
        return [ThinkingDelta(text=delta.get("thinking", ""))]
    # input_json_delta et al.: wait for the assembled block instead.
    return []


def _translate_assistant(message: AssistantMessage, state: TurnState) -> list[WireEvent]:
    out: list[WireEvent] = []
    for block in message.content:
        if isinstance(block, TextBlock):
            if not state.emitted_text_via_stream:
                out.append(TextDelta(text=block.text))
        elif (
            isinstance(block, ToolUseBlock | ServerToolUseBlock)
            and block.id not in state.seen_tool_ids
        ):
            state.seen_tool_ids.add(block.id)
            out.append(
                ToolCall(
                    tool_id=block.id,
                    tool_name=block.name,
                    tool_input=block.input,
                    parent_tool_use_id=message.parent_tool_use_id,
                )
            )
    if message.error is not None:
        out.append(TurnError(message=f"assistant error: {message.error}"))
    return out


def _translate_user(message: UserMessage) -> list[WireEvent]:
    if isinstance(message.content, str):
        return []
    return [
        ToolResult(
            tool_id=block.tool_use_id,
            is_error=bool(block.is_error),
            preview=_preview(block.content),
        )
        for block in message.content
        if isinstance(block, ToolResultBlock)
    ]


def _preview(content: str | list[dict[str, object]] | None) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content[:_PREVIEW_CHARS]
    parts = [str(item.get("text", "")) for item in content if isinstance(item, dict)]
    return " ".join(p for p in parts if p)[:_PREVIEW_CHARS]
