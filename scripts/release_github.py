from __future__ import annotations

import argparse
import subprocess
import tomllib
from pathlib import Path

try:
    from scripts.package_windows_zip import package_windows_zip
except ModuleNotFoundError:
    from package_windows_zip import package_windows_zip

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
DEFAULT_REPO = "airfork/text-cleaner"


def project_version(pyproject_path: Path = PYPROJECT) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    if not isinstance(version, str) or not version:
        raise ValueError("project.version must be a non-empty string")
    return version


def default_tag(pyproject_path: Path = PYPROJECT) -> str:
    return f"v{project_version(pyproject_path)}"


def release_notes(tag: str, repo: str) -> str:
    direct_url = f"https://github.com/{repo}/releases/download/{tag}/text-cleaner-windows.zip"
    return f"""Portable Windows package for text-cleaner.

Download on Windows with GitHub CLI:

```powershell
gh release download {tag} --repo {repo} --pattern text-cleaner-windows.zip
Expand-Archive .\\text-cleaner-windows.zip -DestinationPath . -Force
cd .\\text-cleaner
.\\run.cmd
```

Without GitHub CLI:

```powershell
Invoke-WebRequest -Uri "{direct_url}" -OutFile "text-cleaner-windows.zip"
Expand-Archive .\\text-cleaner-windows.zip -DestinationPath . -Force
cd .\\text-cleaner
.\\run.cmd
```

Requires Python 3.11 or newer on the Windows machine.
"""


def git_is_dirty(run=subprocess.run) -> bool:
    result = run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return bool(result.stdout.strip())


def release_exists(tag: str, repo: str, run=subprocess.run) -> bool:
    result = run(
        ["gh", "release", "view", tag, "--repo", repo],
        cwd=ROOT,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def run_checks(run=subprocess.run) -> None:
    run(["uv", "run", "pytest", "-v"], cwd=ROOT, check=True)
    run(["uv", "run", "ruff", "check", "."], cwd=ROOT, check=True)


def publish_release(
    *,
    tag: str,
    repo: str,
    run=subprocess.run,
    check_before_release: bool = True,
    allow_dirty: bool = False,
    replace_existing: bool = False,
) -> Path:
    if not allow_dirty and git_is_dirty(run=run):
        raise RuntimeError(
            "working tree has uncommitted changes; commit them or pass --allow-dirty"
        )

    existing_release = release_exists(tag, repo, run=run)
    if existing_release and not replace_existing:
        raise RuntimeError(
            f"Release {tag} already exists in {repo}; bump project.version in "
            "pyproject.toml or pass --replace-existing to overwrite that release asset"
        )

    if check_before_release:
        run_checks(run=run)

    zip_path = package_windows_zip()
    if existing_release:
        run(
            [
                "gh",
                "release",
                "upload",
                tag,
                str(zip_path),
                "--repo",
                repo,
                "--clobber",
            ],
            cwd=ROOT,
            check=True,
        )
    else:
        run(
            [
                "gh",
                "release",
                "create",
                tag,
                str(zip_path),
                "--repo",
                repo,
                "--target",
                "main",
                "--title",
                f"text-cleaner {tag}",
                "--notes",
                release_notes(tag, repo),
            ],
            cwd=ROOT,
            check=True,
        )
    return zip_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="release_github",
        description="Build the Windows zip and publish it to a GitHub release.",
    )
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--tag", default=default_tag())
    parser.add_argument(
        "--skip-checks",
        action="store_true",
        help="Skip pytest and ruff before publishing.",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow publishing from a working tree with uncommitted changes.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Replace the zip asset when the release tag already exists.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    zip_path = publish_release(
        tag=args.tag,
        repo=args.repo,
        check_before_release=not args.skip_checks,
        allow_dirty=args.allow_dirty,
        replace_existing=args.replace_existing,
    )
    print(f"Published {zip_path} to {args.repo} {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
