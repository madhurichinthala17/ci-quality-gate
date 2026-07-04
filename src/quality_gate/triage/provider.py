"""LLM provider adapters — the interface the orchestrator depends on.

`LLMProvider` is the port; `FakeProvider` is a deterministic, offline, zero-cost
implementation used by every test (no API key, no spend). Real providers
(ClaudeProvider, OpenAIProvider) implement the same Protocol and are constructed
only by the composition root.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, system: str, user: str) -> LLMResponse: ...


# USD per 1,000,000 tokens: (input, output). OpenAI values are approximate —
# verify against current OpenAI pricing before relying on the dollar figures.
PRICES: dict[str, tuple[float, float]] = {
    "fake-1": (0.0, 0.0),
    "claude-opus-4-8": (5.0, 25.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = PRICES.get(model, (0.0, 0.0))
    return input_tokens / 1e6 * price_in + output_tokens / 1e6 * price_out


class FakeProvider:
    """Deterministic offline provider — classifies from keywords in the failure text."""

    name = "fake"
    model = "fake-1"

    def complete(self, system: str, user: str) -> LLMResponse:
        text = user.lower()
        if "timeout" in text:
            cat, cause, step = ("timeout", "the operation exceeded its time limit",
                                "increase the timeout or optimize the slow call")
        elif "assert" in text:
            cat, cause, step = ("assertion", "an assertion did not hold",
                                "compare expected vs actual and fix the logic or the test")
        elif "connection" in text or "dependency" in text:
            cat, cause, step = ("dependency", "an external dependency was unavailable",
                                "check the dependency and add a retry or a health check")
        else:
            cat, cause, step = ("unknown", "insufficient information in the failure text",
                                "review the failure manually")
        payload = json.dumps({
            "category": cat,
            "probable_cause": cause,
            "suggested_next_step": step,
            "grounded": cat != "unknown",
        })
        # rough offline token estimate (~4 chars/token); real providers report exact usage
        return LLMResponse(payload, input_tokens=len(system + user) // 4, output_tokens=len(payload) // 4)
