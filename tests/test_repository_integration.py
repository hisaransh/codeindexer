from pathlib import Path
import shutil
import subprocess

import pytest

from codeindex.repository.errors import NestedRepositoryPathError
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
