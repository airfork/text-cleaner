# Portable Text Cleaner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable Python TUI text cleaner with saved profiles, clipboard workflows, local logs, and a cross-platform `.pyz` distribution folder.

**Architecture:** Keep the cleaning engine, profile config, clipboard adapter, logging setup, and TUI separate. The TUI calls small service functions; the cleaning engine accepts plain strings and dataclass profiles, so it is easy to test without terminal or clipboard access.

**Tech Stack:** Python 3.11+, `uv`, `prompt-toolkit`, `pyperclip`, `tomli-w`, `emoji`, `pytest`, `ruff`, `shiv`.

---

## File Structure

- Create `pyproject.toml`: package metadata, dependencies, console script, pytest and ruff config.
- Create `.gitignore`: conventional Python ignore rules plus `dist/`, `.venv/`, logs, and build caches.
- Create `README.md`: development commands, portable build command, launch instructions.
- Create `src/text_cleaner/__init__.py`: version export.
- Create `src/text_cleaner/__main__.py`: `python -m text_cleaner` and `.pyz` entrypoint.
- Create `src/text_cleaner/cli.py`: argument parsing and main startup orchestration.
- Create `src/text_cleaner/portable.py`: portable directory resolution and log directory creation.
- Create `src/text_cleaner/logging_setup.py`: file logger, startup-error capture, diagnostic dump.
- Create `src/text_cleaner/profiles.py`: dataclasses, starter profiles, TOML load/save/validation.
- Create `src/text_cleaner/operations.py`: individual text transforms and operation order.
- Create `src/text_cleaner/engine.py`: profile execution and report generation.
- Create `src/text_cleaner/clipboard.py`: clipboard adapter around `pyperclip`.
- Create `src/text_cleaner/tui.py`: prompt-toolkit profile picker, paste flow, clipboard flow, profile editor, logs view.
- Create `scripts/build_pyz.py`: builds `dist/text-cleaner/`, copies launchers/config, validates archive.
- Create `packaging/run.cmd`: Windows launcher.
- Create `packaging/run.command`: macOS launcher.
- Create `examples/profiles.toml`: starter portable profiles.
- Create `tests/`: focused tests for each non-UI module and build helpers.

## Task 1: Project Scaffold And Tooling

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/text_cleaner/__init__.py`
- Create: `src/text_cleaner/__main__.py`
- Create: `src/text_cleaner/cli.py`
- Create: `tests/test_cli_smoke.py`

- [ ] **Step 1: Create scaffold files**

Create `.gitignore`:

```gitignore
.DS_Store
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
build/
dist/
*.egg-info/
logs/
*.log
profiles.toml.bak
```

Create `pyproject.toml`:

```toml
[project]
name = "text-cleaner"
version = "0.1.0"
description = "Portable TUI text cleaner with saved profiles"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "emoji>=2.11.0",
  "prompt-toolkit>=3.0.43",
  "pyperclip>=1.8.2",
  "tomli-w>=1.0.0",
]

[project.scripts]
text-cleaner = "text_cleaner.cli:main"

[dependency-groups]
dev = [
  "pytest>=8.2.0",
  "ruff>=0.4.0",
  "shiv>=1.0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/text_cleaner"]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

Create `README.md`:

````markdown
# Text Cleaner

Portable Python TUI text cleaner.

## Development

```bash
uv sync
uv run text-cleaner --portable-dir .tmp/dev-portable
uv run pytest
uv run ruff check .
```

## Portable Build

```bash
uv run python scripts/build_pyz.py
```

The build creates `dist/text-cleaner/`.

## Running The Portable App

macOS:

```bash
./run.command
```

Windows PowerShell:

```powershell
.\run.cmd
```

Direct fallback:

```bash
python text-cleaner.pyz
```
````

Create `src/text_cleaner/__init__.py`:

```python
__version__ = "0.1.0"
```

Create `src/text_cleaner/__main__.py`:

```python
from text_cleaner.cli import main

if __name__ == "__main__":
    main()
```

Create `src/text_cleaner/cli.py`:

```python
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
```

- [ ] **Step 2: Write the smoke test**

Create `tests/test_cli_smoke.py`:

```python
from text_cleaner.cli import main


def test_version_command_prints_version(capsys):
    exit_code = main(["--version"])

    assert exit_code == 0
    assert "text-cleaner 0.1.0" in capsys.readouterr().out
```

- [ ] **Step 3: Run the scaffold verification**

Run:

```bash
uv sync
uv run pytest tests/test_cli_smoke.py -v
uv run ruff check .
```

Expected: pytest passes with `1 passed`; ruff reports `All checks passed!`.

- [ ] **Step 4: Commit**

```bash
git add .gitignore README.md pyproject.toml src tests
git commit -m "chore: scaffold python text cleaner"
```

## Task 2: Portable Paths And Logging

**Files:**
- Create: `src/text_cleaner/portable.py`
- Create: `src/text_cleaner/logging_setup.py`
- Modify: `src/text_cleaner/cli.py`
- Test: `tests/test_portable_logging.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_portable_logging.py`:

