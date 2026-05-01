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

The build creates `dist/text-cleaner/`:

```text
dist/text-cleaner/
  text-cleaner.pyz
  profiles.toml
  run.command
  run.cmd
  logs/
```

## Running The Portable App

Run commands from inside `dist/text-cleaner/`.

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

## Profiles

Profiles live in `profiles.toml` beside the portable app. Each profile has a
stable TOML ID and display name. The app ships with starter profiles for NBSP
cleanup, web text cleanup, plain text normalization, deduplicating lines, and
ASCII-safe cleanup.

## Logs

Logs are written beside the app under `logs/`.

- `logs/text-cleaner.log` contains normal app logs.
- `logs/startup-error.log` catches launcher or startup failures.
- Diagnostics can be generated from the TUI.

Raw input, output, and clipboard text are not logged by default.

## Key Operations

NBSP cleanup is explicit: `unicode_spaces_to_normal_space` converts NBSP and
related Unicode spaces to regular spaces before trim and collapse operations
run.
