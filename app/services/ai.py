from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from app.core.config import get_settings


SYSTEM_INSTRUCTION = """You are the LANSEIR Reflection Guide. Help the user examine their own words and authorized product context with clarity. Ask useful questions, distinguish observation from inference, never claim hidden knowledge, and never provide medical, legal, or financial conclusions. Be concise, grounded, private by default, and do not quote unavailable source material."""


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderResult:
    content: str
    provider: str
    model: str
    latency_ms: int
    usage: dict


class LocalReflectionProvider:
    name = "local"

    def complete(self, message: str, context: str) -> ProviderResult:
        started = time.monotonic()
        lowered = message.casefold()
        if "summar" in lowered and context:
            words = context.split()
            excerpt = " ".join(words[:80])
            content = f"From the context you chose to share, the central thread is: {excerpt}{'…' if len(words) > 80 else ''}\n\nWhat part of that feels most important to act on now?"
        elif context:
            content = "I can work only with the context you chose to share. One useful distinction is between what happened, what you interpreted, and what you control next. Which of those three needs your attention?"
        else:
            content = "Name the situation in one sentence, then separate what is true now from what you fear or hope may happen. What is the smallest next action within your authority?"
        return ProviderResult(
            content=content,
            provider=self.name,
            model="lanseir-reflection-v1",
            latency_ms=max(1, round((time.monotonic() - started) * 1000)),
            usage={"input_characters": len(message) + len(context), "output_characters": len(content), "estimated_cost_usd": 0},
        )


class OpenAICompatibleProvider:
    name = "openai-compatible"

    @staticmethod
    def _validated_endpoint(base_url: str) -> str:
        parsed = urllib.parse.urlparse(base_url)
        is_loopback = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and is_loopback):
            raise ProviderError("AI base URL must use HTTPS or loopback HTTP")
        if parsed.username or parsed.password or not parsed.hostname:
            raise ProviderError("AI base URL is invalid")
        return base_url.rstrip("/") + "/chat/completions"

    async def complete(self, message: str, context: str) -> ProviderResult:
        settings = get_settings()
        if not settings.ai_api_key:
            raise ProviderError("Configured AI provider is missing its server-side credential")
        endpoint = self._validated_endpoint(settings.ai_base_url)
        prompt = message if not context else f"Authorized user context:\n{context[:12000]}\n\nUser request:\n{message}"
        body = json.dumps(
            {
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_INSTRUCTION},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 700,
                "temperature": 0.4,
            }
        ).encode()
        request = urllib.request.Request(
            endpoint,
            data=body,
            method="POST",
            headers={"Authorization": f"Bearer {settings.ai_api_key}", "Content-Type": "application/json"},
        )
        started = time.monotonic()

        def send() -> tuple[str, dict]:
            try:
                with urllib.request.urlopen(request, timeout=settings.request_timeout_seconds) as response:
                    payload = json.loads(response.read(2_000_000))
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                raise ProviderError("The configured AI provider is unavailable") from exc
            try:
                return payload["choices"][0]["message"]["content"], payload.get("usage", {})
            except (KeyError, IndexError, TypeError) as exc:
                raise ProviderError("The configured AI provider returned an invalid response") from exc

        content, usage = await asyncio.to_thread(send)
        return ProviderResult(
            content=content,
            provider=self.name,
            model=settings.ai_model,
            latency_ms=round((time.monotonic() - started) * 1000),
            usage=usage,
        )


async def route_completion(message: str, context: str) -> ProviderResult:
    provider = get_settings().ai_provider.casefold()
    if provider == "local":
        return LocalReflectionProvider().complete(message, context)
    if provider in {"openai", "openai-compatible", "litellm", "openrouter"}:
        return await OpenAICompatibleProvider().complete(message, context)
    raise ProviderError("AI provider policy is unavailable")
