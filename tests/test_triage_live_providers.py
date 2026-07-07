"""Structural check for the live provider — no SDK or API key required.

The `openai` import is lazy (inside __init__), so importing the class and
inspecting its shape is safe offline. Behavior is covered by the FakeProvider
tests, which share the LLMProvider interface.
"""

from __future__ import annotations

from quality_gate.triage import OpenAIProvider


def test_openai_provider_exposes_the_protocol_surface():
    assert OpenAIProvider.name == "openai"
    assert callable(OpenAIProvider.complete)
