import pyperclip
import pytest

from text_cleaner.clipboard import ClipboardError, ClipboardService


def test_clipboard_service_reads_and_writes(monkeypatch):
    stored = {"value": "input"}

    monkeypatch.setattr("pyperclip.paste", lambda: stored["value"])
    monkeypatch.setattr("pyperclip.copy", lambda value: stored.__setitem__("value", value))

    service = ClipboardService()

    assert service.read_text() == "input"
    service.write_text("output")
    assert stored["value"] == "output"


def test_clipboard_service_returns_empty_string_when_paste_returns_none(monkeypatch):
    monkeypatch.setattr("pyperclip.paste", lambda: None)

    service = ClipboardService()

    assert service.read_text() == ""


def test_clipboard_service_wraps_read_failures(monkeypatch):
    def fail() -> str:
        raise pyperclip.PyperclipException("paste failed")

    monkeypatch.setattr("pyperclip.paste", fail)

    service = ClipboardService()

    with pytest.raises(ClipboardError, match="failed to read"):
        service.read_text()


def test_clipboard_service_wraps_write_failures(monkeypatch):
    def fail(_value: str) -> None:
        raise pyperclip.PyperclipException("copy failed")

    monkeypatch.setattr("pyperclip.copy", fail)

    service = ClipboardService()

    with pytest.raises(ClipboardError, match="failed to write"):
        service.write_text("output")
