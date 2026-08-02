from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """A cloud chat-completion model. Every LLM call in this app — concept
    tagging now, tutoring/summaries/quiz generation from Phase 4 onward —
    goes through this interface, never through a provider SDK directly, so
    swapping Gemini for Groq/OpenRouter/OpenAI is a config change."""

    @abstractmethod
    async def complete(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        response_json: bool = False,
    ) -> str:
        """Returns the model's text response. If response_json is True, the
        provider is instructed to return valid JSON (implementation detail
        varies by provider) — callers still need to json.loads() it."""
        ...
