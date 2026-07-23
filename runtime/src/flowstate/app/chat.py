"""Streaming chat endpoint: wire events over SSE."""

import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from flowstate.core.agent import AgentBackend
from flowstate.core.events import TurnError, WireEvent

router = APIRouter()
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None
    new_session: bool = False


def format_sse(event: WireEvent) -> str:
    return f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"


@router.post("/chat")
async def chat(request: Request, body: ChatRequest) -> StreamingResponse:
    backend: AgentBackend = request.app.state.agent_backend

    async def stream() -> AsyncIterator[str]:
        try:
            async for event in backend.run_turn(
                body.message, session_id=body.session_id, new_session=body.new_session
            ):
                yield format_sse(event)
        except Exception:
            logger.exception("agent turn failed")
            yield format_sse(TurnError(message="agent turn failed — see server logs"))

    return StreamingResponse(stream(), media_type="text/event-stream")