```python
from pathlib import Path

from text_cleaner.logging_setup import configure_logging, write_diagnostics
from text_cleaner.portable import resolve_portable_dir


def test_resolve_portable_dir_uses_explicit_path(tmp_path):
    chosen = tmp_path / "portable"

    result = resolve_portable_dir(explicit=chosen, argv0=Path("/tmp/app/text-cleaner.pyz"))

    assert result == chosen.resolve()


def test_resolve_portable_dir_uses_archive_parent_when_no_explicit_path(tmp_path):
    archive = tmp_path / "text-cleaner.pyz"
    archive.write_text("archive bytes", encoding="utf-8")

    result = resolve_portable_dir(explicit=None, argv0=archive)

    assert result == tmp_path.resolve()


def test_configure_logging_writes_log_file(tmp_path):
    logger = configure_logging(tmp_path)

    logger.info("hello from test")

    log_file = tmp_path / "logs" / "text-cleaner.log"
    assert log_file.exists()
    assert "hello from test" in log_file.read_text(encoding="utf-8")


def test_write_diagnostics_creates_timestamped_dump(tmp_path):
    logger = configure_logging(tmp_path)
    logger.info("diagnostic source")

    dump = write_diagnostics(tmp_path)

    assert dump.parent == tmp_path / "logs"
    assert dump.name.startswith("diagnostics-")
    assert "diagnostic source" in dump.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_portable_logging.py -v
```

Expected: FAIL with `ModuleNotFoundError` or missing function imports for `text_cleaner.portable` and `text_cleaner.logging_setup`.

- [ ] **Step 3: Implement portable path and logging modules**

Create `src/text_cleaner/portable.py`:

```python
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
```

Create `src/text_cleaner/logging_setup.py`:

```python
from __future__ import annotations

import logging
import platform
import shutil
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
```

- [ ] **Step 4: Wire logging into CLI**

Modify `src/text_cleaner/cli.py`:

```python
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
        print("Text Cleaner TUI is not wired yet.")
        return 0
    except Exception as exc:
        write_startup_error(portable_dir, exc)
        raise
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_portable_logging.py tests/test_cli_smoke.py -v
uv run ruff check .
```

Expected: tests pass; ruff reports `All checks passed!`.

Commit:

```bash
git add src/text_cleaner tests
git commit -m "feat: add portable paths and logging"
```

## Task 3: Profile Model, Starter Profiles, And TOML Validation

**Files:**
- Create: `src/text_cleaner/profiles.py`
- Create: `examples/profiles.toml`
- Test: `tests/test_profiles.py`

- [ ] **Step 1: Write failing profile tests**

Create `tests/test_profiles.py`:

```python
from pathlib import Path

import pytest

from text_cleaner.profiles import (
    Profile,
    ProfileValidationError,
    ReplacementRule,
    default_profiles,
    load_profiles,
    save_profiles,
    validate_profiles,
)


def test_default_profiles_include_nbsp_cleanup():
    profiles = default_profiles()

    assert "nbsp_cleanup" in profiles
    assert "unicode_spaces_to_normal_space" in profiles["nbsp_cleanup"].operations


def test_validate_rejects_duplicate_display_names_case_insensitive():
    profiles = {
        "one": Profile("one", "NBSP cleanup", "first", []),
        "two": Profile("two", " nbsp CLEANUP ", "second", []),
    }

    with pytest.raises(ProfileValidationError, match="duplicate profile name"):
        validate_profiles(profiles)


def test_validate_rejects_empty_replacement_find():
    profiles = {
        "bad": Profile(
            "bad",
            "Bad",
            "bad replacement",
            ["trim"],
            [ReplacementRule(find="", replace="x", regex=False)],
        )
    }

    with pytest.raises(ProfileValidationError, match="replacement find"):
        validate_profiles(profiles)


def test_profiles_round_trip_toml(tmp_path):
    path = tmp_path / "profiles.toml"
    profiles = {
        "nbsp_cleanup": Profile(
            "nbsp_cleanup",
            "NBSP cleanup",
            "Convert NBSPs",
            ["unicode_spaces_to_normal_space", "trim"],
            [ReplacementRule(find="old", replace="new", regex=False)],
        )
    }

    save_profiles(path, profiles)
    loaded = load_profiles(path)

    assert loaded == profiles
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_profiles.py -v
```

Expected: FAIL because `text_cleaner.profiles` does not exist.

- [ ] **Step 3: Implement profiles module**

Create `src/text_cleaner/profiles.py`:

