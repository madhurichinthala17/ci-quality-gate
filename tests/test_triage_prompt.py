"""Prompt-building and response-parsing tests — pure, no LLM."""

from __future__ import annotations

from quality_gate.parser.models import Status, TestResult
from quality_gate.triage.models import TriageCategory
from quality_gate.triage.prompt import build_prompt, parse_ticket


def _failing(detail: str = "boom", type_: str = "AssertionError") -> TestResult:
    return TestResult(
        id="t::a",
        name="a",
        classname="t",
        suite="s",
        status=Status.FAILED,
        duration=0.0,
        message="m",
        detail=detail,
        type=type_,
    )


def test_prompt_bounds_and_delimits_untrusted_output():
    system, user = build_prompt(_failing(detail="x" * 5000), char_limit=2000)
    assert user.count("x") == 2000  # detail truncated
    assert "BEGIN_UNTRUSTED_TEST_OUTPUT" in user  # delimited
    assert "only" in system.lower()  # grounding instruction present
    assert "do not decide" not in user.lower()  # sanity: instruction lives in system


def test_parse_valid_json():
    tk = parse_ticket(
        '{"category":"timeout","probable_cause":"slow endpoint","suggested_next_step":"raise timeout","grounded":true}',
        "t::a",
    )
    assert tk.category is TriageCategory.TIMEOUT
    assert tk.grounded


def test_parse_tolerates_prose_and_code_fences():
    tk = parse_ticket(
        'Sure:\n```json\n{"category":"assertion","probable_cause":"c","suggested_next_step":"s","grounded":true}\n```',
        "t::a",
    )
    assert tk.category is TriageCategory.ASSERTION


def test_parse_garbage_degrades_to_ungrounded_unknown():
    tk = parse_ticket("I can't help with that", "t::a")
    assert tk.category is TriageCategory.UNKNOWN
    assert not tk.grounded


def test_parse_invalid_category_falls_back_to_unknown():
    tk = parse_ticket('{"category":"weird","probable_cause":"c","suggested_next_step":"s"}', "t::a")
    assert tk.category is TriageCategory.UNKNOWN
    assert not tk.grounded
