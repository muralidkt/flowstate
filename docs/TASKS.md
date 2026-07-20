# FlowState — Task Backlog

*Source of truth for work. Legend: `[ ]` todo · `[~]` in progress (max one) · `[x]` done. Every task follows `docs/STANDARDS.md`; phase exit criteria live in `docs/PLAN.md` §10. Check tasks off in the same commit that completes them.*

## Phase 0 — Core loop, local

- [x] **T0.1 Repo bootstrap** — README stub, `.gitignore`, initial commit of docs; GitHub repo (`muralidkt/flowstate`, pre-created) wired and pushed.
  *Accept: `git push` works; docs visible on GitHub. Note: repo visibility currently public — decision pending (recommend private).*
- [x] **T0.2 Dev tooling (runtime)** — uv project in `runtime/`, ruff + mypy (strict) + pytest wired, root `justfile` (`check`/`fmt`/`test`/`dev`/`smoke`/`deploy`).
  *Accept: `just check` passes on an empty skeleton. ✓ (format+lint+types+1 test green)*
- [x] **T0.3 Runtime skeleton** — FastAPI app factory, `/healthz`, `pydantic-settings` config (`FLOWSTATE_*` env prefix), structured logging (console local / JSON prod).
  *Accept: `just dev` serves `/healthz`; contract test green. ✓ (live curl verified; 4 tests)*
- [ ] **T0.4 Agent core** — `AgentBackend` interface + real SDK backend (`ClaudeSDKClient`, options per PLAN §8: `setting_sources`, `include_partial_messages`, `stderr` cb), drain-fast event queue, SDK→wire event translator, SSE `POST /chat`.
  *Accept: unit tests for translator; manual real-key chat streams locally.*
- [ ] **T0.5 Persona + sessions** — `runtime/.claude/CLAUDE.md` persona, `./.data` workspace bootstrap, session continuity (session-id state file, JSONL copy at turn end, resume-only-if-exists guard).
  *Accept: two `just dev` restarts continue one conversation; guard unit-tested.*
- [ ] **T0.6 Fake backend + contract tests** — deterministic LLM-free `AgentBackend`; contract tests for `/chat` (stream shape, multi-turn, error turn).
  *Accept: full test suite green with no API key.*
- [ ] **T0.7 Turn hardening** — setup + turn hard timeouts, ~1 s partial flush, per-turn cost capture → ledger JSONL.
  *Accept: timeout paths emit terminal error events (unit-tested); ledger row per turn.*
- **Phase exit:** multi-turn conversation with tool use via `curl -N localhost:8000/chat`.

## Phase 1 — Deployed core

- [ ] **T1.1 Terraform bootstrap** — `infra/` (provider, remote state, R2 bucket w/ `prevent_destroy` + versioning, Access app + policy, DNS record). Needs: domain choice.
  *Accept: `terraform apply` idempotent; Access challenge appears on the hostname.*
- [ ] **T1.2 Container image** — multi-stage Dockerfile, non-root user, Python + git + gh + sqlite, pinned SDK.
  *Accept: local `docker run` serves `/chat` identically to `just dev`.*
- [ ] **T1.3 Gateway scaffold** — Hono Worker, `wrangler.jsonc` (DO + container + R2 bindings), shared-secret auth to container, SSE pass-through; Biome + vitest tooling.
  *Accept: `wrangler dev` proxies chat to local container; auth denial test.*
- [ ] **T1.4 R2 persistence** — workspace checkpoint/restore module (turn-boundary sync, atomic writes), sessions + ledger + audit included; boot-time restore.
  *Accept: round-trip test (checkpoint → wipe → restore → identical); container restart keeps conversation.*
- [ ] **T1.5 First deploy** — `wrangler secret` set, deploy to workers.dev/domain, minimal debug chat page behind Access.
  *Accept: phone-browser chat through Access; cold + warm turn timed and noted in PLAN.*
- [ ] **T1.6 CI** — GitHub Actions: `just check` on PRs/main; `wrangler deploy` on main.
  *Accept: a trivial PR runs checks; merge deploys.*
- **Phase exit:** chat from phone; yesterday's conversation survives container restart.

## Phase 2 — Telegram daily driver

