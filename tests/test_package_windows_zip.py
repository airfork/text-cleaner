import importlib
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

package_windows_zip = importlib.import_module("scripts.package_windows_zip")


def create_portable_dir(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "text-cleaner.pyz").write_text("archive", encoding="utf-8")
    (path / "profiles.toml").write_text("[profiles]\n", encoding="utf-8")
    (path / "run.cmd").write_text("@echo off\n", encoding="utf-8")
    (path / "run.command").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    (path / "logs").mkdir()


def test_write_windows_readme_includes_run_and_log_instructions(tmp_path):
    portable_dir = tmp_path / "text-cleaner"
    portable_dir.mkdir()

    readme_path = package_windows_zip.write_windows_readme(portable_dir)

    readme = readme_path.read_text(encoding="utf-8")
    assert readme_path == portable_dir / "README-WINDOWS.txt"
    assert ".\\run.cmd" in readme
    assert "Python 3.11" in readme
    assert "logs" in readme


def test_create_windows_zip_contains_only_windows_portable_files(tmp_path):
    portable_dir = tmp_path / "text-cleaner"
    create_portable_dir(portable_dir)
    package_windows_zip.write_windows_readme(portable_dir)
    output_zip = tmp_path / "text-cleaner-windows.zip"

    created = package_windows_zip.create_windows_zip(portable_dir, output_zip)

    assert created == output_zip
    with zipfile.ZipFile(output_zip) as archive:
        names = set(archive.namelist())

    assert "text-cleaner/" in names
    assert "text-cleaner/text-cleaner.pyz" in names
    assert "text-cleaner/profiles.toml" in names
    assert "text-cleaner/run.cmd" in names
    assert "text-cleaner/README-WINDOWS.txt" in names
    assert "text-cleaner/logs/" in names
    assert "text-cleaner/run.command" not in names


def test_create_windows_zip_rejects_missing_required_file(tmp_path):
    portable_dir = tmp_path / "text-cleaner"
    create_portable_dir(portable_dir)
    (portable_dir / "run.cmd").unlink()
    output_zip = tmp_path / "text-cleaner-windows.zip"

    with pytest.raises(FileNotFoundError, match="run.cmd"):
        package_windows_zip.create_windows_zip(portable_dir, output_zip)


def test_package_windows_zip_builds_before_zipping(monkeypatch, tmp_path):
    portable_dir = tmp_path / "text-cleaner"
    output_zip = tmp_path / "text-cleaner-windows.zip"
    calls: list[str] = []

    def fake_build() -> None:
        calls.append("build")
        create_portable_dir(portable_dir)

    monkeypatch.setattr(package_windows_zip.build_pyz, "build", fake_build)
    monkeypatch.setattr(package_windows_zip, "DIST_DIR", portable_dir)
    monkeypatch.setattr(package_windows_zip, "ZIP_PATH", output_zip)

    created = package_windows_zip.package_windows_zip()

    assert calls == ["build"]
    assert created == output_zip
    assert output_zip.exists()
