# FlowState

Private personal AI assistant — multi-agent, built on the Claude Agent SDK + FastAPI, deployed serverless on Cloudflare (Container + Worker + R2), used daily through Telegram. Answers questions about bills/bank statements, personal GitHub repos, and the personal website; takes gated actions (PRs, deploys) only with explicit approval.

**Status:** building — currently Phase 0 (local core loop).

| Doc | Purpose |
|---|---|
| [`docs/PLAN.md`](docs/PLAN.md) | Architecture, decision log, security model, phased roadmap |
| [`docs/STANDARDS.md`](docs/STANDARDS.md) | Coding/test/git standards — binding for every task |
| [`docs/TASKS.md`](docs/TASKS.md) | Task backlog with acceptance criteria |
| [`CLAUDE.md`](CLAUDE.md) | Working instructions for agent sessions (`AGENTS.md` symlinks here) |

## Layout

```
runtime/   Python 3.12 — FastAPI + Claude Agent SDK (the assistant)
gateway/   TypeScript — Cloudflare Worker (auth, Telegram webhook, routing)
infra/     Terraform — platform layer (R2 bucket, Access, DNS)
docs/      Plan, standards, backlog
```

## Development

Requires [`uv`](https://github.com/astral-sh/uv), Node 22+, and [`just`](https://github.com/casey/just).

```
just check   # format + lint + types + tests (what CI runs)
just dev     # run the runtime locally
```

Personal project — not open for external use; no real personal data is ever committed (see STANDARDS.md §5).
