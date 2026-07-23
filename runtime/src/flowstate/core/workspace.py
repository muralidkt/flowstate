"""The agent's persistent workspace (PLAN.md §6): all durable runtime state lives here.

Locally this is ``./.data`` (git-ignored — it will hold real personal data);
in the container it is restored from / checkpointed to R2 (T1.4).
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Workspace:
    root: Path

    def __post_init__(self) -> None:
        # Absolute by construction: relative paths handed to the CLI (cwd,
        # CLAUDE_CONFIG_DIR) get re-resolved against *its* cwd, silently
        # nesting directories like `.data/.data/`.
        object.__setattr__(self, "root", self.root.resolve())

    @property
    def claude_home(self) -> Path:
        """``CLAUDE_CONFIG_DIR`` — pinned inside the workspace so the SDK's session
        files (``projects/<encoded-cwd>/<session_id>.jsonl``) are durable by
        construction instead of needing a copy step out of ``~/.claude``."""
        return self.root / "claude-home"

    @property
    def docs_dir(self) -> Path:
        return self.root / "docs"

    @property
    def finance_dir(self) -> Path:
        return self.root / "finance"

    @property
    def wiki_dir(self) -> Path:
        return self.root / "wiki"

    @property
    def repos_dir(self) -> Path:
        return self.root / "repos"

    @property
    def audit_dir(self) -> Path:
        return self.root / "audit"

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    def ensure(self) -> "Workspace":
        for path in (
            self.root,
            self.claude_home,
            self.docs_dir,
            self.finance_dir,
            self.wiki_dir,
            self.repos_dir,
            self.audit_dir,
            self.state_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
        return self
