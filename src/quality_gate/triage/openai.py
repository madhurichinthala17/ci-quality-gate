"""OpenAI provider — the swappable alternative backend.

Lazy-imports the `openai` SDK inside __init__ (absolute import resolves to the
installed package, not this module). Credentials resolve from OPENAI_API_KEY.
Add the chosen model's rates to `provider.PRICES` for accurate cost tracking.
"""

from __future__ import annotations

from .provider import LLMResponse


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-4o-mini", max_tokens: int = 1024) -> None:
        import openai  # lazy: only needed for live triage

        self._client = openai.OpenAI()
        self.model = model
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self.model,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage  # the SDK types this as optional; absent on some responses
        prompt_tokens = usage.prompt_tokens if usage else 0
        completion_tokens = usage.completion_tokens if usage else 0
        return LLMResponse(text, prompt_tokens, completion_tokens)
