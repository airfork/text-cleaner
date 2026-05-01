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

Planned for the portable build task, after it adds `scripts/build_pyz.py`:

```bash
uv run python scripts/build_pyz.py
```

That build will create `dist/text-cleaner/`.

## Running The Portable App

The portable launchers and `.pyz` are produced by the portable build task and
are not present in the initial scaffold.

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
