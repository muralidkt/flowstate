"""Channel-agnostic wire events emitted by an agent turn.

The translator maps Claude Agent SDK messages onto these; channels (SSE now,
Telegram later) only ever render wire events, never SDK types.
"""

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field


class TextDelta(BaseModel):
    type: Literal["text_delta"] = "text_delta"
    text: str


class ThinkingDelta(BaseModel):
    type: Literal["thinking_delta"] = "thinking_delta"
    text: str


class ToolCall(BaseModel):
    type: Literal["tool_call"] = "tool_call"
    tool_id: str
    tool_name: str
    tool_input: dict[str, Any]
    parent_tool_use_id: str | None = None


class ToolResult(BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_id: str
    is_error: bool = False
    # Truncated result text — full tool output stays server-side; the wire stays light.
    preview: str = ""


class TurnEnd(BaseModel):
    type: Literal["turn_end"] = "turn_end"
    session_id: str
    is_error: bool
    cost_usd: float | None = None
    duration_ms: int | None = None
    num_turns: int | None = None
    result: str | None = None


class TurnError(BaseModel):
    type: Literal["error"] = "error"
    message: str


WireEvent = Annotated[
    TextDelta | ThinkingDelta | ToolCall | ToolResult | TurnEnd | TurnError,
    Field(discriminator="type"),
]
