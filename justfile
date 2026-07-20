# FlowState task runner — `just check` is the single gate; CI runs exactly this (STANDARDS.md §6)

default: check

# Format check + lint + types + tests. Gateway/infra checks are appended when those exist (T1.1/T1.3).
check:
    cd runtime && uv run ruff format --check .
    cd runtime && uv run ruff check .
    cd runtime && uv run mypy
    cd runtime && uv run pytest

# Auto-fix formatting and lint
fmt:
    cd runtime && uv run ruff format .
    cd runtime && uv run ruff check --fix .

# CI-tier tests only
test:
    cd runtime && uv run pytest

# Run the runtime locally (app factory arrives with T0.3)
dev:
    cd runtime && uv run uvicorn flowstate.app.main:create_app --factory --reload

# Manual real-key smoke conversation (arrives with T0.4)
smoke:
    @echo "smoke: not yet implemented — lands with T0.4 (agent core)"

# Deploy (normally CI's job; arrives with T1.5)
deploy:
    @echo "deploy: not yet implemented — lands with T1.5 (first deploy)"
