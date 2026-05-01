from __future__ import annotations

import argparse
import sys
from pathlib import Path

from text_cleaner import __version__
from text_cleaner.logging_setup import configure_logging, write_startup_error
from text_cleaner.portable import resolve_portable_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="text-cleaner")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument("--portable-dir", help="Directory that contains profiles.toml and logs/")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"text-cleaner {__version__}")
        return 0
    portable_dir = resolve_portable_dir(args.portable_dir, Path(sys.argv[0]))
    try:
        logger = configure_logging(portable_dir)
        logger.info("cli_start portable_dir=%s", portable_dir)
        from text_cleaner.tui import run_tui

        return run_tui(portable_dir, logger)
    except Exception as exc:
        write_startup_error(portable_dir, exc)
        raise
