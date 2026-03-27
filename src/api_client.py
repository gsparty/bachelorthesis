"""
api_client.py
=============
Async API client for querying LLM providers (Groq, OpenAI, Anthropic).

Features:
    - Async/await with aiohttp for concurrent request batching.
    - Per-provider rate limit management with exponential backoff.
    - Structured error handling with typed exceptions.
    - Response normalization into a provider-agnostic dict schema.

Environment Variables Required (.env):
    GROQ_API_KEY        — Groq API key
    OPENAI_API_KEY      — OpenAI API key
    ANTHROPIC_API_KEY   — Anthropic API key
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

class Provider(str, Enum):
    GROQ = "groq"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"  
    GITHUB = "github"
    TOGETHER = "together"
    OPENROUTER = "openrouter" 
    

PROVIDER_CONFIG: Dict[Provider, Dict[str, Any]] = {
    Provider.TOGETHER: {
        "base_url": "https://api.together.xyz/v1/chat/completions",
        "api_key_env": "TOGETHER_API_KEY",
        "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "requests_per_minute": 60,
    },
    Provider.OPENROUTER: {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_env": "OPENROUTER_API_KEY",
        "default_model": "meta-llama/llama-3.1-8b-instruct:free",
        "requests_per_minute": 20,
    },
    Provider.GROQ: {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key_env": "GROQ_API_KEY",
        "default_model": "llama3-8b-8192",
        "requests_per_minute": 30,
    },
    Provider.GEMINI: {  # NEU HINZUGEFÜGT
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "api_key_env": "GEMINI_API_KEY",
        "default_model": "gemini-2.5-flash", # Sehr ressourceneffizient & schnell
        "requests_per_minute": 10, # Free Tier Limit von Google
    },
    Provider.OPENAI: {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "api_key_env": "OPENAI_API_KEY",
        "default_model": "gpt-3.5-turbo",
        "requests_per_minute": 60,
    },
    Provider.ANTHROPIC: {
        "base_url": "https://api.anthropic.com/v1/messages",
        "api_key_env": "ANTHROPIC_API_KEY",
        "default_model": "claude-haiku-4-5-20251001",
        "requests_per_minute": 50,
    },
    Provider.GITHUB: {
        "base_url": "https://models.inference.ai.azure.com/chat/completions",
        "api_key_env": "GITHUB_TOKEN",
        "default_model": "meta-llama-3.1-8b-instruct",
        "requests_per_minute": 15, 
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LLMRequest:
    """Provider-agnostic request payload."""
    system_prompt: str
    user_prompt: str
    provider: Provider
    model: Optional[str] = None
    temperature: float = 0.9          # High temp to surface stochastic variance
    max_tokens: int = 512
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Normalized response from any provider."""
    provider: str
    model: str
    content: str                       # Raw text output
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    request_metadata: Dict[str, Any]
    raw_response: Dict[str, Any]
    error: Optional[str] = None
    success: bool = True


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RateLimitError(Exception):
    """Raised when a provider returns HTTP 429."""

class ProviderAPIError(Exception):
    """Raised on non-retryable provider errors (4xx except 429)."""

class MaxRetriesExceeded(Exception):
    """Raised after all retry attempts are exhausted."""


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

class AsyncRateLimiter:
    """Token-bucket rate limiter for async contexts."""

    def __init__(self, requests_per_minute: int):
        self.rate = requests_per_minute / 60.0   # requests per second
        self.tokens = float(requests_per_minute)
        self.max_tokens = float(requests_per_minute)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self.tokens = min(
                self.max_tokens,
                self.tokens + elapsed * self.rate
            )
            self._last_refill = now
            if self.tokens < 1.0:
                wait = (1.0 - self.tokens) / self.rate
                logger.debug(f"Rate limiter: sleeping {wait:.2f}s")
                await asyncio.sleep(wait)
                self.tokens = 0.0
            else:
                self.tokens -= 1.0


# ---------------------------------------------------------------------------
# Provider-specific request builders
# ---------------------------------------------------------------------------

def _build_openai_payload(req: LLMRequest, model: str) -> Dict:
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": req.system_prompt},
            {"role": "user",   "content": req.user_prompt},
        ],
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }


def _build_anthropic_payload(req: LLMRequest, model: str) -> Dict:
    return {
        "model": model,
        "system": req.system_prompt,
        "messages": [{"role": "user", "content": req.user_prompt}],
        "temperature": req.temperature,
        "max_tokens": req.max_tokens,
    }


