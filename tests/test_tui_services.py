from typing import Any

from text_cleaner import tui
from text_cleaner.clipboard import ClipboardError, ClipboardService
from text_cleaner.profiles import Profile, ReplacementRule


class FakeDialog:
    def __init__(
        self,
        calls: list[dict[str, Any]],
        result: Any = None,
        **kwargs: Any,
    ) -> None:
        self.calls = calls
        self.kwargs = kwargs
        self.result = result

    def run(self) -> Any:
        self.calls.append(self.kwargs)
        return self.result


class FakeRepository:
    def __init__(self, profiles: dict[str, Profile] | Exception) -> None:
        self.profiles = profiles
        self.saved: list[dict[str, Profile]] = []

    def load_or_create(self) -> dict[str, Profile]:
        if isinstance(self.profiles, Exception):
            raise self.profiles
        return self.profiles

    def save(self, profiles: dict[str, Profile]) -> None:
        self.saved.append(profiles)

    def clear_profile(
        self,
        profiles: dict[str, Profile],
        profile_id: str,
    ) -> dict[str, Profile]:
        updated = tui.clear_profile_actions(profiles, profile_id)
        self.save(updated)
        return updated

    def delete_profile(
        self,
        profiles: dict[str, Profile],
        profile_id: str,
    ) -> dict[str, Profile]:
        updated = tui.delete_profile(profiles, profile_id)
        self.save(updated)
        return updated


class FakeClipboard(ClipboardService):
    def __init__(
        self,
        text: str = "",
        *,
        fail_read: bool = False,
        fail_write: bool = False,
    ) -> None:
        self.text = text
        self.fail_read = fail_read
        self.fail_write = fail_write
        self.write_calls: list[str] = []

    def read_text(self) -> str:
        if self.fail_read:
            raise ClipboardError("read failed")
        return self.text

    def write_text(self, text: str) -> None:
        if self.fail_write:
            raise ClipboardError("write failed")
        self.write_calls.append(text)
        self.text = text


class FakeLogger:
    def __init__(self) -> None:
        self.info_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.exception_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def info(self, *args: Any, **kwargs: Any) -> None:
        self.info_calls.append((args, kwargs))

    def exception(self, *args: Any, **kwargs: Any) -> None:
        self.exception_calls.append((args, kwargs))


def nbsp_profile() -> Profile:
    return Profile(
        "nbsp_cleanup",
        "NBSP cleanup",
        "Clean spaces",
        ["unicode_spaces_to_normal_space", "trim", "collapse_spaces"],
    )


def patch_message_dialog(monkeypatch) -> list[dict[str, Any]]:
    dialog_calls: list[dict[str, Any]] = []

    def fake_message_dialog(**kwargs: Any) -> FakeDialog:
        return FakeDialog(dialog_calls, **kwargs)

    monkeypatch.setattr(tui, "message_dialog", fake_message_dialog)
    return dialog_calls


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


def test_new_profile_collects_fields_and_generates_unique_id(monkeypatch):
    inputs = iter(["Custom Cleanup", "My cleanup"])
    checklist_calls: list[dict[str, Any]] = []

    def fake_input_dialog(**kwargs: Any) -> FakeDialog:
        return FakeDialog([], next(inputs), **kwargs)

    def fake_checkboxlist_dialog(**kwargs: Any) -> FakeDialog:
        return FakeDialog(checklist_calls, ["trim", "collapse_spaces"], **kwargs)

    monkeypatch.setattr(tui, "input_dialog", fake_input_dialog)
    monkeypatch.setattr(tui, "checkboxlist_dialog", fake_checkboxlist_dialog)

    profile = tui.new_profile(
        {"custom_cleanup": Profile("custom_cleanup", "Existing", "description")},
    )

    assert profile == Profile(
        "custom_cleanup_2",
        "Custom Cleanup",
        "My cleanup",
        ["trim", "collapse_spaces"],
    )
    assert checklist_calls[0]["default_values"] == []


def test_edit_replacements_adds_literal_replacement(monkeypatch):
    actions = iter(["add", "back"])
    inputs = iter(["old", "new"])

    def fake_button_dialog(**kwargs: Any) -> FakeDialog:
        if kwargs["title"] == "Replacement type":
            return FakeDialog([], False, **kwargs)
        return FakeDialog([], next(actions), **kwargs)

    def fake_input_dialog(**kwargs: Any) -> FakeDialog:
        return FakeDialog([], next(inputs), **kwargs)

    monkeypatch.setattr(tui, "button_dialog", fake_button_dialog)
    monkeypatch.setattr(tui, "input_dialog", fake_input_dialog)

    updated = tui.edit_replacements(Profile("custom", "Custom", "description"))

    assert updated.replacements == (ReplacementRule("old", "new", False),)


def test_edit_replacements_blocks_empty_find(monkeypatch):
    actions = iter(["add", "back"])
    inputs = iter([""])
    messages = patch_message_dialog(monkeypatch)

    def fake_button_dialog(**kwargs: Any) -> FakeDialog:
        return FakeDialog([], next(actions), **kwargs)

    def fake_input_dialog(**kwargs: Any) -> FakeDialog:
        return FakeDialog([], next(inputs), **kwargs)

    monkeypatch.setattr(tui, "button_dialog", fake_button_dialog)
    monkeypatch.setattr(tui, "input_dialog", fake_input_dialog)

    updated = tui.edit_replacements(Profile("custom", "Custom", "description"))

    assert updated.replacements == ()
    assert messages[0]["title"] == "Replacement error"


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


