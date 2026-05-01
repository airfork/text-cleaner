from __future__ import annotations

import logging
from pathlib import Path

from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import (
    button_dialog,
    checkboxlist_dialog,
    input_dialog,
    message_dialog,
    radiolist_dialog,
)

from text_cleaner.clipboard import ClipboardError, ClipboardService
from text_cleaner.engine import clean_text
from text_cleaner.logging_setup import write_diagnostics
from text_cleaner.profiles import (
    VALID_OPERATIONS,
    Profile,
    ProfileRepository,
    ProfileValidationError,
)

OUTPUT_PREVIEW_CHARS = 4000


def operation_summary(profile: Profile) -> str:
    if not profile.operations and not profile.replacements:
        return "No operations selected"

    pieces = list(profile.operations)
    if profile.replacements:
        pieces.append(f"{len(profile.replacements)} replacement rule(s)")
    return ", ".join(pieces)


def choose_profile(profiles: dict[str, Profile]) -> str | None:
    values = [
        (
            profile_id,
            f"{profile.name} - {profile.description} ({operation_summary(profile)})",
        )
        for profile_id, profile in profiles.items()
    ]
    return radiolist_dialog(
        title="Text Cleaner",
        text="Choose a profile",
        values=values,
    ).run()


def paste_flow(
    profile: Profile,
    clipboard: ClipboardService,
    logger: logging.Logger,
) -> None:
    text = prompt("Paste text. Press Esc+Enter when finished:\n", multiline=True)
    result = clean_text(text, profile)
    logger.info(
        "paste_flow profile=%s input_chars=%s output_chars=%s operations=%s",
        profile.profile_id,
        result.report.input_chars,
        result.report.output_chars,
        result.report.operations,
    )

    message_dialog(title="Cleaned Output", text=result.text[:OUTPUT_PREVIEW_CHARS]).run()
    should_copy = button_dialog(
        title="Copy output",
        text=f"Output has {result.report.output_chars} chars. Copy to clipboard?",
        buttons=[("Copy", True), ("Skip", False)],
    ).run()
    if not should_copy:
        return

    try:
        clipboard.write_text(result.text)
    except ClipboardError as exc:
        logger.exception("paste_copy_failed profile=%s", profile.profile_id)
        message_dialog(title="Clipboard error", text=str(exc)).run()


def clipboard_flow(
    profile: Profile,
    clipboard: ClipboardService,
    logger: logging.Logger,
) -> None:
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
    name = input_dialog(
        title="Profile name",
        text="Display name:",
        default=profile.name,
    ).run()
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
        selected,
        profile.replacements,
    )


def run_tui(portable_dir: Path, logger: logging.Logger) -> int:
    repository = ProfileRepository(portable_dir / "profiles.toml")
    clipboard = ClipboardService()
    profiles = repository.load_or_create()

    while True:
        if not profiles:
            message_dialog(
                title="No profiles",
                text="No profiles are configured. Defaults will be restored.",
            ).run()
            profiles = repository.load_or_create()
            continue

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
            updated = edit_profile(profile)
            if updated == profile:
                continue
            try:
                profiles[profile_id] = updated
                repository.save(profiles)
            except ProfileValidationError as exc:
                profiles[profile_id] = profile
                logger.exception("profile_edit_failed profile=%s", profile.profile_id)
                message_dialog(title="Profile error", text=str(exc)).run()
        elif action == "logs":
            dump = write_diagnostics(portable_dir)
            logger.info("diagnostics_written path=%s", dump)
            message_dialog(title="Diagnostics written", text=str(dump)).run()
        elif action == "quit" or action is None:
            return 0
