from __future__ import annotations

from pathlib import Path


def resolve_portable_dir(explicit: Path | str | None, argv0: Path | str) -> Path:
    if explicit is not None:
        return Path(explicit).expanduser().resolve()
    return Path(argv0).expanduser().resolve().parent


def ensure_portable_dirs(portable_dir: Path) -> Path:
    logs_dir = portable_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir
