import asyncio
from pathlib import Path
from typing import Any

import pytest

from text_cleaner import tui
from text_cleaner.profiles import Profile, ProfileValidationError, ReplacementRule


class FakeRepository:
    def __init__(self, profiles: dict[str, Profile] | Exception) -> None:
        self.profiles = profiles
        self.saved: list[dict[str, Profile]] = []
        self.path = "profiles.toml"

    def load_or_create(self) -> dict[str, Profile]:
        if isinstance(self.profiles, Exception):
            raise self.profiles
        return self.profiles

    def save(self, profiles: dict[str, Profile]) -> None:
        self.saved.append(profiles)


class FakeLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.exception_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def info(self, *args: Any, **kwargs: Any) -> None:
        self.info_calls.append((args, kwargs))

    def exception(self, *args: Any, **kwargs: Any) -> None:
        self.exception_calls.append((args, kwargs))


class FakeClipboard:
    def __init__(self, value: str) -> None:
        self.value = value
        self.writes: list[str] = []

    def read_text(self) -> str:
        return self.value

    def write_text(self, value: str) -> None:
        self.value = value
        self.writes.append(value)


def test_operation_summary_returns_empty_message_for_profile_without_actions():
    profile = Profile("empty", "Empty", "No cleanup yet")

    assert tui.operation_summary(profile) == "No operations selected"


def test_operation_summary_includes_operations_and_replacement_count():
    profile = Profile(
        "custom",
        "Custom",
        "Cleanup",
        ["trim", "collapse_spaces"],
        [ReplacementRule("A", "B"), ReplacementRule("C", "D")],
    )

    assert tui.operation_summary(profile) == "trim, collapse_spaces, 2 replacement rule(s)"


def test_profile_id_from_name_normalizes_to_ascii_underscore_id():
    assert tui.profile_id_from_name("  Crème brûlée cleanup!!  ") == "creme_brulee_cleanup"


def test_profile_id_from_name_uses_default_when_no_usable_chars():
    assert tui.profile_id_from_name("  !!!  ") == "profile"


def test_next_profile_id_appends_suffix_until_unique():
    profiles = {
        "custom": Profile("custom", "Custom", "description"),
        "custom_2": Profile("custom_2", "Custom 2", "description"),
    }

    assert tui.next_profile_id("custom", profiles) == "custom_3"


def test_clear_profile_actions_removes_operations_and_replacements():
    profiles = {
        "custom": Profile(
            "custom",
            "Custom",
            "description",
            ["trim"],
            [ReplacementRule("old", "new")],
        ),
    }

    updated = tui.clear_profile_actions(profiles, "custom")

    assert updated["custom"] == Profile("custom", "Custom", "description")


def test_delete_profile_removes_selected_profile():
    profiles = {
        "custom": Profile("custom", "Custom", "description"),
        "other": Profile("other", "Other", "description"),
    }

    updated = tui.delete_profile(profiles, "custom")

    assert updated == {"other": Profile("other", "Other", "description")}


def test_save_profile_update_writes_repository_and_keeps_change():
    repository = FakeRepository({})
    profiles: dict[str, Profile] = {
        "custom": Profile("custom", "Custom", "old description"),
    }
    updated = Profile("custom", "Custom", "new description", ["trim"])

    tui.save_profile_update(repository, profiles, "custom", updated)

    assert profiles["custom"] == updated
    assert repository.saved == [{"custom": updated}]


def test_save_profile_update_reverts_on_validation_error():
    class FailingRepository(FakeRepository):
        def save(self, profiles: dict[str, Profile]) -> None:
            raise ProfileValidationError("bad data")

    repository = FailingRepository({})
    original = Profile("custom", "Custom", "old description")
    profiles: dict[str, Profile] = {"custom": original}
    updated = Profile("custom", "Custom", "broken", ["trim"])

    try:
        tui.save_profile_update(repository, profiles, "custom", updated)
    except ProfileValidationError:
        pass
    else:
        raise AssertionError("expected ProfileValidationError")

    assert profiles["custom"] is original


def test_load_profiles_for_tui_returns_profiles_on_success():
    profiles = {"custom": Profile("custom", "Custom", "description")}
    repository = FakeRepository(profiles)
    logger = FakeLogger()

    loaded = tui.load_profiles_for_tui(repository, logger)

    assert loaded == profiles
    assert logger.info_calls == []


def test_load_profiles_for_tui_reports_validation_failure():
    error = ProfileValidationError("bad profile")
    repository = FakeRepository(error)
    logger = FakeLogger()

    loaded = tui.load_profiles_for_tui(repository, logger)

    assert isinstance(loaded, tuple)
    assert loaded[0] is None
    assert "could not be loaded" in loaded[1]

    assert len(logger.info_calls) == 1
    logged_values = repr(logger.info_calls[0])
    assert "bad profile" not in logged_values


@pytest.mark.parametrize("confirm_key", ["enter", "c"])
def test_clipboard_preview_keyboard_confirmation_copies_cleaned_text(confirm_key: str):
    async def run_flow() -> FakeClipboard:
        clipboard = FakeClipboard("Text with whitespace after it                          ")
        profile = Profile(
            "nbsp_cleanup",
            "NBSP cleanup",
            "Convert NBSP/unicode spaces, trim, collapse repeated spaces",
            ["unicode_spaces_to_normal_space", "trim", "collapse_spaces"],
        )
        app = tui.TextCleanerApp(
            repository=FakeRepository({"nbsp_cleanup": profile}),
            clipboard=clipboard,  # type: ignore[arg-type]
            portable_dir=Path("."),
            logger=FakeLogger(),  # type: ignore[arg-type]
            initial_profiles={"nbsp_cleanup": profile},
        )

        async with app.run_test() as pilot:
            await pilot.pause()
            await pilot.press("c")
            await pilot.pause()
            await pilot.press(confirm_key)
            await pilot.pause()

        return clipboard

    clipboard = asyncio.run(run_flow())

    assert clipboard.writes == ["Text with whitespace after it"]
