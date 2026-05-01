from __future__ import annotations

import logging
import platform
from datetime import datetime
from pathlib import Path

from text_cleaner import __version__
from text_cleaner.portable import ensure_portable_dirs

LOGGER_NAME = "text_cleaner"


def configure_logging(portable_dir: Path) -> logging.Logger:
    logs_dir = ensure_portable_dirs(portable_dir)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.propagate = False

    handler = logging.FileHandler(logs_dir / "text-cleaner.log", encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(handler)
    logger.info(
        "startup version=%s python=%s platform=%s portable_dir=%s",
        __version__,
        platform.python_version(),
        platform.platform(),
        portable_dir,
    )
    return logger


def write_diagnostics(portable_dir: Path) -> Path:
    logs_dir = ensure_portable_dirs(portable_dir)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    output = logs_dir / f"diagnostics-{timestamp}.log"
    source = logs_dir / "text-cleaner.log"
    with output.open("w", encoding="utf-8") as handle:
        handle.write(f"text-cleaner diagnostics {timestamp}\n")
        handle.write(f"portable_dir={portable_dir}\n")
        handle.write(f"python={platform.python_version()}\n")
        handle.write(f"platform={platform.platform()}\n\n")
        if source.exists():
            handle.write(source.read_text(encoding="utf-8"))
    return output


def write_startup_error(portable_dir: Path, exc: BaseException) -> Path:
    logs_dir = ensure_portable_dirs(portable_dir)
    output = logs_dir / "startup-error.log"
    output.write_text(f"{type(exc).__name__}: {exc}\n", encoding="utf-8")
    return output
