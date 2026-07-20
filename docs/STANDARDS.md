# FlowState — Engineering Standards

*Every task follows this document. If a task needs to break a rule, the task notes must say why.*

## 1. Workflow

- **Backlog:** `docs/TASKS.md` is the single source of truth. One task in progress at a time (`[~]`). A task is picked from the top of the current phase unless there's a stated reason to jump.
- **Trunk-based:** work lands on `main`, which must always pass `just check` and stay deployable. Use a short-lived branch + PR only for risky/large changes (schema changes, security-touching code).
- **Definition of Done** (applies to *every* task):
  1. Code complete and self-reviewed; follows this document.
  2. `just check` passes (format, lint, types, tests).
  3. New logic has tests (see §4 for which tier).
  4. Docs touched if behavior changed (`PLAN.md` decision log for design changes; `README` for user-facing changes).
  5. Task checked off in `TASKS.md` **in the same commit**.
  6. Conventional commit pushed (see §2).
- **Scope discipline:** a task does what its acceptance line says — no drive-by refactors, no speculative abstractions. File a new task instead.

## 2. Git conventions

- **Conventional Commits** with the task ID: `type(scope): summary [T1.2]`
  - `type`: `feat` | `fix` | `docs` | `test` | `refactor` | `chore` | `infra`
  - `scope`: `runtime` | `gateway` | `infra` | `docs` | `ci`
  - Example: `feat(runtime): stream agent events over SSE [T0.4]`
- Commits are small and coherent; the repo builds at every commit. No `wip` commits on `main`.
- Never commit: secrets, `.env`, Terraform state, real bank statements or any real personal data (fixtures are synthetic — see §5).

## 3. Code standards

### Python (`runtime/`)
- Python **3.12**, managed with **uv** (`pyproject.toml` + committed `uv.lock`).
- **ruff** for lint *and* format (line length 100); **mypy** on our code (no untyped defs). Both run in `just check`.
- **Pydantic v2** models at every boundary (API requests/responses, wire events, config). Config via `pydantic-settings` from env — no hand-rolled `os.environ` reads outside `config.py`.
- Layout: `app/` (FastAPI routers — thin, no business logic) · `core/` (agent service, checkpointing, approvals, cost ledger) · `channels/` (Telegram + future adapters behind one interface) · `tools/` (in-process MCP tools).
- Async-first; never block the event loop (file/network I/O in async form or a thread offload).
- **Error handling:** no bare/silent `except`. Catch specific exceptions; every caught error is either handled meaningfully or logged with context and re-raised. Errors that end a turn must still emit a terminal event to the user.
- Logging: stdlib `logging`, structured (key=value / JSON in the container). Never log secrets or full document contents.
- Comments explain *constraints and why*, not what the next line does. Match density of surrounding code.

### TypeScript (`gateway/`)
- `strict: true`. **Biome** for lint + format (one tool). **vitest** with the Workers pool for tests.
- Hono for routing. The Worker stays thin: verify, authorize, route, stream — no business logic.
- No `any` in our code; wrangler-generated types for bindings.

### Terraform (`infra/`)
- `terraform fmt` + `validate` clean. `prevent_destroy` on every stateful resource (R2 bucket).
- No secrets in variables or state; remote state only (never committed).
- One resource domain per file (`r2.tf`, `access.tf`, `dns.tf`).

### Agent assets (`runtime/.claude/`)
- **No-overlap rule:** every instruction lives in exactly one place — `CLAUDE.md` (persona) for always-relevant, a skill for situational. Duplicated guidance is a bug.
- Skills: one directory per skill, `SKILL.md` with frontmatter `name` + `description` (the description is the trigger — write it as "Use when …").
- Prompt/skill changes are code: same review bar, and where feasible a regression check (see contract tests).

## 4. Test pattern

Four tiers — every task states which tiers it touches:

| Tier | What | Runs | Needs API key? |
|---|---|---|---|
| **Unit** | Pure logic: event translator, resume guard, checkpoint diffing, approval gate, chunking | `just test`, CI | No |
| **Contract** | End-to-end through FastAPI with the **fake agent backend** (deterministic, LLM-free implementation of the same `AgentBackend` interface) | `just test`, CI | No |
| **Golden** | Ingestion: synthetic statement fixture in → expected SQLite rows out (byte-stable) | `just test`, CI | No |
| **Smoke** | One real conversation with tool use against the live SDK | `just smoke`, manual | Yes (local only) |

Rules:
- CI never needs `ANTHROPIC_API_KEY`. The fake backend makes that possible — keep it faithful to the real interface.
- Security-critical paths have **explicit denial tests**: webhook with wrong secret → 403; unknown chat ID → dropped; unapproved risky tool → never executes; approval timeout → deny.
- Tests live in `runtime/tests/` and `gateway/test/`, named after the module under test. Fixtures in `tests/fixtures/` — synthetic only.
- Don't chase coverage numbers; the critical-path list above must be covered.

## 5. Security non-negotiables

- Container runs as a **non-root** user.
- Secrets exist only as env vars (`wrangler secret` / local `.env`); never in code, prompts, logs, Terraform, or test fixtures.
- All test data is **synthetic** — never a real statement, account number, or token, even redacted.
- Tool policy is **allowlist-first**; anything outward or destructive goes through the approval gate. New tools default to gated.
- Every tool call is written to the append-only audit log.
- The Telegram webhook route validates the secret header **before** parsing the body and drops non-allowlisted chat IDs silently.

## 6. Tooling entry points

A `justfile` at the repo root is the single interface (created in T0.2; keep it current):

```
just check     # format-check + lint + types + all CI-tier tests (runtime + gateway + infra fmt)
just test      # unit + contract + golden tests
just dev       # run runtime locally (uvicorn, fake or real backend via env)
just smoke     # manual real-key smoke conversation
just deploy    # wrangler deploy (normally CI's job)
```

If a check isn't in `just check`, it doesn't exist — CI runs exactly `just check`.
