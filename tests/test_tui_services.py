from typing import Any

from text_cleaner import tui
from text_cleaner.clipboard import ClipboardError, ClipboardService
from text_cleaner.profiles import Profile, ReplacementRule


class FakeDialog:
    def __init__(self, calls: list[dict[str, Any]], **kwargs: Any) -> None:
        self.calls = calls
        self.kwargs = kwargs

    def run(self) -> None:
        self.calls.append(self.kwargs)


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


def test_clipboard_flow_success_cleans_text_and_logs_metadata(monkeypatch):
    dialog_calls = patch_message_dialog(monkeypatch)
    clipboard = FakeClipboard("\u00a0Hello\u00a0\u00a0World\u00a0")
    logger = FakeLogger()

    tui.clipboard_flow(nbsp_profile(), clipboard, logger)

    assert clipboard.text == "Hello World"
    assert clipboard.write_calls == ["Hello World"]
    assert len(logger.info_calls) == 1
    assert not logger.exception_calls
    assert len(dialog_calls) == 1
    assert dialog_calls[0]["title"] == "Clipboard cleaned"

    logged_args, logged_kwargs = logger.info_calls[0]
    logged_values = repr((logged_args, logged_kwargs))
    assert "\u00a0Hello\u00a0\u00a0World\u00a0" not in logged_values
    assert "Hello World" not in logged_values


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
    clipboard = FakeClipboard("\u00a0Hello\u00a0\u00a0World\u00a0", fail_write=True)
    logger = FakeLogger()

    tui.clipboard_flow(nbsp_profile(), clipboard, logger)

    assert clipboard.text == "\u00a0Hello\u00a0\u00a0World\u00a0"
    assert clipboard.write_calls == []
    assert not logger.info_calls
    assert len(logger.exception_calls) == 1
    assert len(dialog_calls) == 1
    assert dialog_calls[0] == {"title": "Clipboard error", "text": "write failed"}