```python
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w


class ProfileValidationError(ValueError):
    pass


VALID_OPERATIONS = {
    "unicode_spaces_to_normal_space",
    "trim",
    "remove_blank_lines",
    "collapse_spaces",
    "collapse_blank_lines",
    "line_breaks_to_spaces",
    "remove_line_breaks",
    "uppercase",
    "lowercase",
    "sentence_case",
    "capitalize_words",
    "remove_punctuation",
    "strip_emoji",
    "remove_accents",
    "normalize_unicode",
    "remove_non_ascii",
    "remove_non_alphanumeric",
    "smart_quotes_to_plain",
    "strip_html_tags",
    "decode_html_entities",
    "remove_duplicate_lines",
}


@dataclass(frozen=True)
class ReplacementRule:
    find: str
    replace: str
    regex: bool = False


@dataclass(frozen=True)
class Profile:
    profile_id: str
    name: str
    description: str
    operations: list[str] = field(default_factory=list)
    replacements: list[ReplacementRule] = field(default_factory=list)


def normalize_display_name(name: str) -> str:
    return " ".join(name.strip().casefold().split())


def validate_profiles(profiles: dict[str, Profile]) -> None:
    seen_names: set[str] = set()
    for profile_id, profile in profiles.items():
        if profile_id != profile.profile_id:
            raise ProfileValidationError(f"profile key mismatch for {profile_id}")
        if not profile_id.strip():
            raise ProfileValidationError("profile id cannot be empty")
        normalized_name = normalize_display_name(profile.name)
        if not normalized_name:
            raise ProfileValidationError("profile name cannot be empty")
        if normalized_name in seen_names:
            raise ProfileValidationError(f"duplicate profile name: {profile.name}")
        seen_names.add(normalized_name)
        invalid = [op for op in profile.operations if op not in VALID_OPERATIONS]
        if invalid:
            raise ProfileValidationError(f"invalid operation for {profile_id}: {invalid[0]}")
        for rule in profile.replacements:
            if not rule.find:
                raise ProfileValidationError(f"replacement find cannot be empty for {profile_id}")
            if rule.regex:
                re.compile(rule.find)


def default_profiles() -> dict[str, Profile]:
    profiles = {
        "nbsp_cleanup": Profile(
            "nbsp_cleanup",
            "NBSP cleanup",
            "Convert NBSP/unicode spaces, trim, collapse repeated spaces",
            ["unicode_spaces_to_normal_space", "trim", "collapse_spaces"],
        ),
        "web_text_cleanup": Profile(
            "web_text_cleanup",
            "Web text cleanup",
            "Strip HTML, decode entities, normalize spacing",
            [
                "strip_html_tags",
                "decode_html_entities",
                "unicode_spaces_to_normal_space",
                "collapse_spaces",
            ],
        ),
        "plain_text_normalize": Profile(
            "plain_text_normalize",
            "Plain text normalize",
            "Normalize spacing, quotes, accents, and blank lines",
            [
                "unicode_spaces_to_normal_space",
                "smart_quotes_to_plain",
                "remove_accents",
                "trim",
                "collapse_spaces",
                "collapse_blank_lines",
            ],
        ),
        "deduplicate_lines": Profile(
            "deduplicate_lines",
            "Deduplicate lines",
            "Remove duplicate lines while preserving first occurrence",
            ["remove_duplicate_lines"],
        ),
        "ascii_safe_cleanup": Profile(
            "ascii_safe_cleanup",
            "ASCII-safe cleanup",
            "Plain ASCII output with normalized spaces and quotes",
            [
                "unicode_spaces_to_normal_space",
                "smart_quotes_to_plain",
                "remove_accents",
                "remove_non_ascii",
                "trim",
                "collapse_spaces",
            ],
        ),
    }
    validate_profiles(profiles)
    return profiles


def load_profiles(path: Path) -> dict[str, Profile]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    raw_profiles = data.get("profiles", {})
    profiles: dict[str, Profile] = {}
    for profile_id, raw in raw_profiles.items():
        replacements = [
            ReplacementRule(
                find=str(rule.get("find", "")),
                replace=str(rule.get("replace", "")),
                regex=bool(rule.get("regex", False)),
            )
            for rule in raw.get("replacements", [])
        ]
        profiles[profile_id] = Profile(
            profile_id=profile_id,
            name=str(raw.get("name", "")),
            description=str(raw.get("description", "")),
            operations=list(raw.get("operations", [])),
            replacements=replacements,
        )
    validate_profiles(profiles)
    return profiles


def profile_to_toml(profile: Profile) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": profile.name,
        "description": profile.description,
        "operations": profile.operations,
    }
    if profile.replacements:
        data["replacements"] = [
            {"find": rule.find, "replace": rule.replace, "regex": rule.regex}
            for rule in profile.replacements
        ]
    return data


def save_profiles(path: Path, profiles: dict[str, Profile]) -> None:
    validate_profiles(profiles)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    data = {"profiles": {key: profile_to_toml(value) for key, value in profiles.items()}}
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(tomli_w.dumps(data), encoding="utf-8")
    temp.replace(path)
```

- [ ] **Step 4: Add starter config file**

Create `examples/profiles.toml` by serializing `default_profiles()` through `save_profiles()` or by copying this content:

```toml
[profiles.nbsp_cleanup]
name = "NBSP cleanup"
description = "Convert NBSP/unicode spaces, trim, collapse repeated spaces"
operations = ["unicode_spaces_to_normal_space", "trim", "collapse_spaces"]

[profiles.web_text_cleanup]
name = "Web text cleanup"
description = "Strip HTML, decode entities, normalize spacing"
operations = ["strip_html_tags", "decode_html_entities", "unicode_spaces_to_normal_space", "collapse_spaces"]

[profiles.plain_text_normalize]
name = "Plain text normalize"
description = "Normalize spacing, quotes, accents, and blank lines"
operations = ["unicode_spaces_to_normal_space", "smart_quotes_to_plain", "remove_accents", "trim", "collapse_spaces", "collapse_blank_lines"]

[profiles.deduplicate_lines]
name = "Deduplicate lines"
description = "Remove duplicate lines while preserving first occurrence"
operations = ["remove_duplicate_lines"]

[profiles.ascii_safe_cleanup]
name = "ASCII-safe cleanup"
description = "Plain ASCII output with normalized spaces and quotes"
operations = ["unicode_spaces_to_normal_space", "smart_quotes_to_plain", "remove_accents", "remove_non_ascii", "trim", "collapse_spaces"]
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_profiles.py -v
uv run ruff check .
```

Expected: profile tests pass; ruff reports `All checks passed!`.

Commit:

```bash
git add src/text_cleaner/profiles.py examples/profiles.toml tests/test_profiles.py
git commit -m "feat: add portable profile config"
```

## Task 4: Cleaning Operations And Engine

**Files:**
- Create: `src/text_cleaner/operations.py`
- Create: `src/text_cleaner/engine.py`
- Test: `tests/test_operations.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write failing operation tests**

Create `tests/test_operations.py`:

```python
import pytest

from text_cleaner.operations import apply_operation


@pytest.mark.parametrize(
    ("operation", "input_text", "expected"),
    [
        ("unicode_spaces_to_normal_space", "a\u00a0b\u2007c", "a b c"),
        ("trim", "  hello \n", "hello"),
        ("remove_blank_lines", "a\n\n \n b", "a\n b"),
        ("collapse_spaces", "a   b\t\tc", "a b c"),
        ("collapse_blank_lines", "a\n\n\nb", "a\n\nb"),
        ("line_breaks_to_spaces", "a\nb\r\nc", "a b c"),
        ("remove_line_breaks", "a\nb\r\nc", "abc"),
        ("uppercase", "Hello", "HELLO"),
        ("lowercase", "Hello", "hello"),
        ("sentence_case", "hello. next", "Hello. Next"),
        ("capitalize_words", "hello world", "Hello World"),
        ("remove_punctuation", "hello, world!", "hello world"),
        ("strip_emoji", "hi 😀 there", "hi  there"),
        ("remove_accents", "cafe\u0301 déjà", "cafe deja"),
        ("normalize_unicode", "\uff21", "A"),
        ("remove_non_ascii", "aé😀b", "ab"),
        ("remove_non_alphanumeric", "a-b c!", "ab c"),
        ("smart_quotes_to_plain", "“hi” ‘there’", '"hi" \'there\''),
        ("strip_html_tags", "<p>Hello <strong>world</strong></p>", "Hello world"),
        ("decode_html_entities", "Tom&nbsp;&amp;&nbsp;Jerry", "Tom\u00a0&\u00a0Jerry"),
        ("remove_duplicate_lines", "a\nb\na\nc\nb", "a\nb\nc"),
    ],
)
def test_apply_operation(operation, input_text, expected):
    assert apply_operation(operation, input_text) == expected
```

Create `tests/test_engine.py`:

```python
from text_cleaner.engine import clean_text
from text_cleaner.profiles import Profile, ReplacementRule


def test_clean_text_uses_engine_order_for_nbsp_then_trim_then_collapse():
    profile = Profile(
        "test",
        "Test",
        "Test profile",
        ["trim", "collapse_spaces", "unicode_spaces_to_normal_space"],
    )

    result = clean_text("\u00a0 hello\u00a0\u00a0world \u00a0", profile)

    assert result.text == "hello world"
    assert result.report.input_chars == 16
    assert result.report.output_chars == 11
    assert result.report.operations == [
        "unicode_spaces_to_normal_space",
        "trim",
        "collapse_spaces",
    ]


def test_clean_text_applies_replacements_after_operations():
    profile = Profile(
        "test",
        "Test",
        "Test profile",
        ["lowercase"],
        [ReplacementRule(find="hello", replace="hi", regex=False)],
    )

    result = clean_text("HELLO", profile)

    assert result.text == "hi"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_operations.py tests/test_engine.py -v
```

Expected: FAIL because operation and engine modules do not exist.

- [ ] **Step 3: Implement operations**

Create `src/text_cleaner/operations.py`:

```python
from __future__ import annotations

import html
import re
import string
import unicodedata
from html.parser import HTMLParser

import emoji


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


SMART_QUOTES = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
}


def apply_operation(operation: str, text: str) -> str:
    return OPERATIONS[operation](text)


def unicode_spaces_to_normal_space(text: str) -> str:
    return "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in text)


def trim(text: str) -> str:
    return text.strip()


def remove_blank_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if line.strip())


def collapse_spaces(text: str) -> str:
    return re.sub(r"[ \t\f\v]+", " ", text)


