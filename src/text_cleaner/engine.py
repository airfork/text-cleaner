from __future__ import annotations

import re
from dataclasses import dataclass

from text_cleaner.operations import OPERATION_ORDER, apply_operation
from text_cleaner.profiles import Profile


@dataclass(frozen=True)
class CleanReport:
    profile_id: str
    profile_name: str
    input_chars: int
    output_chars: int
    operations: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class CleanResult:
    text: str
    report: CleanReport


def clean_text(text: str, profile: Profile) -> CleanResult:
    selected = set(profile.operations)
    ordered = [operation for operation in OPERATION_ORDER if operation in selected]

    output = text
    for operation in ordered:
        output = apply_operation(operation, output)

    for rule in profile.replacements:
        if rule.regex:
            output = re.sub(rule.find, rule.replace, output)
        else:
            output = output.replace(rule.find, rule.replace)

    return CleanResult(
        text=output,
        report=CleanReport(
            profile_id=profile.profile_id,
            profile_name=profile.name,
            input_chars=len(text),
            output_chars=len(output),
            operations=ordered,
            warnings=[],
        ),
    )
