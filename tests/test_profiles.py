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