def collapse_blank_lines(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", normalized)


def line_breaks_to_spaces(text: str) -> str:
    return re.sub(r"[ \t]*\r?\n[ \t]*", " ", text)


def remove_line_breaks(text: str) -> str:
    return text.replace("\r\n", "").replace("\n", "").replace("\r", "")


def sentence_case(text: str) -> str:
    lowered = text.lower()
    chars = list(lowered)
    capitalize_next = True
    for index, char in enumerate(chars):
        if capitalize_next and char.isalpha():
            chars[index] = char.upper()
            capitalize_next = False
        if char in ".!?":
            capitalize_next = True
    return "".join(chars)


def remove_punctuation(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != "P")


def remove_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def remove_non_ascii(text: str) -> str:
    return "".join(ch for ch in text if ord(ch) < 128)


def remove_non_alphanumeric(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum() or ch.isspace())


def smart_quotes_to_plain(text: str) -> str:
    return "".join(SMART_QUOTES.get(ch, ch) for ch in text)


def strip_html_tags(text: str) -> str:
    parser = _TextExtractor()
    parser.feed(text)
    return parser.text()


def remove_duplicate_lines(text: str) -> str:
    seen: set[str] = set()
    output: list[str] = []
    for line in text.splitlines():
        if line not in seen:
            seen.add(line)
            output.append(line)
    return "\n".join(output)


OPERATIONS = {
    "unicode_spaces_to_normal_space": unicode_spaces_to_normal_space,
    "trim": trim,
    "remove_blank_lines": remove_blank_lines,
    "collapse_spaces": collapse_spaces,
    "collapse_blank_lines": collapse_blank_lines,
    "line_breaks_to_spaces": line_breaks_to_spaces,
    "remove_line_breaks": remove_line_breaks,
    "uppercase": str.upper,
    "lowercase": str.lower,
    "sentence_case": sentence_case,
    "capitalize_words": string.capwords,
    "remove_punctuation": remove_punctuation,
    "strip_emoji": lambda text: emoji.replace_emoji(text, replace=""),
    "remove_accents": remove_accents,
    "normalize_unicode": lambda text: unicodedata.normalize("NFKC", text),
    "remove_non_ascii": remove_non_ascii,
    "remove_non_alphanumeric": remove_non_alphanumeric,
    "smart_quotes_to_plain": smart_quotes_to_plain,
    "strip_html_tags": strip_html_tags,
    "decode_html_entities": html.unescape,
    "remove_duplicate_lines": remove_duplicate_lines,
}

OPERATION_ORDER = [
    "strip_html_tags",
    "decode_html_entities",
    "normalize_unicode",
    "unicode_spaces_to_normal_space",
    "trim",
    "remove_blank_lines",
    "collapse_spaces",
    "collapse_blank_lines",
    "line_breaks_to_spaces",
    "remove_line_breaks",
    "uppercase",
    "lowercase",
    "sentence_case",
    "capitalize_words",
    "remove_punctuation",
    "strip_emoji",
    "remove_accents",
    "remove_non_ascii",
    "remove_non_alphanumeric",
    "smart_quotes_to_plain",
    "remove_duplicate_lines",
]
```

- [ ] **Step 4: Implement engine**

Create `src/text_cleaner/engine.py`:

```python
from __future__ import annotations

import re
from dataclasses import dataclass

from text_cleaner.operations import OPERATION_ORDER, apply_operation
from text_cleaner.profiles import Profile


@dataclass(frozen=True)
class CleanReport:
    profile_id: str
    profile_name: str
    input_chars: int
    output_chars: int
    operations: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class CleanResult:
    text: str
    report: CleanReport


def clean_text(text: str, profile: Profile) -> CleanResult:
    selected = set(profile.operations)
    ordered = [operation for operation in OPERATION_ORDER if operation in selected]
    output = text
    for operation in ordered:
        output = apply_operation(operation, output)
    for rule in profile.replacements:
        if rule.regex:
            output = re.sub(rule.find, rule.replace, output)
        else:
            output = output.replace(rule.find, rule.replace)
    return CleanResult(
        text=output,
        report=CleanReport(
            profile_id=profile.profile_id,
            profile_name=profile.name,
            input_chars=len(text),
            output_chars=len(output),
            operations=ordered,
            warnings=[],
        ),
    )
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_operations.py tests/test_engine.py tests/test_profiles.py -v
uv run ruff check .
```

Expected: tests pass; ruff reports `All checks passed!`.

Commit:

```bash
git add src/text_cleaner/operations.py src/text_cleaner/engine.py tests/test_operations.py tests/test_engine.py
git commit -m "feat: add cleaning engine"
```

## Task 5: Clipboard Adapter And Profile Repository

**Files:**
- Create: `src/text_cleaner/clipboard.py`
- Modify: `src/text_cleaner/profiles.py`
- Test: `tests/test_clipboard.py`
- Test: `tests/test_profile_repository.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_clipboard.py`:

```python
from text_cleaner.clipboard import ClipboardService


def test_clipboard_service_reads_and_writes(monkeypatch):
    stored = {"value": "input"}

    monkeypatch.setattr("pyperclip.paste", lambda: stored["value"])
    monkeypatch.setattr("pyperclip.copy", lambda value: stored.__setitem__("value", value))

    service = ClipboardService()

    assert service.read_text() == "input"
    service.write_text("output")
    assert stored["value"] == "output"
```

Create `tests/test_profile_repository.py`:

```python
from text_cleaner.profiles import ProfileRepository


def test_repository_creates_default_profiles_when_file_missing(tmp_path):
    repository = ProfileRepository(tmp_path / "profiles.toml")

    profiles = repository.load_or_create()

    assert "nbsp_cleanup" in profiles
    assert (tmp_path / "profiles.toml").exists()


def test_repository_saves_clear_profile(tmp_path):
    repository = ProfileRepository(tmp_path / "profiles.toml")
    profiles = repository.load_or_create()

    cleared = repository.clear_profile(profiles, "nbsp_cleanup")

    assert cleared["nbsp_cleanup"].operations == []
    assert cleared["nbsp_cleanup"].replacements == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_clipboard.py tests/test_profile_repository.py -v
```

Expected: FAIL because `ClipboardService` and `ProfileRepository` do not exist.

- [ ] **Step 3: Implement clipboard adapter**

Create `src/text_cleaner/clipboard.py`:

```python
from __future__ import annotations

import pyperclip


class ClipboardError(RuntimeError):
    pass


class ClipboardService:
    def read_text(self) -> str:
        try:
            value = pyperclip.paste()
        except pyperclip.PyperclipException as exc:
            raise ClipboardError(str(exc)) from exc
        return "" if value is None else str(value)

    def write_text(self, text: str) -> None:
        try:
            pyperclip.copy(text)
        except pyperclip.PyperclipException as exc:
            raise ClipboardError(str(exc)) from exc
```

- [ ] **Step 4: Implement profile repository**

Add this to `src/text_cleaner/profiles.py`:

```python
class ProfileRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load_or_create(self) -> dict[str, Profile]:
        if not self.path.exists():
            profiles = default_profiles()
            save_profiles(self.path, profiles)
            return profiles
        profiles = load_profiles(self.path)
        if not profiles:
            profiles = default_profiles()
            save_profiles(self.path, profiles)
        return profiles

    def save(self, profiles: dict[str, Profile]) -> None:
        save_profiles(self.path, profiles)

    def clear_profile(self, profiles: dict[str, Profile], profile_id: str) -> dict[str, Profile]:
        profile = profiles[profile_id]
        updated = dict(profiles)
        updated[profile_id] = Profile(
            profile.profile_id,
            profile.name,
            profile.description,
            [],
            [],
        )
        save_profiles(self.path, updated)
        return updated

    def delete_profile(self, profiles: dict[str, Profile], profile_id: str) -> dict[str, Profile]:
        updated = dict(profiles)
        del updated[profile_id]
        if not updated:
            return {}
        save_profiles(self.path, updated)
        return updated
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest tests/test_clipboard.py tests/test_profile_repository.py tests/test_profiles.py -v
uv run ruff check .
```

Expected: tests pass; ruff reports `All checks passed!`.

Commit:

```bash
git add src/text_cleaner/clipboard.py src/text_cleaner/profiles.py tests/test_clipboard.py tests/test_profile_repository.py
git commit -m "feat: add clipboard and profile repository"
```

## Task 6: TUI Workflows

**Files:**
- Create: `src/text_cleaner/tui.py`
- Modify: `src/text_cleaner/cli.py`
- Test: `tests/test_tui_services.py`

- [ ] **Step 1: Write service-level tests for TUI actions**

Create `tests/test_tui_services.py`:

```python
from text_cleaner.clipboard import ClipboardService
from text_cleaner.engine import clean_text
from text_cleaner.profiles import Profile


class FakeClipboard(ClipboardService):
    def __init__(self, text: str) -> None:
        self.text = text

    def read_text(self) -> str:
        return self.text

    def write_text(self, text: str) -> None:
        self.text = text


def test_clipboard_clean_flow_uses_selected_profile():
    clipboard = FakeClipboard("\u00a0Hello\u00a0\u00a0World\u00a0")
    profile = Profile(
        "nbsp_cleanup",
        "NBSP cleanup",
        "Clean spaces",
        ["unicode_spaces_to_normal_space", "trim", "collapse_spaces"],
    )

    result = clean_text(clipboard.read_text(), profile)
    clipboard.write_text(result.text)

    assert clipboard.text == "Hello World"
    assert result.report.operations == [
        "unicode_spaces_to_normal_space",
        "trim",
        "collapse_spaces",
    ]
```

- [ ] **Step 2: Run test to verify current service flow works**

Run:

```bash
uv run pytest tests/test_tui_services.py -v
```

Expected: PASS. This pins the service contract before terminal UI wiring.

- [ ] **Step 3: Implement prompt-toolkit TUI**

Create `src/text_cleaner/tui.py`:

```python
from __future__ import annotations

import logging
from pathlib import Path

from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import button_dialog, checkboxlist_dialog, input_dialog, message_dialog, radiolist_dialog

from text_cleaner.clipboard import ClipboardError, ClipboardService
from text_cleaner.engine import clean_text
from text_cleaner.logging_setup import write_diagnostics
from text_cleaner.profiles import Profile, ProfileRepository, VALID_OPERATIONS


def operation_summary(profile: Profile) -> str:
    if not profile.operations and not profile.replacements:
        return "No operations selected"
    pieces = list(profile.operations)
    if profile.replacements:
        pieces.append(f"{len(profile.replacements)} replacement rule(s)")
    return ", ".join(pieces)


def choose_profile(profiles: dict[str, Profile]) -> str | None:
    values = [
        (profile_id, f"{profile.name} - {profile.description}")
        for profile_id, profile in profiles.items()
    ]
    return radiolist_dialog(
        title="Text Cleaner",
        text="Choose a profile",
        values=values,
    ).run()


def paste_flow(profile: Profile, clipboard: ClipboardService, logger: logging.Logger) -> None:
    text = prompt("Paste text. Press Esc+Enter when finished:\n", multiline=True)
    result = clean_text(text, profile)
    logger.info(
        "paste_flow profile=%s input_chars=%s output_chars=%s operations=%s",
        profile.profile_id,
        result.report.input_chars,
        result.report.output_chars,
        result.report.operations,
    )
    message_dialog(title="Cleaned Output", text=result.text[:4000]).run()
    copy = button_dialog(
        title="Copy output",
        text=f"Output has {result.report.output_chars} chars. Copy to clipboard?",
        buttons=[("Copy", True), ("Skip", False)],
    ).run()
    if copy:
        clipboard.write_text(result.text)


def clipboard_flow(profile: Profile, clipboard: ClipboardService, logger: logging.Logger) -> None:
    try:
        source = clipboard.read_text()
        result = clean_text(source, profile)
        clipboard.write_text(result.text)
    except ClipboardError as exc:
        logger.exception("clipboard_flow_failed profile=%s", profile.profile_id)
        message_dialog(title="Clipboard error", text=str(exc)).run()
        return
    logger.info(
        "clipboard_flow profile=%s input_chars=%s output_chars=%s operations=%s",
        profile.profile_id,
        result.report.input_chars,
        result.report.output_chars,
        result.report.operations,
    )
    message_dialog(
        title="Clipboard cleaned",
        text=f"{result.report.input_chars} chars -> {result.report.output_chars} chars",
    ).run()


def edit_profile(profile: Profile) -> Profile:
    name = input_dialog(title="Profile name", text="Display name:", default=profile.name).run()
    if name is None:
        return profile
    description = input_dialog(
        title="Profile description",
        text="Short hint:",
        default=profile.description,
    ).run()
    if description is None:
        return profile
    selected = checkboxlist_dialog(
        title="Operations",
        text="Choose operations",
        values=[(operation, operation) for operation in sorted(VALID_OPERATIONS)],
        default_values=profile.operations,
    ).run()
    if selected is None:
        return profile
    return Profile(
        profile.profile_id,
        name,
        description,
        list(selected),
        profile.replacements,
    )


def run_tui(portable_dir: Path, logger: logging.Logger) -> int:
    repository = ProfileRepository(portable_dir / "profiles.toml")
    clipboard = ClipboardService()
    profiles = repository.load_or_create()
    while True:
        if not profiles:
            message_dialog(title="No profiles", text="Create a profile in profiles.toml or restore defaults.").run()
            profiles = repository.load_or_create()
        profile_id = choose_profile(profiles)
        if profile_id is None:
            return 0
        profile = profiles[profile_id]
        action = button_dialog(
            title=profile.name,
            text=f"{profile.description}\n\n{operation_summary(profile)}",
            buttons=[
                ("Paste", "paste"),
                ("Clipboard", "clipboard"),
                ("Edit", "edit"),
                ("Logs", "logs"),
                ("Quit", "quit"),
            ],
        ).run()
        if action == "paste":
            paste_flow(profile, clipboard, logger)
        elif action == "clipboard":
            clipboard_flow(profile, clipboard, logger)
        elif action == "edit":
            profiles[profile_id] = edit_profile(profile)
            repository.save(profiles)
        elif action == "logs":
            dump = write_diagnostics(portable_dir)
            message_dialog(title="Diagnostics written", text=str(dump)).run()
        elif action == "quit" or action is None:
            return 0
```

- [ ] **Step 4: Wire TUI into CLI**

Modify `src/text_cleaner/cli.py` so `main()` imports and calls `run_tui` after logging:

```python
from text_cleaner.tui import run_tui
```

Replace the current print branch with:

```python
return run_tui(portable_dir, logger)
```

- [ ] **Step 5: Run tests and commit**

Run:

```bash
uv run pytest -v
uv run ruff check .
```

Expected: tests pass; ruff reports `All checks passed!`.

Commit:

```bash
git add src/text_cleaner/tui.py src/text_cleaner/cli.py tests/test_tui_services.py
git commit -m "feat: add text cleaner tui workflows"
```

## Task 7: Portable Build And Launchers

**Files:**
- Create: `scripts/build_pyz.py`
- Create: `packaging/run.cmd`
- Create: `packaging/run.command`
- Test: `tests/test_build_pyz.py`

- [ ] **Step 1: Write failing build-helper tests**

Create `tests/test_build_pyz.py`:

```python
import ntpath
import posixpath

from scripts.build_pyz import exclude_active_virtualenv, python_candidates


def test_python_candidates_windows_order():
    assert python_candidates("nt") == ["py -3", "python"]


def test_python_candidates_posix_order():
    assert python_candidates("posix") == ["python3", "python"]


def test_exclude_active_virtualenv_windows_path():
    path = ntpathsep_join([r"C:\repo\.venv\Scripts", r"C:\Python312"])

    result = exclude_active_virtualenv(
        path_value=path,
        virtual_env=r"C:\repo\.venv",
        os_name="nt",
    )

    assert result == r"C:\Python312"


def test_exclude_active_virtualenv_posix_path():
    path = posixpathsep_join(["/repo/.venv/bin", "/usr/bin"])

    result = exclude_active_virtualenv(
        path_value=path,
        virtual_env="/repo/.venv",
        os_name="posix",
    )

    assert result == "/usr/bin"


def ntpathsep_join(parts):
    return ";".join(parts)


def posixpathsep_join(parts):
    return ":".join(parts)
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_build_pyz.py -v
```

Expected: FAIL because `scripts/build_pyz.py` does not exist.

- [ ] **Step 3: Implement launchers**

Create `packaging/run.cmd`:

```bat
@echo off
setlocal
set "APP_DIR=%~dp0"
if not exist "%APP_DIR%logs" mkdir "%APP_DIR%logs"

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 "%APP_DIR%text-cleaner.pyz" --portable-dir "%APP_DIR%"
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python "%APP_DIR%text-cleaner.pyz" --portable-dir "%APP_DIR%"
  exit /b %ERRORLEVEL%
)

