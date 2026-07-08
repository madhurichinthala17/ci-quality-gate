# CI Quality Gate

**An intelligent CI/CD quality gate that parses test results, detects and quarantines flaky tests, decides whether a pull request may merge, and uses an LLM to *explain* failures — without ever letting the LLM decide the verdict.**

Built as a self-contained, zero-dependency Python core (standard library only), wrapped in a GitHub Actions workflow that publishes trend dashboards to GitHub Pages. It runs on its own test suite — the gate is dogfooded on every push.

---

## Why this exists

CI is noisy. A red build might be a real regression, or it might be the same timing-sensitive test that fails 1 run in 6 for no reason. Teams that can't tell the difference either merge broken code or learn to ignore red — both are expensive.

This project is a decision-maker that sits between the test run and the merge button and answers one question deterministically: **should this change be allowed to merge?** It backs that verdict with statistical flake detection and a plain-English triage note per failure, so engineers spend their attention on real problems.

## What it does

| Stage | Responsibility |
|-------|----------------|
| **Parse** | Read JUnit XML into a typed, framework-agnostic model via a pluggable adapter. |
| **Detect flakes** | Track each test across a rolling window; quarantine intermittent tests, block genuine regressions. |
| **Gate** | Run deterministic checks (coverage, failures, flake rate, defect-escape rate) and emit a single `PASS` / `WARN` / `FAIL` verdict with the right exit code. |
| **Triage** | Ask an LLM to classify each *real* failure and draft a remediation note — advisory only, cost-capped, offline by default. |
| **Report** | Emit JSON verdicts, file deduplicated GitHub Issues, and publish Allure + metrics-trend dashboards to GitHub Pages. |

## Architecture

Layered / hexagonal design — dependencies point inward, toward a pure functional core. The outer shell (CLI, SQLite, LLM SDK, GitHub API) is swappable; the decision logic is pure and fully unit-tested offline.

```
                    ┌─────────────────────────────────────────┐
   junit.xml ──────▶│  parser/     JUnit XML → typed TestRun    │
                    │              (adapter Protocol, pluggable) │
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌─────────────────────────────────────────┐
   history.db ◀────▶│  flake/      rolling-window classifier    │
                    │              HEALTHY / FLAKY / REGRESSION  │
                    │              + quarantine state machine    │
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌─────────────────────────────────────────┐
   coverage.xml ───▶│  gate/       deterministic checks →       │
                    │              PASS / WARN / FAIL verdict    │  ← the authority
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌─────────────────────────────────────────┐
   OPENAI_API_KEY ─▶│  triage/     LLM classifies & explains    │  ← advisory only
                    │              cost-capped, provider-swappable│
                    └────────────────────┬─────────────────────┘
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │  cli.py (composition root) → dashboard/    │
                    │  issues.py → JSON, GitHub Issues, Pages    │
                    └─────────────────────────────────────────┘
```

The CLI is the **composition root**: it's the only place that knows which concrete adapters, store, and LLM provider get wired together. Everything below it depends on interfaces (`Protocol`s), not implementations.

## Design decisions worth defending

- **The gate is deterministic; the LLM is advisory.** The merge verdict comes entirely from statistical checks you can reproduce and audit. The LLM only *explains* failures it's given — it never votes on pass/fail. This is deliberate: a non-deterministic model must not gate your release.

- **Flakes are caught fast, not slowly.** A test is treated as *real* by default — a failure on build #1 blocks. A test is only reclassified as flaky once there's genuine evidence: intermittent results (>15% failure rate) across a rolling 10-build window, guarded by a 5-run minimum so thin history can't quarantine anything. A test that fails 100% of the time is a regression, **not** a flake, and is never quarantined.

- **Quarantine has anti-flapping exit.** A quarantined test is only released once it's *consistent* again (all-pass or all-fail across the window), so a still-flaky test can't bounce in and out of quarantine.

- **Untrusted LLM input is treated as data, not instructions.** Failure text is truncated (2000 chars), delimited, and never interpolated into the system prompt as commands. Triage is cost-capped per run and stops spending once the cap is hit.

- **Zero-dependency core.** The parsing, flake, and gate logic import only the standard library (`xml`, `sqlite3`, `json`, `argparse`). The OpenAI SDK is an optional extra, lazy-imported only when live triage is selected — so the gate runs anywhere, offline, with nothing to install.

## Quick start

```bash
# Install (editable, with dev + optional OpenAI extras)
python -m pip install -e ".[dev,openai]"

# Run the test suite — it produces the reports the gate consumes
pytest --junitxml=junit.xml --cov=quality_gate --cov-report=xml:coverage.xml

# Run the gate on those results (offline triage, no API key needed)
python -m quality_gate \
  --junit junit.xml \
  --coverage coverage.xml \
  --history gate-history.db \
  --report gate-report.json \
  --triage --provider fake \
  --triage-report triage-report.json
```

The process exits **1** on `FAIL` (blocking the PR) and **0** on `PASS`/`WARN`.

### Live LLM triage

Triage runs offline by default with a deterministic `fake` provider — CI stays green with no secrets. To use OpenAI, set your key and switch the provider:

```bash
export OPENAI_API_KEY=sk-...              # macOS / Linux
$env:OPENAI_API_KEY = "sk-..."            # PowerShell

python -m quality_gate --junit junit.xml --triage --provider openai \
  --triage-model gpt-4o-mini --max-cost-usd 0.50 --triage-report triage-report.json
```

The key is read from the environment by the SDK — it never touches the code or the repo. In CI, add it as an `OPENAI_API_KEY` repository secret.

### Durable cloud history (optional)

Flake detection needs history to persist *between* CI runs. By default the gate writes a local `gate-history.db` (SQLite) — perfect for local dev, but on ephemeral CI runners that file doesn't survive. Point it at [Turso](https://turso.tech) (libSQL — SQLite's dialect in the cloud) and the history becomes durable:

```bash
export TURSO_DATABASE_URL=libsql://<your-db>.turso.io
export TURSO_AUTH_TOKEN=<your-token>        # read from env only, never a CLI flag

python -m quality_gate --junit junit.xml --history-url "$TURSO_DATABASE_URL"
```

The store is chosen behind the `HistoryStore` protocol: Turso when a URL **and** token are present, local SQLite otherwise. libSQL speaks SQLite's dialect, so both adapters run identical SQL — only the connection differs. Install the extra with `pip install -e ".[turso]"`.

## Development

```bash
ruff check src tests    # lint + import order
mypy                    # static type check
pytest -q               # 65 tests, offline, deterministic
```

## Tech

Python 3.12 · standard library core · OpenAI API (optional) · Turso / libSQL (optional) · pytest · pytest-cov · JUnit XML · Allure · GitHub Actions · GitHub Pages · ruff · mypy · hatchling
