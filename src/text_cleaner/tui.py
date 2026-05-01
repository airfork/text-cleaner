from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import MutableMapping
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
    ReplacementRule,
    default_profiles,
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


def profile_id_from_name(name: str) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    )
    profile_id = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    profile_id = re.sub(r"_+", "_", profile_id)
    return profile_id or "profile"


def next_profile_id(base: str, profiles: dict[str, Profile]) -> str:
    candidate = base
    suffix = 2
    while candidate in profiles:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def clear_profile_actions(
    profiles: dict[str, Profile],
    profile_id: str,
) -> dict[str, Profile]:
    profile = profiles[profile_id]
    updated = dict(profiles)
    updated[profile_id] = Profile(
        profile.profile_id,
        profile.name,
        profile.description,
    )
    return updated


def delete_profile(
    profiles: dict[str, Profile],
    profile_id: str,
) -> dict[str, Profile]:
    updated = dict(profiles)
    del updated[profile_id]
    return updated


def new_profile(profiles: dict[str, Profile]) -> Profile | None:
    name = input_dialog(
        title="New profile",
        text="Display name:",
    ).run()
    if name is None:
        return None
    name = name.strip()
    if not name:
        message_dialog(title="Profile error", text="Profile name cannot be empty.").run()
        return None

    description = input_dialog(
        title="Profile description",
        text="Short hint:",
    ).run()
    if description is None:
        return None

    selected = checkboxlist_dialog(
        title="Operations",
        text="Choose operations",
        values=[(operation, operation) for operation in sorted(VALID_OPERATIONS)],
        default_values=[],
    ).run()
    if selected is None:
        return None

    profile_id = next_profile_id(profile_id_from_name(name), profiles)
    return Profile(profile_id, name, description.strip(), selected)


def edit_replacements(profile: Profile) -> Profile:
    replacements = list(profile.replacements)
    while True:
        action = button_dialog(
            title="Replacements",
            text=f"{len(replacements)} replacement rule(s)",
            buttons=[
                ("Add replacement", "add"),
                ("Clear replacements", "clear"),
                ("Back", "back"),
            ],
        ).run()

        if action == "add":
            find = input_dialog(
                title="Find text",
                text="Find:",
            ).run()
            if find is None:
                continue
            if not find:
                message_dialog(
                    title="Replacement error",
                    text="Find text cannot be empty.",
                ).run()
                continue

            replace = input_dialog(
                title="Replace text",
                text="Replace with:",
            ).run()
            if replace is None:
                continue

            regex = button_dialog(
                title="Replacement type",
                text="Use regex matching?",
                buttons=[("Literal", False), ("Regex", True), ("Cancel", None)],
            ).run()
            if regex is None:
                continue

            replacements.append(
                ReplacementRule(find=find, replace=replace, regex=bool(regex)),
            )
        elif action == "clear":
            confirmed = button_dialog(
                title="Clear replacements",
                text="Remove all replacement rules from this profile?",
                buttons=[("Clear", True), ("Cancel", False)],
            ).run()
            if confirmed:
                replacements.clear()
        else:
            return Profile(
                profile.profile_id,
                profile.name,
                profile.description,
                profile.operations,
                replacements,
            )


def recover_profiles(
    repository: ProfileRepository,
    profiles: dict[str, Profile],
) -> dict[str, Profile] | None:
    while True:
        action = button_dialog(
            title="No profiles",
            text="No profiles are configured.",
            buttons=[
                ("New profile", "new"),
                ("Restore defaults", "defaults"),
                ("Quit", "quit"),
            ],
        ).run()

        if action == "new":
            profile = new_profile(profiles)
            if profile is None:
                continue
            updated = {**profiles, profile.profile_id: profile}
            repository.save(updated)
            return updated
        if action == "defaults":
            updated = default_profiles()
            repository.save(updated)
            return updated
        return None


def load_profiles_for_tui(
    repository: ProfileRepository,
    logger: logging.Logger,
) -> dict[str, Profile] | None:
    try:
        return repository.load_or_create()
    except ProfileValidationError as exc:
        logger.info(
            "profile_load_failed error_type=%s cause_type=%s config_path=%s",
            type(exc).__name__,
            type(exc.__cause__).__name__ if exc.__cause__ else None,
            getattr(repository, "path", "profiles.toml"),
        )
        message_dialog(
            title="Profiles error",
            text=(
                "profiles.toml could not be loaded. "
                "Create a new profile, restore defaults, or quit."
            ),
        ).run()
        return recover_profiles(repository, {})


def save_profile_update(
    repository: ProfileRepository,
    profiles: MutableMapping[str, Profile],
    profile_id: str,
    updated: Profile,
) -> None:
    previous = profiles[profile_id]
    try:
        profiles[profile_id] = updated
        repository.save(dict(profiles))
    except ProfileValidationError:
        profiles[profile_id] = previous
        raise


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
    profiles = load_profiles_for_tui(repository, logger)
    if profiles is None:
        return 0

    while True:
        if not profiles:
            recovered = recover_profiles(repository, profiles)
            if recovered is None:
                return 0
            profiles = recovered
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
                ("Replacements", "replacements"),
                ("New", "new"),
                ("Clear", "clear"),
                ("Delete", "delete"),
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
                save_profile_update(repository, profiles, profile_id, updated)
            except ProfileValidationError as exc:
                logger.info(
                    "profile_edit_failed profile=%s error_type=%s",
                    profile.profile_id,
                    type(exc).__name__,
                )
                message_dialog(title="Profile error", text=str(exc)).run()
        elif action == "replacements":
            updated = edit_replacements(profile)
            if updated == profile:
                continue
            try:
                save_profile_update(repository, profiles, profile_id, updated)
            except ProfileValidationError as exc:
                logger.info(
                    "profile_replacements_failed profile=%s error_type=%s",
                    profile.profile_id,
                    type(exc).__name__,
                )
                message_dialog(title="Profile error", text=str(exc)).run()
        elif action == "new":
            profile = new_profile(profiles)
            if profile is None:
                continue
            try:
                profiles[profile.profile_id] = profile
                repository.save(profiles)
            except ProfileValidationError as exc:
                del profiles[profile.profile_id]
                logger.info(
                    "profile_create_failed profile=%s error_type=%s",
                    profile.profile_id,
                    type(exc).__name__,
                )
                message_dialog(title="Profile error", text=str(exc)).run()
        elif action == "clear":
            confirmed = button_dialog(
                title="Clear profile",
                text="Remove all operations and replacements from this profile?",
                buttons=[("Clear", True), ("Cancel", False)],
            ).run()
            if confirmed:
                profiles = repository.clear_profile(profiles, profile_id)
        elif action == "delete":
            confirmed = button_dialog(
                title="Delete profile",
                text=f"Delete profile '{profile.name}'?",
                buttons=[("Delete", True), ("Cancel", False)],
            ).run()
            if confirmed:
                profiles = repository.delete_profile(profiles, profile_id)
        elif action == "logs":
            dump = write_diagnostics(portable_dir)
            logger.info("diagnostics_written path=%s", dump)
            message_dialog(title="Diagnostics written", text=str(dump)).run()
        elif action == "quit" or action is None:
            return 0
