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
