from collections.abc import AsyncIterator

import httpx

from flowstate.app.chat import format_sse
from flowstate.app.main import create_app
from flowstate.core import events
from flowstate.core.events import WireEvent


class StubBackend:
    """Minimal stand-in; the full deterministic fake backend arrives with T0.6."""

    async def run_turn(
        self, prompt: str, *, session_id: str | None = None
    ) -> AsyncIterator[WireEvent]:
        yield events.TextDelta(text=f"echo:{prompt}")
        yield events.TurnEnd(session_id="s1", is_error=False)


def test_format_sse() -> None:
    assert (
        format_sse(events.TextDelta(text="hi"))
        == 'event: text_delta\ndata: {"type":"text_delta","text":"hi"}\n\n'
    )


async def test_chat_streams_wire_events_as_sse() -> None:
    app = create_app()
    app.state.agent_backend = StubBackend()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/chat", json={"message": "hi"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: text_delta" in response.text
    assert "echo:hi" in response.text
    assert "event: turn_end" in response.text


async def test_chat_rejects_empty_message() -> None:
    app = create_app()
    app.state.agent_backend = StubBackend()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/chat", json={"message": ""})
    assert response.status_code == 422
