"""File triage tickets as GitHub Issues, deduped — the CI ticket-filing step.

Reads a triage-report.json and creates one issue per ticket via the `gh` CLI,
skipping any whose title already exists (so re-runs don't spam). No-ops cleanly
when there's no report, no tickets, or no `gh` available. Kept as an importable
module so the non-gh logic is unit-testable; CI invokes `python -m quality_gate.issues`.
"""

from __future__ import annotations

import json
import subprocess
import sys


def _issue_title(ticket: dict) -> str:
    return f"[quality-gate] {ticket['test_id']} ({ticket['category']})"


def _issue_body(ticket: dict) -> str:
    return (
        f"**Probable cause:** {ticket['probable_cause']}\n\n"
        f"**Suggested next step:** {ticket['suggested_next_step']}\n\n"
        f"_category: {ticket['category']} · grounded: {ticket['grounded']}_\n\n"
        "<sub>Filed automatically by the CI quality gate.</sub>"
    )


def _existing_open_titles() -> set[str]:
    try:
        out = subprocess.run(
            ["gh", "issue", "list", "--state", "open", "--limit", "200", "--json", "title"],
            capture_output=True, text=True, check=True,
        ).stdout
        return {i["title"] for i in json.loads(out or "[]")}
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        return set()  # no gh / not authenticated -> treat as nothing existing


def file_tickets(report_path: str) -> int:
    try:
        with open(report_path, encoding="utf-8") as f:
            tickets = json.load(f).get("tickets", [])
    except FileNotFoundError:
        print(f"no triage report at {report_path}; nothing to file")
        return 0

    if not tickets:
        print("no tickets to file")
        return 0

    existing = _existing_open_titles()
    created = 0
    for ticket in tickets:
        title = _issue_title(ticket)
        if title in existing:
            print(f"skip (issue already open): {title}")
            continue
        try:
            subprocess.run(
                ["gh", "issue", "create", "--title", title, "--body", _issue_body(ticket)],
                check=True,
            )
            created += 1
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            print(f"could not create issue for {title}: {exc}")
    print(f"filed {created} new ticket(s)")
    return 0


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "triage-report.json"
    sys.exit(file_tickets(path))
