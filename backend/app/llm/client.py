from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import structlog
from google import genai
from google.genai import types as gtypes
from groq import AsyncGroq

from app.config import get_settings

logger = structlog.get_logger(__name__)

Tier = Literal["fast", "strong"]


@dataclass(frozen=True)
class CompleteResult:
    text: str
    tokens_used: int
    provider: str


async def complete(
    prompt: str,
    *,
    tier: Tier = "fast",
    max_tokens: int = 1024,
    temperature: float = 0.2,
    json_mode: bool = False,
    system: str | None = None,
) -> CompleteResult:
    """Generate text via Groq (preferred) or Gemini (fallback)."""
    settings = get_settings()
    provider = settings.active_llm_provider
    if provider == "none":
        raise RuntimeError("No LLM provider configured. Set GROQ_API_KEY or GEMINI_API_KEY.")

    if provider == "groq":
        return await _complete_groq(
            prompt,
            tier=tier,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
            system=system,
        )
    return await _complete_gemini(
        prompt,
        tier=tier,
        max_tokens=max_tokens,
        temperature=temperature,
        json_mode=json_mode,
    )


async def _complete_groq(
    prompt: str,
    *,
    tier: Tier,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
    system: str | None,
) -> CompleteResult:
    settings = get_settings()
    model = settings.llm_model_fast if tier == "fast" else settings.llm_model_strong
    # Groq coerces temperature 0 to 1e-8; keep values in (0, 2].
    safe_temp = min(2.0, max(1e-8, float(temperature) or 1e-8))

    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    elif json_mode:
        messages.append(
            {
                "role": "system",
                "content": "You must respond with a valid JSON object only. No markdown fences.",
            }
        )
    messages.append({"role": "user", "content": prompt})

    kwargs: dict = {
        "model": model,
        "messages": messages,
        "temperature": safe_temp,
        "max_completion_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    client = AsyncGroq(api_key=settings.groq_api_key)
    completion = await client.chat.completions.create(**kwargs)
    text = (completion.choices[0].message.content or "").strip()
    usage = completion.usage
    tokens = 0
    if usage is not None:
        tokens = int(getattr(usage, "total_tokens", 0) or 0)
        if not tokens:
            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
            tokens = prompt_tokens + completion_tokens

    logger.debug("LLM complete via Groq", model=model, tokens=tokens, json_mode=json_mode)
    return CompleteResult(text=text, tokens_used=tokens, provider="groq")


async def _complete_gemini(
    prompt: str,
    *,
    tier: Tier,
    max_tokens: int,
    temperature: float,
    json_mode: bool,
) -> CompleteResult:
    settings = get_settings()
    model = settings.gemini_model_fast if tier == "fast" else settings.gemini_model_strong
    safe_temp = min(2.0, max(1e-8, float(temperature) or 1e-8))

    config_kwargs: dict = {
        "max_output_tokens": max_tokens,
        "temperature": safe_temp,
    }
    if json_mode:
        config_kwargs["response_mime_type"] = "application/json"

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.generate_content(
        model=model,
        contents=prompt,
        config=gtypes.GenerateContentConfig(**config_kwargs),
    )
    text = (response.text or "").strip()
    tokens = 0
    usage = response.usage_metadata
    if usage is not None:
        tokens = int((usage.prompt_token_count or 0) + (usage.candidates_token_count or 0))

    logger.debug("LLM complete via Gemini", model=model, tokens=tokens, json_mode=json_mode)
    return CompleteResult(text=text, tokens_used=tokens, provider="gemini")
