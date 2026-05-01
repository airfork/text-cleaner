from __future__ import annotations

import pyperclip


class ClipboardError(RuntimeError):
    pass


class ClipboardService:
    def read_text(self) -> str:
        try:
            return pyperclip.paste() or ""
        except pyperclip.PyperclipException as exc:
            raise ClipboardError("failed to read from clipboard") from exc

    def write_text(self, text: str) -> None:
        try:
            pyperclip.copy(text)
        except pyperclip.PyperclipException as exc:
            raise ClipboardError("failed to write to clipboard") from exc
