import base64

from openai import AsyncOpenAI

from app.services.llm.base import LLMProvider


class OpenAICompatibleProvider(LLMProvider):
    """Groq, OpenRouter, and OpenAI itself all speak the OpenAI chat-completions
    API, so one client — pointed at a different base_url and key — covers all
    three instead of three separate SDK integrations."""

    def __init__(self, *, api_key: str, base_url: str, model: str, provider_name: str):
        if not api_key:
            raise ValueError(f"{provider_name.upper()}_API_KEY is not set.")
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def complete(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
        response_json: bool = False,
    ) -> str:
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_output_tokens,
            response_format={"type": "json_object"} if response_json else None,
        )
        return response.choices[0].message.content or ""

    async def complete_vision(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        max_output_tokens: int = 2048,
    ) -> str:
        # Standard OpenAI-compatible vision message shape — same content-part
        # format Groq's and OpenRouter's vision-capable models accept.
        data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=max_output_tokens,
        )
        return response.choices[0].message.content or ""
