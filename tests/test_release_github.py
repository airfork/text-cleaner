import importlib
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

release_github = importlib.import_module("scripts.release_github")


class FakeRunner:
    def __init__(self, release_exists: bool = False, dirty: bool = False) -> None:
        self.release_exists = release_exists
        self.dirty = dirty
        self.commands: list[list[str]] = []

    def __call__(self, command, **kwargs):
        command = list(command)
        self.commands.append(command)
        if command[:3] == ["git", "status", "--porcelain"]:
            stdout = " M src/text_cleaner/tui.py\n" if self.dirty else ""
            return subprocess.CompletedProcess(command, 0, stdout=stdout)
        if command[:3] == ["gh", "release", "view"]:
            return subprocess.CompletedProcess(command, 0 if self.release_exists else 1)
        return subprocess.CompletedProcess(command, 0)


def test_project_version_reads_pyproject(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "text-cleaner"
version = "1.2.3"
""",
        encoding="utf-8",
    )

    assert release_github.project_version(pyproject) == "1.2.3"


def test_default_tag_uses_project_version(tmp_path):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
version = "1.2.3"
""",
        encoding="utf-8",
    )

    assert release_github.default_tag(pyproject) == "v1.2.3"


def test_release_notes_include_windows_download_commands():
    notes = release_github.release_notes("v1.2.3", "airfork/text-cleaner")

    assert "gh release download v1.2.3 --repo airfork/text-cleaner" in notes
    assert "Invoke-WebRequest" in notes
    assert ".\\run.cmd" in notes


def test_git_is_dirty_reads_status_porcelain():
    assert release_github.git_is_dirty(run=FakeRunner(dirty=True)) is True
    assert release_github.git_is_dirty(run=FakeRunner(dirty=False)) is False


def test_publish_release_rejects_dirty_worktree(tmp_path, monkeypatch):
    zip_path = tmp_path / "text-cleaner-windows.zip"
    zip_path.write_bytes(b"zip")
    monkeypatch.setattr(release_github, "package_windows_zip", lambda: zip_path)

    with pytest.raises(RuntimeError, match="working tree has uncommitted changes"):
        release_github.publish_release(
            tag="v1.2.3",
            repo="airfork/text-cleaner",
            run=FakeRunner(dirty=True),
            check_before_release=False,
            allow_dirty=False,
        )


def test_publish_release_creates_release_when_tag_missing(tmp_path, monkeypatch):
    zip_path = tmp_path / "text-cleaner-windows.zip"
    zip_path.write_bytes(b"zip")
    runner = FakeRunner(release_exists=False)
    monkeypatch.setattr(release_github, "package_windows_zip", lambda: zip_path)

    release_github.publish_release(
        tag="v1.2.3",
        repo="airfork/text-cleaner",
        run=runner,
        check_before_release=False,
        allow_dirty=False,
    )

    assert [
        "gh",
        "release",
        "create",
        "v1.2.3",
        str(zip_path),
        "--repo",
        "airfork/text-cleaner",
    ] == runner.commands[-1][:7]
    assert "--title" in runner.commands[-1]
    assert "--notes" in runner.commands[-1]


def test_publish_release_replaces_asset_when_release_exists(tmp_path, monkeypatch):
    zip_path = tmp_path / "text-cleaner-windows.zip"
    zip_path.write_bytes(b"zip")
    runner = FakeRunner(release_exists=True)
    monkeypatch.setattr(release_github, "package_windows_zip", lambda: zip_path)

    release_github.publish_release(
        tag="v1.2.3",
        repo="airfork/text-cleaner",
        run=runner,
        check_before_release=False,
        allow_dirty=False,
    )

    assert runner.commands[-1] == [
        "gh",
        "release",
        "upload",
        "v1.2.3",
        str(zip_path),
        "--repo",
        "airfork/text-cleaner",
        "--clobber",
    ]