echo Python was not found. Install Python or run with an available Python command. > "%APP_DIR%logs\startup-error.log"
echo Python was not found.
exit /b 1
```

Create `packaging/run.command`:

```bash
#!/usr/bin/env bash
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$APP_DIR/logs"

if command -v python3 >/dev/null 2>&1; then
  exec python3 "$APP_DIR/text-cleaner.pyz" --portable-dir "$APP_DIR"
fi

if command -v python >/dev/null 2>&1; then
  exec python "$APP_DIR/text-cleaner.pyz" --portable-dir "$APP_DIR"
fi

echo "Python was not found." | tee "$APP_DIR/logs/startup-error.log"
exit 1
```

- [ ] **Step 4: Implement build script**

Create `scripts/build_pyz.py`:

```python
from __future__ import annotations

import ntpath
import os
import posixpath
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = ROOT / "dist" / "text-cleaner"
ARCHIVE = DIST_DIR / "text-cleaner.pyz"


def python_candidates(os_name: str) -> list[str]:
    return ["py -3", "python"] if os_name == "nt" else ["python3", "python"]


def exclude_active_virtualenv(path_value: str, virtual_env: str | None, os_name: str) -> str:
    if not virtual_env:
        return path_value
    separator = ";" if os_name == "nt" else ":"
    pathmod = ntpath if os_name == "nt" else posixpath
    scripts_dir = "Scripts" if os_name == "nt" else "bin"
    venv_bin = pathmod.normcase(pathmod.normpath(pathmod.join(virtual_env, scripts_dir)))
    entries = [
        entry
        for entry in path_value.split(separator)
        if entry and pathmod.normcase(pathmod.normpath(entry)) != venv_bin
    ]
    return separator.join(entries)


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
        cwd=ROOT,
        check=True,
    )
    shutil.copy2(ROOT / "examples" / "profiles.toml", DIST_DIR / "profiles.toml")
    shutil.copy2(ROOT / "packaging" / "run.cmd", DIST_DIR / "run.cmd")
    run_command = DIST_DIR / "run.command"
    shutil.copy2(ROOT / "packaging" / "run.command", run_command)
    run_command.chmod(0o755)
    (DIST_DIR / "logs").mkdir()
    subprocess.run(["python", str(ARCHIVE), "--version"], check=True)