def test_recover_profiles_restores_defaults(monkeypatch):
    repository = FakeRepository({})
    monkeypatch.setattr(
        tui,
        "button_dialog",
        lambda **kwargs: FakeDialog([], "defaults", **kwargs),
    )

    profiles = tui.recover_profiles(repository, {})

    assert profiles is not None
    assert "nbsp_cleanup" in profiles
    assert repository.saved == [profiles]


def test_recover_profiles_creates_new_profile(monkeypatch):
    repository = FakeRepository({})
    profile = Profile("custom", "Custom", "description")
    monkeypatch.setattr(
        tui,
        "button_dialog",
        lambda **kwargs: FakeDialog([], "new", **kwargs),
    )
    monkeypatch.setattr(tui, "new_profile", lambda profiles: profile)

    profiles = tui.recover_profiles(repository, {})

    assert profiles == {"custom": profile}
    assert repository.saved == [profiles]


def test_load_profiles_for_tui_recovers_invalid_profile_file(monkeypatch):
    error = tui.ProfileValidationError("bad profile")
    repository = FakeRepository(error)
    logger = FakeLogger()
    recovered = {"custom": Profile("custom", "Custom", "description")}
    messages = patch_message_dialog(monkeypatch)
    monkeypatch.setattr(tui, "recover_profiles", lambda repo, profiles: recovered)

    profiles = tui.load_profiles_for_tui(repository, logger)

    assert profiles == recovered
    assert len(logger.exception_calls) == 0
    assert len(logger.info_calls) == 1
    logged_values = repr(logger.info_calls[0])
    assert "bad profile" not in logged_values
    assert messages[0]["title"] == "Profiles error"


def test_clipboard_flow_success_cleans_text_and_logs_metadata(monkeypatch):
    dialog_calls = patch_message_dialog(monkeypatch)
    confirmation_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        tui,
        "button_dialog",
        lambda **kwargs: FakeDialog(confirmation_calls, True, **kwargs),
    )
    clipboard = FakeClipboard("\u00a0Hello\u00a0\u00a0World\u00a0")
    logger = FakeLogger()

    tui.clipboard_flow(nbsp_profile(), clipboard, logger)

    assert clipboard.text == "Hello World"
    assert clipboard.write_calls == ["Hello World"]
    assert len(logger.info_calls) == 1
    assert not logger.exception_calls
    assert len(dialog_calls) == 1
    assert dialog_calls[0]["title"] == "Clipboard cleaned"
    assert len(confirmation_calls) == 1
    assert confirmation_calls[0]["title"] == "Clipboard preview"
    assert "Hello World" in confirmation_calls[0]["text"]

    logged_args, logged_kwargs = logger.info_calls[0]
    logged_values = repr((logged_args, logged_kwargs))
    assert "\u00a0Hello\u00a0\u00a0World\u00a0" not in logged_values
    assert "Hello World" not in logged_values


def test_clipboard_flow_cancel_leaves_clipboard_unchanged(monkeypatch):
    dialog_calls = patch_message_dialog(monkeypatch)
    confirmation_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        tui,
        "button_dialog",
        lambda **kwargs: FakeDialog(confirmation_calls, False, **kwargs),
    )
    clipboard = FakeClipboard("\u00a0Hello\u00a0\u00a0World\u00a0")
    logger = FakeLogger()

    tui.clipboard_flow(nbsp_profile(), clipboard, logger)

    assert clipboard.text == "\u00a0Hello\u00a0\u00a0World\u00a0"
    assert clipboard.write_calls == []
    assert len(logger.info_calls) == 1
    assert not logger.exception_calls
    assert dialog_calls == []
    assert confirmation_calls[0]["title"] == "Clipboard preview"


def test_clipboard_flow_read_failure_logs_exception_and_shows_error(monkeypatch):
    dialog_calls = patch_message_dialog(monkeypatch)
    clipboard = FakeClipboard(fail_read=True)
    logger = FakeLogger()

    tui.clipboard_flow(nbsp_profile(), clipboard, logger)

    assert clipboard.write_calls == []
    assert not logger.info_calls
    assert len(logger.exception_calls) == 1
    assert len(dialog_calls) == 1
    assert dialog_calls[0] == {"title": "Clipboard error", "text": "read failed"}


def test_clipboard_flow_write_failure_logs_exception_and_shows_error(monkeypatch):
    dialog_calls = patch_message_dialog(monkeypatch)
    monkeypatch.setattr(
        tui,
        "button_dialog",
        lambda **kwargs: FakeDialog([], True, **kwargs),
    )
    clipboard = FakeClipboard("\u00a0Hello\u00a0\u00a0World\u00a0", fail_write=True)
    logger = FakeLogger()

    tui.clipboard_flow(nbsp_profile(), clipboard, logger)

    assert clipboard.text == "\u00a0Hello\u00a0\u00a0World\u00a0"
    assert clipboard.write_calls == []
    assert not logger.info_calls
    assert len(logger.exception_calls) == 1
    assert len(dialog_calls) == 1
    assert dialog_calls[0] == {"title": "Clipboard error", "text": "write failed"}
