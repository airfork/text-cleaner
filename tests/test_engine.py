import pytest

from text_cleaner.engine import clean_text
from text_cleaner.profiles import Profile, ReplacementRule


def test_clean_text_uses_engine_order_for_nbsp_then_trim_then_collapse():
    profile = Profile(
        "test",
        "Test",
        "Test profile",
        ["trim", "collapse_spaces", "unicode_spaces_to_normal_space"],
    )

    result = clean_text("\u00a0 hello\u00a0\u00a0world \u00a0", profile)

    assert result.text == "hello world"
    assert result.report.input_chars == 16
    assert result.report.output_chars == 11
    assert result.report.operations == (
        "unicode_spaces_to_normal_space",
        "trim",
        "collapse_spaces",
    )
    assert isinstance(result.report.operations, tuple)
    assert result.report.warnings == ()


def test_clean_text_applies_literal_replacements_after_operations():
    profile = Profile(
        "test",
        "Test",
        "Test profile",
        ["lowercase"],
        [ReplacementRule(find="hello", replace="hi", regex=False)],
    )

    result = clean_text("HELLO", profile)

    assert result.text == "hi"


def test_clean_text_applies_regex_replacements_after_operations():
    profile = Profile(
        "test",
        "Test",
        "Test profile",
        ["lowercase"],
        [ReplacementRule(find=r"h.llo", replace="hi", regex=True)],
    )

    result = clean_text("HELLO", profile)

    assert result.text == "hi"


def test_clean_text_rejects_unknown_operations():
    profile = Profile("test", "Test", "Test profile", ["typo"])

    with pytest.raises(ValueError, match="unknown operation.*typo"):
        clean_text("hello", profile)
