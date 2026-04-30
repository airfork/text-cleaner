# Portable Text Cleaner Design

Date: 2026-04-30

## Goal

Build a portable, cross-platform text-cleaning utility inspired by textcleaner.net. The app will be developed on macOS and must work reliably on Windows 11 without requiring an installer. It should support saved named profiles, fast clipboard workflows, manual paste workflows, and thorough local logging for debugging Windows issues.

## Runtime And Packaging

The app will be a Python TUI distributed as a portable folder:

```text
text-cleaner/
  text-cleaner.pyz
  profiles.toml
  run.command
  run.cmd
  README.txt
  logs/
```

Development uses `uv` from the source repository. Distribution builds a fresh folder under `dist/text-cleaner/`. The portable artifact can be copied from macOS to Windows with its profiles intact.

The supported launch paths are:

```text
Daily use on macOS:
  ./run.command

Daily use on Windows or PowerShell:
  .\run.cmd

Direct fallback:
  python text-cleaner.pyz
```

The launcher scripts are convenience and guardrails, not hidden requirements. They should:

- run from the portable folder so `profiles.toml` and `logs/` resolve consistently
- choose a Python command for the platform: Windows tries `py -3`, then `python`; macOS tries `python3`, then `python`
- create `logs/` if missing
- pass a stable portable directory argument to the app
- capture early startup failures in `logs/startup-error.log`

The `.pyz` may have a Unix shebang for macOS/Linux direct execution, but Windows support must not depend on shebang behavior.

## Profiles

Profiles are stored in one portable, human-readable `profiles.toml` file. Each profile has a stable TOML ID and a display name:

```toml
[profiles.nbsp_cleanup]
name = "NBSP cleanup"
description = "Convert NBSP/unicode spaces, trim, collapse repeated spaces"
operations = [
  "unicode_spaces_to_normal_space",
  "trim",
  "collapse_spaces",
]

[[profiles.nbsp_cleanup.replacements]]
find = "old"
replace = "new"
regex = false
```

The TOML ID, such as `nbsp_cleanup`, is stable after creation. The display name is what the TUI shows. Both profile IDs and display names must be unique case-insensitively, after trimming whitespace. For v1, renaming a profile changes the display name but does not automatically rename the TOML ID.

The app should ship with starter profiles so a normal first run is immediately useful:

- NBSP cleanup
- Web text cleanup
- Plain text normalize
- Deduplicate lines
- ASCII-safe cleanup

If `profiles.toml` is missing, empty, invalid, or contains no usable profiles, the app opens directly into the New Profile flow. If the file failed to load, the TUI shows a clear warning and logs the error.

Profiles can be edited in-app and by hand. The in-app editor supports:

- creating a profile
- editing name and description
- toggling operations
- editing find/replace rules
- clearing all operations and replacement rules after confirmation
- deleting a profile after confirmation

Clearing a profile leaves the name and description intact. A profile with no operations is allowed and marked as "No operations selected" because it can be useful for pass-through testing. Deleting the last profile immediately enters New Profile flow.

## Cleaning Engine

The cleaning engine is separate from the TUI. It accepts input text and a profile, then returns cleaned text plus a small report:

```text
profile: NBSP cleanup
input: 4,203 chars
output: 3,918 chars
operations: unicode spaces to normal space, trim, collapse spaces
warnings: none
```

Supported v1 operations:

- convert NBSP and related Unicode spacing characters to normal ASCII spaces
- trim leading and trailing text
- remove blank lines
- collapse repeated spaces
- collapse repeated blank lines
- replace line breaks with spaces
- remove all line breaks
- uppercase
- lowercase
- sentence case
- capitalize words
- remove punctuation
- strip emoji
- remove accents and diacritics
- normalize Unicode
- remove non-ASCII characters
- remove non-alphanumeric characters
- convert smart quotes to plain quotes
- strip HTML tags
- decode HTML entities
- remove duplicate lines
- literal and regex find/replace rules

NBSP handling is explicit and not hidden behind generic Unicode normalization. `unicode_spaces_to_normal_space` runs before trim and space-collapse operations so NBSPs at text edges and inside text are handled predictably.

Cleaning runs in a predictable engine-defined order, not arbitrary UI order:

```text
decode/strip markup
normalize Unicode spacing, including NBSP
trim
line and space cleanup
case conversion
character removal
duplicate-line handling
find/replace rules
```

This ordering should be documented in the help text because it affects profile behavior.

## TUI Workflow

The app opens to a profile picker:

```text
Text Cleaner

> NBSP cleanup
  Web text cleanup
  Plain text normalize

NBSP cleanup
Convert NBSP/unicode spaces, trim, collapse repeated spaces

[Enter] Clean pasted text
[c] Clean clipboard now
[e] Edit profile
[n] New profile
[l] View logs
[q] Quit
```

Primary workflows:

- Paste mode: select a profile, paste text into an editor area, run cleaning, preview output, copy output.
- Clipboard mode: select a profile, press a key, read clipboard, clean it, write cleaned text back to clipboard, then show a short report.
- Profile mode: create and edit profile settings through checklists, simple fields, and replacement-rule controls.

The TUI shows each profile's display name, description, and operation summary. Last-modified timestamps are out of scope for v1.

## Config Validation And Writes

Config validation must prevent ambiguous profile selection and bad saves:

- duplicate profile IDs are invalid
- duplicate display names are invalid case-insensitively after trimming
- invalid operation names are blocked on save
- replacement rules require a non-empty `find` value
- regex replacement rules must compile before saving

Config writes should be defensive:

- validate before writing
- write to a temporary file
- replace `profiles.toml` atomically where possible
- keep `profiles.toml.bak` as the previous saved config
- show validation errors in the TUI instead of corrupting the config

## Logging And Diagnostics

The portable folder owns all normal logs:

```text
logs/
  text-cleaner.log
  startup-error.log
  diagnostics-YYYY-MM-DD-HHMMSS.log
```

Normal logs include:

- app startup and shutdown
- app version
- Python version
- OS and platform information
- working directory
- portable directory
- config path
- selected profile
- operations run
- input and output character counts
- clipboard success or failure
- full exception tracebacks

Raw input, output, and clipboard text are not logged by default. A future explicit debug mode may allow text-content logging, but it must warn clearly before enabling that because clipboard contents can be sensitive.

The TUI includes a diagnostics command that writes a timestamped log dump under `logs/`. This lets the user copy back a thorough debugging artifact after a Windows failure.

## Testing And Verification

The cleaning engine should carry most of the test coverage. Required coverage includes:

- each v1 operation
- operation ordering, especially HTML/entity decode before spacing cleanup and NBSP cleanup before trim/collapse
- profile config load and save
- duplicate profile ID and duplicate display-name validation
- invalid operation and replacement validation
- clipboard workflow boundaries with clipboard access mocked where needed
- logging setup and diagnostic dump creation
- `.pyz` build behavior
- Windows-style and POSIX-style path handling in build and launcher support code

The direct launch path `python text-cleaner.pyz` and the launcher paths should both be documented and verified.

## Deferred Scope

The first version intentionally defers specialized textcleaner.net-style operations that are less central to the current use case:

- BBCode tag removal
- email-address stripping
- URL removal and URL-to-link conversion
- fine-grained HTML attribute cleanup
- URL decoding
- smart quote generation
- remove N characters from left or right
- remove repeating words
- shorthand expansion
- tab/space conversion with configurable counts

These can be added later as new operations without changing the profile model.
