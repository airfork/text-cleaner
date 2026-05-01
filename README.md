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

## Windows Zip

```bash
uv run python scripts/package_windows_zip.py
```

The zip command rebuilds `dist/text-cleaner/`, adds `README-WINDOWS.txt`, and
creates `dist/text-cleaner-windows.zip`. The zip contains only the Windows
portable files needed to run from PowerShell.

## GitHub Release

The release helper rebuilds the Windows zip and publishes it as a GitHub release
asset. It uses the package version from `pyproject.toml` as the default tag, so
version `0.1.0` publishes `v0.1.0`.

Prerequisites:

```bash
gh auth status
```

Release from a clean working tree:

```bash
uv run python scripts/release_github.py
```

If the release tag does not exist, the script creates it. If it already exists,
the script stops and asks you to bump `project.version` in `pyproject.toml` so a
new release tag is created instead of repeatedly replacing the same version.

To intentionally refresh the zip on an existing release:

```bash
uv run python scripts/release_github.py --replace-existing
```

The script refuses to publish when the working tree has uncommitted changes. To
override that for a one-off test release:

```bash
uv run python scripts/release_github.py --allow-dirty
```

Download the latest release on Windows with GitHub CLI:

```powershell
gh release download --repo airfork/text-cleaner --pattern text-cleaner-windows.zip
Expand-Archive .\text-cleaner-windows.zip -DestinationPath . -Force
cd .\text-cleaner
.\run.cmd
```

Or download a specific version:

```powershell
gh release download v0.1.0 --repo airfork/text-cleaner --pattern text-cleaner-windows.zip
```

## Email Windows Zip

The email helper uses iCloud SMTP by default and stores the app-specific password
in the OS keyring. Do not put the app-specific password in this repo.

One-time setup:

```bash
uv run python scripts/email_windows_zip.py --setup --from yourname@icloud.com
```

Send the package:

```bash
uv run python scripts/email_windows_zip.py --from yourname@icloud.com --to destination@example.com
```

Reset the stored password:

```bash
uv run python scripts/email_windows_zip.py --setup --reset-password --from yourname@icloud.com
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

The profile file is strict: misspelled keys are treated as config errors instead
of being ignored.

## Clipboard Flow

The clipboard action reads the current clipboard, applies the selected profile,
and shows a preview with input/output character counts. Choose `Copy` to replace
the clipboard with the cleaned text, or `Cancel` to leave the clipboard
unchanged.

## Operation Order

Selected operations run in the engine-defined order below, not in the order they
appear in `profiles.toml` or the TUI checklist:

```text
strip_html_tags
decode_html_entities
normalize_unicode
unicode_spaces_to_normal_space
trim
remove_blank_lines
collapse_spaces
collapse_blank_lines
line_breaks_to_spaces
remove_line_breaks
uppercase
lowercase
sentence_case
capitalize_words
smart_quotes_to_plain
remove_punctuation
strip_emoji
remove_accents
remove_non_ascii
remove_non_alphanumeric
remove_duplicate_lines
```

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
