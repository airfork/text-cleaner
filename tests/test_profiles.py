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
    assert isinstance(profiles["nbsp_cleanup"].operations, tuple)


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


@pytest.mark.parametrize(
    "profile_id",
    [
        "",
        " bad",
        "bad ",
        "Bad",
        "bad name",
        "bad-name",
        "bad/name",
        "../bad",
    ],
)
def test_validate_rejects_invalid_profile_ids(profile_id):
    profiles = {
        profile_id: Profile(profile_id, "Name", "description", ["trim"]),
    }

    with pytest.raises(ProfileValidationError, match="profile id"):
        validate_profiles(profiles)


def test_validate_keeps_key_profile_id_mismatch_validation():
    profiles = {
        "profile": Profile("other", "Name", "description", ["trim"]),
    }

    with pytest.raises(ProfileValidationError, match="profile key mismatch"):
        validate_profiles(profiles)


def test_validate_rejects_invalid_operation():
    profiles = {
        "bad": Profile("bad", "Bad", "description", ["not_an_operation"]),
    }

    with pytest.raises(ProfileValidationError, match="invalid operation"):
        validate_profiles(profiles)


def test_validate_rejects_invalid_regex_as_profile_validation_error():
    profiles = {
        "bad": Profile(
            "bad",
            "Bad",
            "description",
            [],
            [ReplacementRule(find="[", replace="", regex=True)],
        ),
    }

    with pytest.raises(ProfileValidationError, match="invalid replacement regex"):
        validate_profiles(profiles)


def test_profile_constructor_converts_mutable_lists_to_tuples():
    rule = ReplacementRule(find="old", replace="new", regex=False)
    operations = ["trim"]
    replacements = [rule]
    profile = Profile("profile", "Name", "description", operations, replacements)

    operations.append("collapse_spaces")
    replacements.append(ReplacementRule(find="x", replace="y", regex=False))

    assert profile.operations == ("trim",)
    assert profile.replacements == (rule,)


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


def test_load_profiles_wraps_malformed_toml(tmp_path):
    path = tmp_path / "profiles.toml"
    path.write_text("[profiles.bad\n", encoding="utf-8")

    with pytest.raises(ProfileValidationError, match="invalid TOML"):
        load_profiles(path)


def test_load_profiles_rejects_profiles_that_is_not_table(tmp_path):
    path = tmp_path / "profiles.toml"
    path.write_text("profiles = []\n", encoding="utf-8")

    with pytest.raises(ProfileValidationError, match="profiles must be a table"):
        load_profiles(path)


def test_load_profiles_rejects_profile_entry_that_is_not_table(tmp_path):
    path = tmp_path / "profiles.toml"
    path.write_text(
        """
[profiles]
bad = "not a table"
""",
        encoding="utf-8",
    )

    with pytest.raises(ProfileValidationError, match="profile bad must be a table"):
        load_profiles(path)


def test_load_profiles_rejects_replacement_item_that_is_not_table(tmp_path):
    path = tmp_path / "profiles.toml"
    path.write_text(
        """
[profiles.bad]
name = "Bad"
description = "bad"
operations = ["trim"]
replacements = ["not a table"]
""",
        encoding="utf-8",
    )

    with pytest.raises(ProfileValidationError, match="replacement.*must be a table"):
        load_profiles(path)


@pytest.mark.parametrize(
    "operations",
    [
        '"trim"',
        '["trim", 1]',
    ],
)
def test_load_profiles_rejects_operations_that_are_not_list_of_strings(tmp_path, operations):
    path = tmp_path / "profiles.toml"
    path.write_text(
        f"""
[profiles.bad]
name = "Bad"
description = "bad"
operations = {operations}
""",
        encoding="utf-8",
    )

    with pytest.raises(ProfileValidationError, match="operations.*list of strings"):
        load_profiles(path)


def test_save_profiles_does_not_overwrite_existing_file_when_validation_fails(tmp_path):
    path = tmp_path / "profiles.toml"
    original = "[profiles.good]\nname = \"Good\"\n"
    path.write_text(original, encoding="utf-8")
    profiles = {
        "bad": Profile("bad", "Bad", "description", ["not_an_operation"]),
    }

    with pytest.raises(ProfileValidationError):
        save_profiles(path, profiles)

    assert path.read_text(encoding="utf-8") == original
    assert not path.with_suffix(path.suffix + ".bak").exists()
    assert not path.with_suffix(path.suffix + ".tmp").exists()
