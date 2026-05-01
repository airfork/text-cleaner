from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Callable

import emoji

from text_cleaner.profiles import VALID_OPERATIONS

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
    return re.sub(r"[ \t]*(?:\r\n|\r|\n)[ \t]*", " ", text)


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


def capitalize_words(text: str) -> str:
    return re.sub(r"\S+", lambda match: match.group(0).capitalize(), text)


def normalize_unicode(text: str) -> str:
    parts: list[str] = []
    segment: list[str] = []

    for ch in text:
        if unicodedata.category(ch) == "Zs":
            if segment:
                parts.append(unicodedata.normalize("NFKC", "".join(segment)))
                segment.clear()
            parts.append(ch)
        else:
            segment.append(ch)

    if segment:
        parts.append(unicodedata.normalize("NFKC", "".join(segment)))

    return "".join(parts)


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
    output: list[str] = []
    index = 0

    while index < len(text):
        ch = text[index]
        if ch != "<" or not _starts_html_tag(text, index):
            output.append(ch)
            index += 1
            continue

        end = _find_tag_end(text, index + 1)
        if end is None:
            output.append(ch)
            index += 1
            continue

        index = end + 1

    return "".join(output)


def _starts_html_tag(text: str, index: int) -> bool:
    next_index = index + 1
    return next_index < len(text) and (
        text[next_index].isalpha() or text[next_index] in "/!?"
    )


def _find_tag_end(text: str, index: int) -> int | None:
    quote: str | None = None

    while index < len(text):
        ch = text[index]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == ">":
            return index
        index += 1

    return None


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
    "capitalize_words": capitalize_words,
    "remove_punctuation": remove_punctuation,
    "strip_emoji": lambda text: emoji.replace_emoji(text, replace=""),
    "remove_accents": remove_accents,
    "normalize_unicode": normalize_unicode,
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
    "smart_quotes_to_plain",
    "remove_punctuation",
    "strip_emoji",
    "remove_accents",
    "remove_non_ascii",
    "remove_non_alphanumeric",
    "remove_duplicate_lines",
]
