from typing import Optional, Protocol


class ValidationLike(Protocol):
    verdict: str
    reasoning: str


PASS_VERDICTS = {"pass", "passed", "true", "success", "yes"}
FAIL_VERDICTS = {"fail", "failed", "false", "no"}


def normalize_verdict(verdict: str) -> str:
    normalized = verdict.strip().lower()
    if normalized in PASS_VERDICTS:
        return "pass"
    if normalized in FAIL_VERDICTS:
        return "fail"
    return "unknown"


def extract_suggestions(reason: str) -> list[str]:
    if not reason:
        return []
    suggestions: list[str] = []
    for line in reason.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("-"):
            stripped = stripped[1:].strip()
        suggestions.append(stripped)
    return suggestions


def build_assistant_hint(
    validation: Optional[ValidationLike],
    success_message: str,
) -> str:
    if validation is None or validation.verdict == "pass":
        return success_message
    return f"Validator suggests updates: {validation.reasoning}"


def build_final_guidance(
    validation: Optional[ValidationLike],
    success_message: str,
) -> str:
    if validation is None or validation.verdict == "pass":
        return success_message
    return validation.reasoning
