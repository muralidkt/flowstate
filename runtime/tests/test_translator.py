from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from flowstate.core import events
from flowstate.core.translator import _PREVIEW_CHARS, TurnState, translate_sdk_message


def _text_delta_event(text: str) -> StreamEvent:
    return StreamEvent(
        uuid="u1",
        session_id="s1",
        event={"type": "content_block_delta", "delta": {"type": "text_delta", "text": text}},
    )


def _result_message(**overrides: object) -> ResultMessage:
    defaults: dict[str, object] = {
        "subtype": "success",
        "duration_ms": 1200,
        "duration_api_ms": 900,
        "is_error": False,
        "num_turns": 2,
        "session_id": "s1",
        "total_cost_usd": 0.0123,
        "result": "done",
    }
    defaults.update(overrides)
    return ResultMessage(**defaults)  # type: ignore[arg-type]


def test_text_deltas_stream_through() -> None:
    state = TurnState()
    out = translate_sdk_message(_text_delta_event("hel"), state)
    out += translate_sdk_message(_text_delta_event("lo"), state)
    assert out == [events.TextDelta(text="hel"), events.TextDelta(text="lo")]
    assert state.emitted_text_via_stream


def test_assistant_text_suppressed_after_streaming() -> None:
    state = TurnState()
    translate_sdk_message(_text_delta_event("hello"), state)
    out = translate_sdk_message(
        AssistantMessage(content=[TextBlock(text="hello")], model="m"), state
    )
    assert out == []


def test_assistant_text_emitted_when_not_streamed() -> None:
    out = translate_sdk_message(
        AssistantMessage(content=[TextBlock(text="hello")], model="m"), TurnState()
    )
    assert out == [events.TextDelta(text="hello")]


def test_partial_tool_input_ignored_and_tool_call_deduped() -> None:
    state = TurnState()
    partial = StreamEvent(
        uuid="u1",
        session_id="s1",
        event={
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": '{"pa'},
        },
    )
    assert translate_sdk_message(partial, state) == []

    block = ToolUseBlock(id="t1", name="Read", input={"file_path": "/x"})
    message = AssistantMessage(content=[block], model="m")
    first = translate_sdk_message(message, state)
    assert first == [
        events.ToolCall(tool_id="t1", tool_name="Read", tool_input={"file_path": "/x"})
    ]
    assert translate_sdk_message(message, state) == []


def test_tool_result_preview_truncated() -> None:
    block = ToolResultBlock(tool_use_id="t1", content="x" * 1000)
    out = translate_sdk_message(UserMessage(content=[block]), TurnState())
    assert isinstance(out[0], events.ToolResult)
    assert out[0].tool_id == "t1"
    assert not out[0].is_error
    assert len(out[0].preview) == _PREVIEW_CHARS


def test_user_prompt_string_ignored() -> None:
    assert translate_sdk_message(UserMessage(content="hi"), TurnState()) == []


def test_result_message_maps_turn_end() -> None:
    state = TurnState()
    out = translate_sdk_message(_result_message(), state)
    assert out == [
        events.TurnEnd(
            session_id="s1",
            is_error=False,
            cost_usd=0.0123,
            duration_ms=1200,
            num_turns=2,
            result="done",
        )
    ]
    assert state.session_id == "s1"


def test_system_message_ignored() -> None:
    assert translate_sdk_message(SystemMessage(subtype="init", data={}), TurnState()) == []


def test_assistant_error_surfaces() -> None:
    out = translate_sdk_message(
        AssistantMessage(content=[], model="m", error="rate_limit"), TurnState()
    )
    assert out == [events.TurnError(message="assistant error: rate_limit")]