- [ ] **T2.1 Webhook route** — bot registration (manual, BotFather), `/webhook/telegram` in gateway: secret-header verify → chat-ID allowlist → fast ack → forward; `setWebhook` script.
  *Accept: denial tests (bad secret 403, unknown chat dropped); echo path works.*
- [ ] **T2.2 Telegram adapter** — channel interface in runtime; async dispatch, typing indicator loop, 4096-char chunking, MarkdownV2-safe rendering, error replies.
  *Accept: real bot conversation e2e; chunking unit-tested.*
- [ ] **T2.3 Commands** — `/new`, `/model sonnet|opus`, `/status` (session, spend this month), `/help`.
  *Accept: contract tests via fake backend.*
- [ ] **T2.4 File intake** — document/photo download → R2 `docs/` → workspace mirror → confirmation message.
  *Accept: send a PDF, ask a question about it, get a grounded answer.*
- [ ] **T2.5 `notify` tool** — in-process MCP tool the agent (and later cron) uses to message you.
  *Accept: agent-initiated Telegram message arrives; tool allowlisted read-only-safe.*
- **Phase exit (core-assistant milestone):** FlowState is a Telegram chat you use daily.

## Phase 3 — Wiki memory

- [ ] **T3.1 Wiki scaffold** — `/data/wiki` structure + `INDEX.md`, inner git repo, commit-per-edit; conventions added to persona (consult-before-answer, update-in-place, facts-not-instructions).
  *Accept: told a fact → page updated + committed; next session uses it.*
- [ ] **T3.2 Wiki behavior checks** — contract tests with fake backend for the update flow; smoke checklist for retrieval quality.
  *Accept: suite green; smoke notes recorded in task.*

## Phase 4 — Finance specialist

- [ ] **T4.1 Finance store** — SQLite schema (transactions, accounts, categories, `source_doc`), `finance_sql` MCP tool (read-only query + guarded ingestion upsert).
  *Accept: unit tests incl. SQL injection-shaped inputs rejected.*
- [ ] **T4.2 Ingestion** — `finance` subagent (minimal tools per PLAN §4), `ingest-statement` skill, synthetic golden fixtures (2 bank formats + 1 bill).
  *Accept: golden tests byte-stable; a real month ingested locally.*
- [ ] **T4.3 Spend answers** — `spend-report` skill, citation convention (answers reference `source_doc`).
  *Accept: "groceries in June?" correct over Telegram with citations.*

## Phase 5 — GitHub specialist + approvals

- [ ] **T5.1 Approval core** — `can_use_tool` → pending-approval record → resolution future, default-deny timeout; audit-log hook on **all** tool calls.
  *Accept: unapproved risky tool never executes (contract test); timeout denies; audit rows written.*
- [ ] **T5.2 Telegram approval UX** — inline Approve/Deny buttons, callback handling, result echo.
  *Accept: e2e approve and deny paths against fake backend + one real run.*
- [ ] **T5.3 Repo subagent** — `gh` + fine-grained PATs (RO default; RW gated), `repo-actions` skill (never push main), clone cache.
  *Accept: cross-repo Q&A; typo-fix → PR lands only after Approve tap (sandbox repo).*

## Phase 6 — Website agent

- [ ] **T6.1 Website subagent** — scope Phase-5 machinery to the website repo + `deploy-site` skill. Needs: website repo/host details.
  *Accept: approved content change live on the site.*

## Phase 7 — Automation & workbench

- [ ] **T7.1 Weekly digest** — cron trigger → digest job (spend + repo activity) → `notify`.
- [ ] **T7.2 Email-in ingestion** — Cloudflare Email Routing → Worker → R2 → auto-ingest pipeline.
- [ ] **T7.3 Wiki gardener** — scheduled dedupe/prune/contradiction pass with report.
- [ ] **T7.4 Workbench UI v1** — approvals detail, spend table, audit view, wiki browser (behind Access).
- [ ] **T7.5 Budget guard polish** — monthly cap enforcement + `/status` breakdown + override command.

---

*Adding work: append a task to the right phase with an accept line — don't grow an existing task's scope. Mirroring to GitHub Issues can come later if this file stops being enough.*
