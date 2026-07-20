# FlowState

Personal multi-agent assistant (bills/finance, GitHub repos, website) — Claude Agent SDK + FastAPI in a Cloudflare Container, Worker gateway, Telegram as primary interface, R2 persistence.

**Read before working:** `docs/PLAN.md` (architecture + phases, incl. §8 SDK hardening checklist) · `docs/STANDARDS.md` (coding/test/git standards — binding) · `docs/TASKS.md` (backlog).

## How work happens here

1. Pick the next `[ ]` task in the current phase of `docs/TASKS.md` (or the one the user names). Mark it `[~]`. **One task at a time.**
2. Stay inside the task's scope — its accept line is the contract. New ideas become new backlog tasks, not scope creep.
3. `just check` must pass before every commit (format, lint, types, CI-tier tests — no API key needed; the fake agent backend covers contract tests).
4. Commit with Conventional Commits + task ID (`feat(runtime): … [T0.4]`), check the task off in the same commit, push to `main`.
5. Definition of Done is in `docs/STANDARDS.md` §1 — all six points, every task.

## Non-negotiables (full list: STANDARDS.md §5)

- No secrets or real personal data anywhere in the repo — fixtures are synthetic.
- Allowlist-first tool policy; outward/destructive agent actions go through the approval gate; every tool call is audit-logged.
- Container runs non-root. Telegram webhook verifies the secret header before parsing and drops unknown chat IDs.
- Design changes (not just code) get a `docs/PLAN.md` decision-log row.

## Layout

- `runtime/` — Python 3.12 (uv): FastAPI + Agent SDK. `app/` routers · `core/` agent/checkpoint/approvals · `channels/` Telegram etc. · `tools/` MCP tools · `.claude/` persona + skills (no-overlap rule).
- `gateway/` — TypeScript Worker (Hono, Biome, vitest): auth, webhook, SSE pass-through, cron.
- `infra/` — Terraform platform layer (R2 bucket, Access, DNS). Manual applies; never holds secrets.
- `docs/` — plan, standards, tasks.

Built from-scratch; external systems we studied are inspiration only — never copy their code.
