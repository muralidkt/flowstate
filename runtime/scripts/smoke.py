"""Manual real-key smoke: one real conversation turn through the SDK backend.

Usage: just smoke ["your prompt"]
Requires Claude credentials — a local Claude Code login or ANTHROPIC_API_KEY
(shell env or runtime/.env). Never run in CI (STANDARDS.md §4).
"""

import asyncio
import sys

from flowstate.config import get_settings
from flowstate.core import events
from flowstate.core.agent import SdkAgentBackend


async def main() -> int:
    prompt = " ".join(sys.argv[1:]) or (
        "In one sentence: which files exist in your current directory? Use your tools."
    )
    backend = SdkAgentBackend(get_settings())
    async for event in backend.run_turn(prompt):
        match event:
            case events.TextDelta(text=text):
                print(text, end="", flush=True)
            case events.ToolCall(tool_name=name):
                print(f"\n[tool: {name}]", flush=True)
            case events.ToolResult(is_error=is_error):
                print(f"[tool {'failed' if is_error else 'done'}]", flush=True)
            case events.TurnEnd() as end:
                cost = f"${end.cost_usd:.4f}" if end.cost_usd is not None else "n/a"
                print(f"\n— session={end.session_id} cost={cost} turns={end.num_turns}")
            case events.TurnError(message=message):
                print(f"\nERROR: {message}")
                return 1
            case _:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
