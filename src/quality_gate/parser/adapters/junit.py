"""JUnit-style XML adapter — the de-facto universal CI report format.

Despite the name, "JUnit XML" is not Java-specific: pytest (`--junitxml`), Jest,
Go, PHPUnit, Cypress and Playwright all emit this schema, and every major CI
system consumes it. That's why it is the first (and, for now, only) adapter.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import parse as et_parse

from ..models import Status, TestResult, TestRun


class JUnitAdapter:
    name = "junit"

    # JUnit reports are rooted at <testsuites> or a bare <testsuite>.
    # NUnit3 uses <test-run>, so it won't be claimed here.
    _ROOTS = {"testsuites", "testsuite"}

    def can_parse(self, root: Element) -> bool:
        return root.tag in self._ROOTS

    def parse(self, path: str | Path) -> TestRun:
        root = et_parse(path).getroot()
        run = TestRun()
        # .iter matches the root itself when it's a bare <testsuite>, and its
        # children when the root is <testsuites> — both shapes handled.
        for suite in root.iter("testsuite"):
            suite_name = suite.get("name", "")
            for case in suite.findall("testcase"):
                run.results.append(self._to_result(case, suite_name))
        return run

    @staticmethod
    def _to_result(case: Element, suite_name: str) -> TestResult:
        name = case.get("name", "")
        classname = case.get("classname", "")
        duration = float(case.get("time") or 0.0)

        # JUnit encodes the outcome as a child element; no child means passed.
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if failure is not None:
            status, node = Status.FAILED, failure
        elif error is not None:
            status, node = Status.ERROR, error
        elif skipped is not None:
            status, node = Status.SKIPPED, skipped
        else:
            status, node = Status.PASSED, None

        message = node.get("message") if node is not None else None
        detail = node.text.strip() if node is not None and node.text else None
        type_ = node.get("type") if node is not None else None

        test_id = f"{classname}::{name}" if classname else name
        return TestResult(
            id=test_id,
            name=name,
            classname=classname,
            suite=suite_name,
            status=status,
            duration=duration,
            message=message,
            detail=detail,
            type=type_,
        )
