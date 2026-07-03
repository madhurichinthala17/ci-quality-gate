"""Structural checks for the live providers — no SDK or API key required.

The `anthropic`/`openai` imports are lazy (inside __init__), so importing the
classes and inspecting their shape is safe offline. Behavior is covered by the
FakeProvider tests, which share the LLMProvider interface.
"""

from __future__ import annotations

from quality_gate.triage import ClaudeProvider, OpenAIProvider


def test_live_providers_expose_the_protocol_surface():
    assert ClaudeProvider.name == "claude"
    assert OpenAIProvider.name == "openai"
    assert callable(ClaudeProvider.complete)
    assert callable(OpenAIProvider.complete)