def _build_headers(provider: Provider, api_key: str) -> Dict[str, str]:
    if provider == Provider.ANTHROPIC:
        return {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _parse_response(provider: Provider, raw: Dict, latency_ms: float,
                    metadata: Dict) -> LLMResponse:
    """Normalize provider-specific response shapes into LLMResponse."""
    if provider == Provider.ANTHROPIC:
        content = raw.get("content", [{}])[0].get("text", "")
        model   = raw.get("model", "unknown")
        usage   = raw.get("usage", {})
        return LLMResponse(
            provider=provider.value,
            model=model,
            content=content,
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            latency_ms=latency_ms,
            request_metadata=metadata,
            raw_response=raw,
        )
    else:  # OpenAI-compatible (Groq uses OpenAI schema)
        choice  = raw.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        model   = raw.get("model", "unknown")
        usage   = raw.get("usage", {})
        return LLMResponse(
            provider=provider.value,
            model=model,
            content=content,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            request_metadata=metadata,
            raw_response=raw,
        )


# ---------------------------------------------------------------------------
# Core async client
# ---------------------------------------------------------------------------

class AsyncLLMClient:
    """
    Async client that dispatches requests to multiple LLM providers
    with per-provider rate limiting and exponential backoff.

    Usage:
        async with AsyncLLMClient() as client:
            response = await client.query(request)
    """

    MAX_RETRIES = 5
    BACKOFF_BASE = 2.0      # seconds; doubles each retry

    def __init__(self):
        self._rate_limiters: Dict[Provider, AsyncRateLimiter] = {
            p: AsyncRateLimiter(cfg["requests_per_minute"])
            for p, cfg in PROVIDER_CONFIG.items()
        }
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60)
        )
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def query(self, req: LLMRequest) -> LLMResponse:
        """
        Execute a single LLM request with automatic retry on rate limits.

        Args:
            req: LLMRequest instance.

        Returns:
            LLMResponse with normalized content and metadata.

        Raises:
            MaxRetriesExceeded: if all retry attempts fail.
            ProviderAPIError:   on non-retryable HTTP errors.
        """
        cfg     = PROVIDER_CONFIG[req.provider]
        api_key = os.getenv(cfg["api_key_env"], "")
        if not api_key:
            raise EnvironmentError(
                f"Missing env var: {cfg['api_key_env']}"
            )

        model   = req.model or cfg["default_model"]
        url     = cfg["base_url"]
        headers = _build_headers(req.provider, api_key)

        if req.provider == Provider.ANTHROPIC:
            payload = _build_anthropic_payload(req, model)
        else:
            payload = _build_openai_payload(req, model)

        for attempt in range(1, self.MAX_RETRIES + 1):
            await self._rate_limiters[req.provider].acquire()
            t0 = time.monotonic()
            try:
                async with self._session.post(
                    url, headers=headers, json=payload
                ) as resp:
                    latency_ms = (time.monotonic() - t0) * 1000
                    body = await resp.json(content_type=None)

                    if resp.status == 200:
                        return _parse_response(
                            req.provider, body, latency_ms, req.metadata
                        )
                    elif resp.status == 429:
                        backoff = self.BACKOFF_BASE ** attempt
                        logger.warning(
                            f"Rate limited by {req.provider.value} "
                            f"(attempt {attempt}/{self.MAX_RETRIES}). "
                            f"Backing off {backoff:.1f}s."
                        )
                        await asyncio.sleep(backoff)
                    elif 400 <= resp.status < 500:
                        raise ProviderAPIError(
                            f"HTTP {resp.status} from {req.provider.value}: "
                            f"{json.dumps(body)}"
                        )
                    else:
                        backoff = self.BACKOFF_BASE ** attempt
                        logger.warning(
                            f"HTTP {resp.status} from {req.provider.value}. "
                            f"Retrying in {backoff:.1f}s."
                        )
                        await asyncio.sleep(backoff)

            except aiohttp.ClientError as exc:
                backoff = self.BACKOFF_BASE ** attempt
                logger.error(f"Network error (attempt {attempt}): {exc}")
                await asyncio.sleep(backoff)

        raise MaxRetriesExceeded(
            f"Exhausted {self.MAX_RETRIES} retries for "
            f"{req.provider.value} — {req.metadata}"
        )

    async def batch_query(
        self,
        requests: List[LLMRequest],
        concurrency: int = 5,
    ) -> List[LLMResponse]:
        """
        Execute a batch of requests with bounded concurrency.

        Args:
            requests:    List of LLMRequest objects.
            concurrency: Max simultaneous in-flight requests.

        Returns:
            List of LLMResponse objects (order preserved).
        """
        semaphore = asyncio.Semaphore(concurrency)
        results   = [None] * len(requests)

        async def _bounded(i: int, req: LLMRequest):
            async with semaphore:
                try:
                    results[i] = await self.query(req)
                except Exception as exc:
                    logger.error(f"Request {i} failed: {exc}")
                    results[i] = LLMResponse(
                        provider=req.provider.value,
                        model=req.model or "",
                        content="",
                        prompt_tokens=0,
                        completion_tokens=0,
                        latency_ms=0.0,
                        request_metadata=req.metadata,
                        raw_response={},
                        error=str(exc),
                        success=False,
                    )

        await asyncio.gather(*[_bounded(i, r) for i, r in enumerate(requests)])
        return results