if __name__ == "__main__":
    build()
```

- [ ] **Step 5: Run tests and build**

Run:

```bash
uv run pytest tests/test_build_pyz.py -v
uv run ruff check .
uv run python scripts/build_pyz.py
python dist/text-cleaner/text-cleaner.pyz --version
```

Expected: tests pass; ruff reports `All checks passed!`; build creates `dist/text-cleaner/text-cleaner.pyz`; version command prints `text-cleaner 0.1.0`.

Commit:

```bash
git add scripts/build_pyz.py packaging tests/test_build_pyz.py
git commit -m "feat: add portable pyz build"
```

## Task 8: Final Verification And Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-04-30-portable-text-cleaner-implementation.md`

- [x] **Step 1: Update README with operation and logging behavior**

Add these sections to `README.md`:

```markdown
## Profiles

Profiles live in `profiles.toml` beside the portable app. Each profile has a stable TOML ID and display name.

## Logs

Logs are written beside the app under `logs/`.

- `logs/text-cleaner.log` contains normal app logs.
- `logs/startup-error.log` catches launcher or startup failures.
- Diagnostics can be generated from the TUI.

Raw input and clipboard text are not logged by default.

## Key Operations

NBSP cleanup is explicit: `unicode_spaces_to_normal_space` converts NBSP and related Unicode spaces to regular spaces before trim and collapse operations run.
```

