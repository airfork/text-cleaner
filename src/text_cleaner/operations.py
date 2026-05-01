from __future__ import annotations

import html
import re
import string
import unicodedata
from collections.abc import Callable
from html.parser import HTMLParser

import emoji

from text_cleaner.profiles import VALID_OPERATIONS


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


SMART_QUOTES = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
}


def apply_operation(operation: str, text: str) -> str:
    return OPERATIONS[operation](text)


def unicode_spaces_to_normal_space(text: str) -> str:
    return "".join(" " if unicodedata.category(ch) == "Zs" else ch for ch in text)


def trim(text: str) -> str:
    return text.strip()


def remove_blank_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if line.strip())


def collapse_spaces(text: str) -> str:
    return re.sub(r"[ \t\f\v]+", " ", text)


def collapse_blank_lines(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", normalized)


def line_breaks_to_spaces(text: str) -> str:
    return re.sub(r"[ \t]*\r?\n[ \t]*", " ", text)


def remove_line_breaks(text: str) -> str:
    return text.replace("\r\n", "").replace("\n", "").replace("\r", "")


def sentence_case(text: str) -> str:
    lowered = text.lower()
    chars = list(lowered)
    capitalize_next = True

    for index, char in enumerate(chars):
        if capitalize_next and char.isalpha():
            chars[index] = char.upper()
            capitalize_next = False
        if char in ".!?":
            capitalize_next = True

    return "".join(chars)


def remove_punctuation(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch)[0] != "P")


def remove_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def remove_non_ascii(text: str) -> str:
    return "".join(ch for ch in text if ord(ch) < 128)


def remove_non_alphanumeric(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum() or ch.isspace())


def smart_quotes_to_plain(text: str) -> str:
    return "".join(SMART_QUOTES.get(ch, ch) for ch in text)


def strip_html_tags(text: str) -> str:
    parser = _TextExtractor()
    parser.feed(text)
    return parser.text()


def remove_duplicate_lines(text: str) -> str:
    seen: set[str] = set()
    output: list[str] = []

    for line in text.splitlines():
        if line not in seen:
            seen.add(line)
            output.append(line)

    return "\n".join(output)


OPERATIONS: dict[str, Callable[[str], str]] = {
    "unicode_spaces_to_normal_space": unicode_spaces_to_normal_space,
    "trim": trim,
    "remove_blank_lines": remove_blank_lines,
    "collapse_spaces": collapse_spaces,
    "collapse_blank_lines": collapse_blank_lines,
    "line_breaks_to_spaces": line_breaks_to_spaces,
    "remove_line_breaks": remove_line_breaks,
    "uppercase": str.upper,
    "lowercase": str.lower,
    "sentence_case": sentence_case,
    "capitalize_words": string.capwords,
    "remove_punctuation": remove_punctuation,
    "strip_emoji": lambda text: emoji.replace_emoji(text, replace=""),
    "remove_accents": remove_accents,
    "normalize_unicode": lambda text: unicodedata.normalize("NFKC", text),
    "remove_non_ascii": remove_non_ascii,
    "remove_non_alphanumeric": remove_non_alphanumeric,
    "smart_quotes_to_plain": smart_quotes_to_plain,
    "strip_html_tags": strip_html_tags,
    "decode_html_entities": html.unescape,
    "remove_duplicate_lines": remove_duplicate_lines,
}

if set(OPERATIONS) != VALID_OPERATIONS:
    raise RuntimeError("operations must match profiles.VALID_OPERATIONS")


OPERATION_ORDER = [
    "strip_html_tags",
    "decode_html_entities",
    "normalize_unicode",
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
    "remove_non_ascii",
    "remove_non_alphanumeric",
    "smart_quotes_to_plain",
    "remove_duplicate_lines",
]
