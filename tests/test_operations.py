import pytest

from text_cleaner.operations import OPERATION_ORDER, OPERATIONS, apply_operation
from text_cleaner.profiles import VALID_OPERATIONS


@pytest.mark.parametrize(
    ("operation", "input_text", "expected"),
    [
        ("unicode_spaces_to_normal_space", "a\u00a0b\u2007c", "a b c"),
        ("trim", "  hello \n", "hello"),
        ("remove_blank_lines", "a\n\n \n b", "a\n b"),
        ("collapse_spaces", "a   b\t\tc", "a b c"),
        ("collapse_blank_lines", "a\n\n\nb", "a\n\nb"),
        ("line_breaks_to_spaces", "a\nb\r\nc", "a b c"),
        ("remove_line_breaks", "a\nb\r\nc", "abc"),
        ("uppercase", "Hello", "HELLO"),
        ("lowercase", "Hello", "hello"),
        ("sentence_case", "hello. next", "Hello. Next"),
        ("capitalize_words", "hello world", "Hello World"),
        ("capitalize_words", "hello\nworld", "Hello\nWorld"),
        ("remove_punctuation", "hello, world!", "hello world"),
        ("strip_emoji", "hi 😀 there", "hi  there"),
        ("remove_accents", "cafe\u0301 déjà", "cafe deja"),
        ("normalize_unicode", "\uff21", "A"),
        ("normalize_unicode", "e\u0301", "é"),
        ("normalize_unicode", "a\u00a0b", "a\u00a0b"),
        ("remove_non_ascii", "aé😀b", "ab"),
        ("remove_non_alphanumeric", "a-b c!", "ab c"),
        ("smart_quotes_to_plain", "“hi” ‘there’", "\"hi\" 'there'"),
        ("strip_html_tags", "<p>Hello <strong>world</strong></p>", "Hello world"),
        ("strip_html_tags", "AT&T", "AT&T"),
        ("strip_html_tags", "<p>AT&T</p>", "AT&T"),
        ("strip_html_tags", "<p>A&bogus;B</p>", "A&bogus;B"),
        ("decode_html_entities", "Tom&nbsp;&amp;&nbsp;Jerry", "Tom\u00a0&\u00a0Jerry"),
        ("remove_duplicate_lines", "a\nb\na\nc\nb", "a\nb\nc"),
        ("line_breaks_to_spaces", "a\rb", "a b"),
    ],
)
def test_apply_operation(operation, input_text, expected):
    assert apply_operation(operation, input_text) == expected


def test_strip_html_tags_preserves_entity_text_for_decode_operation():
    assert (
        apply_operation("strip_html_tags", "<p>Tom&nbsp;&amp;&nbsp;Jerry</p>")
        == "Tom&nbsp;&amp;&nbsp;Jerry"
    )


def test_operations_match_profile_valid_operations():
    assert set(OPERATIONS) == VALID_OPERATIONS


def test_operation_order_covers_all_operations_once():
    assert set(OPERATION_ORDER) == set(OPERATIONS)
    assert len(OPERATION_ORDER) == len(OPERATIONS)
