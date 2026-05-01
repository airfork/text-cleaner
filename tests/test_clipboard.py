from text_cleaner.clipboard import ClipboardService


def test_clipboard_service_reads_and_writes(monkeypatch):
    stored = {"value": "input"}

    monkeypatch.setattr("pyperclip.paste", lambda: stored["value"])
    monkeypatch.setattr("pyperclip.copy", lambda value: stored.__setitem__("value", value))

    service = ClipboardService()

    assert service.read_text() == "input"
    service.write_text("output")
    assert stored["value"] == "output"
