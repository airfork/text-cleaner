from text_cleaner.clipboard import ClipboardService
from text_cleaner.engine import clean_text
from text_cleaner.profiles import Profile


class FakeClipboard(ClipboardService):
    def __init__(self, text: str) -> None:
        self.text = text

    def read_text(self) -> str:
        return self.text

    def write_text(self, text: str) -> None:
        self.text = text


def test_clipboard_clean_flow_uses_selected_profile():
    clipboard = FakeClipboard("\u00a0Hello\u00a0\u00a0World\u00a0")
    profile = Profile(
        "nbsp_cleanup",
        "NBSP cleanup",
        "Clean spaces",
        ["unicode_spaces_to_normal_space", "trim", "collapse_spaces"],
    )

    result = clean_text(clipboard.read_text(), profile)
    clipboard.write_text(result.text)

    assert clipboard.text == "Hello World"
    assert result.report.operations == (
        "unicode_spaces_to_normal_space",
        "trim",
        "collapse_spaces",
    )
