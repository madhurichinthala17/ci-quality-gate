"""Anthropic Claude provider — the default live LLM backend.

Lazy-imports the `anthropic` SDK inside __init__ so the package and every offline
test (which use FakeProvider) never require it. Credentials resolve from the
environment (ANTHROPIC_API_KEY, or an `ant auth login` profile).
"""

from __future__ import annotations

from .provider import LLMResponse


class ClaudeProvider:
    name = "claude"

    def __init__(self, model: str = "claude-opus-4-8", max_tokens: int = 1024) -> None:
        import anthropic  # lazy: only needed for live triage

        self._client = anthropic.Anthropic()
        self.model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str) -> LLMResponse:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return LLMResponse(text, resp.usage.input_tokens, resp.usage.output_tokens)
