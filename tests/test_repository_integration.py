from pathlib import Path
import shutil
import subprocess

import pytest

from codeindex.repository.discovery import (
    discover_files,
    summarize_discovery,
)
from codeindex.repository.errors import NestedRepositoryPathError
from codeindex.repository.models import (
    DiscoveredFile,
    SkipReason,
    SkippedFile,
)
from codeindex.repository.resolver import resolve_repository


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_real_git_root_detection_and_nested_path_rejection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository"
    subprocess.run(
        ["git", "init", str(repository_root)],
        capture_output=True,
        check=True,
        text=True,
    )
    nested_path = repository_root / "src"
    nested_path.mkdir()

    repository = resolve_repository(repository_root)

    assert repository.root == repository_root.resolve()
    with pytest.raises(NestedRepositoryPathError):
        resolve_repository(nested_path)

    monkeypatch.chdir(nested_path)
    with pytest.raises(NestedRepositoryPathError):
        resolve_repository(".")


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_real_git_discovery_uses_current_tracked_worktree(
    tmp_path: Path,
) -> None:
    repository_root = tmp_path / "repository"
    subprocess.run(
        ["git", "init", str(repository_root)],
        capture_output=True,
        check=True,
        text=True,
    )
    source_path = repository_root / "src" / "app.py"
    source_path.parent.mkdir()
    source_path.write_text("version = 'staged'\n", encoding="utf-8")
    (repository_root / ".gitignore").write_text(
        "ignored.py\n",
        encoding="utf-8",
    )
    deleted_path = repository_root / "deleted.py"
    deleted_path.write_text("deleted = False\n", encoding="utf-8")
    symlink_path = repository_root / "link.py"
    symlink_path.symlink_to(source_path)
    subprocess.run(
        ["git", "-C", str(repository_root), "add", "."],
        capture_output=True,
        check=True,
        text=True,
    )

    source_path.write_text("version = 'working-tree'\n", encoding="utf-8")
    deleted_path.unlink()
    (repository_root / "untracked.py").write_text(
        "untracked = True\n",
        encoding="utf-8",
    )
    (repository_root / "ignored.py").write_text(
        "ignored = True\n",
        encoding="utf-8",
    )

    repository = resolve_repository(repository_root)
    status_before = subprocess.run(
        ["git", "-C", str(repository_root), "status", "--porcelain=v1", "-z"],
        capture_output=True,
        check=True,
    ).stdout
    decisions = list(discover_files(repository))
    status_after = subprocess.run(
        ["git", "-C", str(repository_root), "status", "--porcelain=v1", "-z"],
        capture_output=True,
        check=True,
    ).stdout
    decisions_by_path = {
        decision.relative_path.as_posix(): decision
        for decision in decisions
    }

    assert isinstance(decisions_by_path["src/app.py"], DiscoveredFile)
    assert decisions_by_path["src/app.py"].text == "version = 'working-tree'\n"
    assert decisions_by_path["deleted.py"] == SkippedFile(
        Path("deleted.py"),
        SkipReason.DELETED,
    )
    assert decisions_by_path["link.py"] == SkippedFile(
        Path("link.py"),
        SkipReason.SYMLINK,
    )
    assert "untracked.py" not in decisions_by_path
    assert "ignored.py" not in decisions_by_path
    assert status_after == status_before

    summary = summarize_discovery(decisions)
    assert summary.candidate_count == 4
    assert summary.accepted_count == 2


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_real_git_discovery_skips_gitlink_entry(tmp_path: Path) -> None:
    repository_root = tmp_path / "repository"
    subprocess.run(
        ["git", "init", str(repository_root)],
        capture_output=True,
        check=True,
        text=True,
    )
    source_path = repository_root / "app.py"
    source_path.write_text("app = True\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repository_root), "add", "app.py"],
        capture_output=True,
        check=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository_root),
            "-c",
            "user.name=Codeindex Tests",
            "-c",
            "user.email=codeindex@example.invalid",
            "commit",
            "-m",
            "fixture",
        ],
        capture_output=True,
        check=True,
        text=True,
    )
    commit_id = subprocess.run(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        [
            "git",
            "-C",
            str(repository_root),
            "update-index",
            "--add",
            "--cacheinfo",
            f"160000,{commit_id},modules/dependency",
        ],
        capture_output=True,
        check=True,
        text=True,
    )

    decisions = list(discover_files(resolve_repository(repository_root)))

    assert SkippedFile(
        Path("modules/dependency"),
        SkipReason.SUBMODULE,
    ) in decisions
