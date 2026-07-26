from pathlib import Path, PurePosixPath
import subprocess

import pytest

import codeindex.repository.gitops as gitops_module
from codeindex.repository.errors import (
    GitUnavailableError,
    TrackedFilesInspectionError,
    TrackedFilesOutputError,
)
from codeindex.repository.gitops import list_tracked_files


def test_parses_deduplicates_and_byte_sorts_tracked_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    output = (
        b"100644 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 2\tzeta.py\0"
        b"100644 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 1\tzeta.py\0"
        b"100755 cccccccccccccccccccccccccccccccccccccccc 0\ta script.sh\0"
        b"100644 dddddddddddddddddddddddddddddddddddddddd 0\tline\nbreak.py\0"
    )
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=output,
        stderr=b"",
    )
    monkeypatch.setattr(
        gitops_module.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )

    tracked_files = list_tracked_files(tmp_path)

    assert [entry.relative_path for entry in tracked_files] == [
        PurePosixPath("a script.sh"),
        PurePosixPath("line\nbreak.py"),
        PurePosixPath("zeta.py"),
    ]
    assert tracked_files[-1].stage == 2


def test_prefers_stage_zero_when_duplicate_path_has_mixed_stages(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=(
            b"100644 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa 2\tapp.py\0"
            b"100755 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb 0\tapp.py\0"
        ),
        stderr=b"",
    )
    monkeypatch.setattr(
        gitops_module.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )

    tracked_files = list_tracked_files(tmp_path)

    assert len(tracked_files) == 1
    assert tracked_files[0].mode == "100755"
    assert tracked_files[0].stage == 0


@pytest.mark.parametrize(
    "output",
    [
        b"missing-tab\0",
        b"100644 object stage\tfile.py\0",
        b"100644 object 4\tfile.py\0",
        b"100644 object 0\t\0",
    ],
)
def test_rejects_malformed_git_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    output: bytes,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=output,
        stderr=b"",
    )
    monkeypatch.setattr(
        gitops_module.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )

    with pytest.raises(TrackedFilesOutputError):
        list_tracked_files(tmp_path)


def test_reports_missing_git_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def unavailable(*args: object, **kwargs: object) -> None:
        raise FileNotFoundError

    monkeypatch.setattr(gitops_module.subprocess, "run", unavailable)

    with pytest.raises(GitUnavailableError):
        list_tracked_files(tmp_path)


def test_reports_failed_git_enumeration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    completed = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout=b"",
        stderr=b"failure",
    )
    monkeypatch.setattr(
        gitops_module.subprocess,
        "run",
        lambda *args, **kwargs: completed,
    )

    with pytest.raises(TrackedFilesInspectionError):
        list_tracked_files(tmp_path)
