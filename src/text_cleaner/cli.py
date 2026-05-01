from __future__ import annotations

import argparse

from text_cleaner import __version__


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
    print("Text Cleaner TUI is not wired yet.")
    return 0
