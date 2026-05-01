from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w


class ProfileValidationError(ValueError):
    pass


PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9_]+$")


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
    operations: tuple[str, ...] = field(default_factory=tuple)
    replacements: tuple[ReplacementRule, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "operations", tuple(self.operations))
        object.__setattr__(self, "replacements", tuple(self.replacements))


def normalize_display_name(name: str) -> str:
    return " ".join(name.strip().casefold().split())


def validate_profiles(profiles: dict[str, Profile]) -> None:
    seen_names: set[str] = set()
    for profile_id, profile in profiles.items():
        if profile_id != profile.profile_id:
            raise ProfileValidationError(f"profile key mismatch for {profile_id}")
        if not PROFILE_ID_PATTERN.fullmatch(profile_id):
            raise ProfileValidationError(
                "profile id must use lowercase ASCII letters, digits, and "
                f"underscores: {profile_id}"
            )

        normalized_name = normalize_display_name(profile.name)
        if not normalized_name:
            raise ProfileValidationError("profile name cannot be empty")
        if normalized_name in seen_names:
            raise ProfileValidationError(f"duplicate profile name: {profile.name}")
        seen_names.add(normalized_name)

        invalid = [
            operation for operation in profile.operations if operation not in VALID_OPERATIONS
        ]
        if invalid:
            raise ProfileValidationError(f"invalid operation for {profile_id}: {invalid[0]}")

        for rule in profile.replacements:
            if not rule.find:
                raise ProfileValidationError(f"replacement find cannot be empty for {profile_id}")
            if rule.regex:
                try:
                    re.compile(rule.find)
                except re.error as exc:
                    raise ProfileValidationError(
                        f"invalid replacement regex for {profile_id}: {rule.find}"
                    ) from exc


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
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ProfileValidationError(f"invalid TOML in {path}: {exc}") from exc

    raw_profiles = data.get("profiles", {})
    if not isinstance(raw_profiles, dict):
        raise ProfileValidationError("profiles must be a table")

    profiles: dict[str, Profile] = {}
    for profile_id, raw_profile in raw_profiles.items():
        if not isinstance(raw_profile, dict):
            raise ProfileValidationError(f"profile {profile_id} must be a table")

        operations = raw_profile.get("operations", [])
        if not isinstance(operations, list) or not all(
            isinstance(operation, str) for operation in operations
        ):
            raise ProfileValidationError(
                f"profile {profile_id} operations must be a list of strings"
            )

        raw_replacements = raw_profile.get("replacements", [])
        if not isinstance(raw_replacements, list):
            raise ProfileValidationError(f"profile {profile_id} replacements must be a list")

        replacements: list[ReplacementRule] = []
        for index, raw_rule in enumerate(raw_replacements):
            if not isinstance(raw_rule, dict):
                raise ProfileValidationError(
                    f"profile {profile_id} replacement {index} must be a table"
                )
            find = raw_rule.get("find", "")
            replace = raw_rule.get("replace", "")
            regex = raw_rule.get("regex", False)
            if not isinstance(find, str):
                raise ProfileValidationError(
                    f"profile {profile_id} replacement {index} find must be a string"
                )
            if not isinstance(replace, str):
                raise ProfileValidationError(
                    f"profile {profile_id} replacement {index} replace must be a string"
                )
            if not isinstance(regex, bool):
                raise ProfileValidationError(
                    f"profile {profile_id} replacement {index} regex must be a boolean"
                )
            replacements.append(ReplacementRule(find=find, replace=replace, regex=regex))

        name = raw_profile.get("name", "")
        description = raw_profile.get("description", "")
        if not isinstance(name, str):
            raise ProfileValidationError(f"profile {profile_id} name must be a string")
        if not isinstance(description, str):
            raise ProfileValidationError(f"profile {profile_id} description must be a string")

        profiles[profile_id] = Profile(
            profile_id=profile_id,
            name=name,
            description=description,
            operations=operations,
            replacements=replacements,
        )
    validate_profiles(profiles)
    return profiles


def profile_to_toml(profile: Profile) -> dict[str, Any]:
    data: dict[str, Any] = {
        "name": profile.name,
        "description": profile.description,
        "operations": list(profile.operations),
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

    data = {
        "profiles": {
            profile_id: profile_to_toml(profile)
            for profile_id, profile in profiles.items()
        }
    }
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(tomli_w.dumps(data), encoding="utf-8")
    temp.replace(path)
