from __future__ import annotations

import ntpath
import os
import posixpath
import shutil
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist" / "text-cleaner"
ARCHIVE = DIST_DIR / "text-cleaner.pyz"
PYTHON_VERSION_PROBE = "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"


@dataclass(frozen=True)
class RuntimePython:
    command: list[str]
    env: dict[str, str]


def python_candidates(os_name: str = os.name) -> list[str]:
    if os_name == "nt":
        return ["py -3", "python"]
    return ["python3", "python"]


def exclude_active_virtualenv(
    path_value: str,
    virtual_env: str | None,
    os_name: str = os.name,
) -> str:
    if not path_value or not virtual_env:
        return path_value

    path_module = ntpath if os_name == "nt" else posixpath
    path_separator = ";" if os_name == "nt" else ":"
    scripts_dir_name = "Scripts" if os_name == "nt" else "bin"
    active_scripts_dir = path_module.normcase(
        path_module.normpath(path_module.join(virtual_env, scripts_dir_name)),
    )

    filtered_entries = [
        entry
        for entry in path_value.split(path_separator)
        if path_module.normcase(path_module.normpath(entry)) != active_scripts_dir
    ]
    return path_separator.join(filtered_entries)


def _candidate_args(candidate: str) -> list[str]:
    return candidate.split()


def _runtime_env(os_name: str, environ: dict[str, str]) -> dict[str, str]:
    env = dict(environ)
    env["PATH"] = exclude_active_virtualenv(
        env.get("PATH", ""),
        env.get("VIRTUAL_ENV"),
        os_name,
    )
    return env


def resolve_runtime_python(
    os_name: str = os.name,
    environ: dict[str, str] | None = None,
) -> RuntimePython:
    env = _runtime_env(os_name, dict(os.environ if environ is None else environ))
    path_value = env.get("PATH")

    for candidate in python_candidates(os_name):
        args = _candidate_args(candidate)
        if shutil.which(args[0], path=path_value) is None:
            continue
        try:
            subprocess.run(
                [*args, "-c", PYTHON_VERSION_PROBE],
                check=True,
                cwd=ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError):
            continue
        return RuntimePython(args, env)

    raise RuntimeError(
        "No suitable Python 3.11+ runtime found on PATH after excluding the active "
        "virtual environment."
    )


def build() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    subprocess.run(
        [
            "uv",
            "run",
            "shiv",
            "--console-script",
            "text-cleaner",
            "--output-file",
            str(ARCHIVE),
            ".",
        ],
        check=True,
        cwd=ROOT,
    )

    shutil.copy2(ROOT / "examples" / "profiles.toml", DIST_DIR / "profiles.toml")
    shutil.copy2(ROOT / "packaging" / "run.cmd", DIST_DIR / "run.cmd")
    shutil.copy2(ROOT / "packaging" / "run.command", DIST_DIR / "run.command")
    run_command = DIST_DIR / "run.command"
    run_command.chmod(run_command.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    (DIST_DIR / "logs").mkdir()

    runtime_python = resolve_runtime_python()
    subprocess.run(
        [*runtime_python.command, str(ARCHIVE), "--version"],
        check=True,
        cwd=ROOT,
        env=runtime_python.env,
    )


if __name__ == "__main__":
    build()