- [x] **Step 2: Run full verification**

Run:

```bash
uv run pytest -v
uv run ruff check .
uv run python scripts/build_pyz.py
python dist/text-cleaner/text-cleaner.pyz --version
```

Expected:

- pytest reports all tests passing
- ruff reports `All checks passed!`
- build recreates `dist/text-cleaner/`
- direct archive run prints `text-cleaner 0.1.0`

- [x] **Step 3: Manual smoke test the TUI**

Run:

```bash
uv run text-cleaner --portable-dir .tmp/manual-smoke
```

Expected:

- starter profiles load or are created
- selecting NBSP cleanup shows the description
- paste flow cleans `Hello\u00a0\u00a0World` to `Hello World`
- clipboard flow reports input and output character counts
- diagnostics command writes a file under `.tmp/manual-smoke/logs/`

- [ ] **Step 4: Commit docs and plan completion**

```bash
git add README.md docs/superpowers/plans/2026-04-30-portable-text-cleaner-implementation.md
git commit -m "docs: document text cleaner usage"
```

## Self-Review Checklist

- Spec coverage: runtime packaging, portable profiles, NBSP cleanup, in-app profile editing, duplicate-name validation, logging, diagnostics, clipboard flow, and `.pyz` build each have implementation tasks.
- Red-flag scan: no vague implementation language is allowed in this plan.
- Type consistency: `Profile`, `ReplacementRule`, `ProfileRepository`, `ClipboardService`, `clean_text`, `CleanResult`, and `CleanReport` names are defined before later tasks use them.
