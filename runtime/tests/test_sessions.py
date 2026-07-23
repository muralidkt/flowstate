from pathlib import Path

import pytest

from flowstate.config import Settings
from flowstate.core.agent import SdkAgentBackend
from flowstate.core.sessions import SessionPointer, find_session_file
from flowstate.core.workspace import Workspace


def _make_session_file(claude_home: Path, session_id: str) -> Path:
    project_dir = claude_home / "projects" / "-some-encoded-cwd"
    project_dir.mkdir(parents=True)
    path = project_dir / f"{session_id}.jsonl"
    path.write_text('{"type":"user"}\n')
    return path


def _backend(tmp_path: Path) -> tuple[SdkAgentBackend, Workspace]:
    workspace = Workspace(tmp_path / "ws").ensure()
    # An explicit key pins session storage into the workspace, keeping the
    # guard tests off the developer's real ~/.claude.
    settings = Settings(
        workspace_dir=workspace.root,
        persona_path=tmp_path / "missing-persona.md",
        anthropic_api_key="test-key",
    )
    return SdkAgentBackend(settings, workspace), workspace


class TestFindSessionFile:
    def test_missing(self, tmp_path: Path) -> None:
        assert find_session_file(tmp_path, "abc") is None

    def test_found_regardless_of_cwd_encoding(self, tmp_path: Path) -> None:
        expected = _make_session_file(tmp_path, "abc")
        assert find_session_file(tmp_path, "abc") == expected

    def test_empty_id(self, tmp_path: Path) -> None:
        assert find_session_file(tmp_path, "") is None


class TestSessionPointer:
    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        assert SessionPointer(tmp_path).load() is None

    def test_round_trip(self, tmp_path: Path) -> None:
        pointer = SessionPointer(tmp_path)
        pointer.save("s-123")
        assert SessionPointer(tmp_path).load() == "s-123"

    def test_corrupted_state_returns_none(self, tmp_path: Path) -> None:
        (tmp_path / "conversation.json").write_text("{not json")
        assert SessionPointer(tmp_path).load() is None

    def test_conversations_are_independent(self, tmp_path: Path) -> None:
        SessionPointer(tmp_path, "a").save("s-a")
        SessionPointer(tmp_path, "b").save("s-b")
        assert SessionPointer(tmp_path, "a").load() == "s-a"
        assert SessionPointer(tmp_path, "b").load() == "s-b"


def _local_settings(tmp_path: Path, workspace: Workspace) -> Settings:
    return Settings(
        workspace_dir=workspace.root,
        persona_path=tmp_path / "missing-persona.md",
        anthropic_api_key=None,
        environment="local",
    )


def test_local_login_keeps_default_claude_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    workspace = Workspace(tmp_path / "ws").ensure()
    backend = SdkAgentBackend(_local_settings(tmp_path, workspace), workspace)
    assert backend._claude_home == Path.home() / ".claude"


def test_local_login_honors_inherited_config_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "custom-home"))
    workspace = Workspace(tmp_path / "ws").ensure()
    backend = SdkAgentBackend(_local_settings(tmp_path, workspace), workspace)
    assert backend._claude_home == tmp_path / "custom-home"


def test_workspace_resolves_relative_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert Workspace(Path("./.data")).root == tmp_path / ".data"


class TestResolveResumeGuard:
    def test_no_saved_session(self, tmp_path: Path) -> None:
        backend, _ = _backend(tmp_path)
        assert backend._resolve_resume(None, new_session=False) is None

    def test_saved_pointer_without_file_is_not_resumed(self, tmp_path: Path) -> None:
        backend, workspace = _backend(tmp_path)
        SessionPointer(workspace.state_dir).save("gone")
        assert backend._resolve_resume(None, new_session=False) is None

    def test_saved_pointer_with_file_resumes(self, tmp_path: Path) -> None:
        backend, workspace = _backend(tmp_path)
        SessionPointer(workspace.state_dir).save("s-1")
        _make_session_file(workspace.claude_home, "s-1")
        assert backend._resolve_resume(None, new_session=False) == "s-1"

    def test_new_session_ignores_existing(self, tmp_path: Path) -> None:
        backend, workspace = _backend(tmp_path)
        SessionPointer(workspace.state_dir).save("s-1")
        _make_session_file(workspace.claude_home, "s-1")
        assert backend._resolve_resume(None, new_session=True) is None

    def test_explicit_session_id_beats_pointer(self, tmp_path: Path) -> None:
        backend, workspace = _backend(tmp_path)
        SessionPointer(workspace.state_dir).save("s-pointer")
        _make_session_file(workspace.claude_home, "s-explicit")
        assert backend._resolve_resume("s-explicit", new_session=False) == "s-explicit"


def test_workspace_ensure_creates_all_dirs_idempotently(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "ws").ensure().ensure()
    for path in (
        workspace.claude_home,
        workspace.docs_dir,
        workspace.finance_dir,
        workspace.wiki_dir,
        workspace.repos_dir,
        workspace.audit_dir,
        workspace.state_dir,
    ):
        assert path.is_dir()
