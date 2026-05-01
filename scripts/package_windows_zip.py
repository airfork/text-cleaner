from __future__ import annotations

import zipfile
from pathlib import Path

try:
    from scripts import build_pyz
except ModuleNotFoundError:
    import build_pyz

ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = ROOT / "dist"
DIST_DIR = DIST_ROOT / "text-cleaner"
ZIP_PATH = DIST_ROOT / "text-cleaner-windows.zip"
ZIP_ROOT = "text-cleaner"
WINDOWS_FILES = (
    "text-cleaner.pyz",
    "profiles.toml",
    "run.cmd",
    "README-WINDOWS.txt",
)

WINDOWS_README = """Text Cleaner - Windows

Requirements:
- Windows 11
- Python 3.11 or newer available as either `py -3` or `python`

How to run:
1. Unzip this folder.
2. Open PowerShell in the extracted `text-cleaner` folder.
3. Run:

   .\\run.cmd

The app stores profiles in `profiles.toml` beside `run.cmd`.
Logs and diagnostics are written under `logs`.

If the app does not start, check `logs\\startup-error.log`.
"""


def write_windows_readme(portable_dir: Path = DIST_DIR) -> Path:
    readme_path = portable_dir / "README-WINDOWS.txt"
    readme_path.write_text(WINDOWS_README, encoding="utf-8", newline="\n")
    return readme_path


def _assert_required_files(portable_dir: Path) -> None:
    for filename in WINDOWS_FILES:
        path = portable_dir / filename
        if not path.is_file():
            raise FileNotFoundError(f"missing Windows package file: {path}")
    logs_dir = portable_dir / "logs"
    if not logs_dir.is_dir():
        raise FileNotFoundError(f"missing Windows package directory: {logs_dir}")


def create_windows_zip(
    portable_dir: Path = DIST_DIR,
    output_zip: Path = ZIP_PATH,
) -> Path:
    _assert_required_files(portable_dir)
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{ZIP_ROOT}/", "")
        archive.writestr(f"{ZIP_ROOT}/logs/", "")
        for filename in WINDOWS_FILES:
            archive.write(portable_dir / filename, f"{ZIP_ROOT}/{filename}")

    return output_zip


def package_windows_zip() -> Path:
    build_pyz.build()
    write_windows_readme(DIST_DIR)
    output_zip = create_windows_zip(DIST_DIR, ZIP_PATH)
    print(output_zip)
    return output_zip


if __name__ == "__main__":
    package_windows_zip()
