"""
core/model_router.py

Routes chat requests across ALL your LLM providers:
Groq, Mistral, Cerebras, OpenRouter, and Cohere (10 keys total,
2 each) — with:
1. Rate-limit LOCK — never wastes a call on an exhausted key
2. Automatic rotation between keys/providers on failure
3. Exponential backoff retries
4. Local logging (pyros_data/router.log)
5. Timeout protection
6. A status() health check for the UI

NOTE: HPC is not included yet — its API details need to be confirmed
before it can be wired in safely. See core/settings.py for the placeholder.
"""
import os
import time
import logging
from collections import deque
from groq import Groq
from openai import OpenAI
from mistralai.client.sdk import Mistral
import cohere
import core.settings as settings

os.makedirs("pyros_data", exist_ok=True)
logging.basicConfig(
    filename="pyros_data/router.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("model_router")

WINDOW_SECONDS = 60
REQUEST_TIMEOUT = 20
MAX_RETRIES = 2


class RateLimitedClient:
    def __init__(self, name: str, client, model: str, provider_type: str = "openai_style"):
        self.name = name
        self.client = client
        self.model = model
        self.provider_type = provider_type  # "openai_style" or "cohere"
        self.call_times = deque()
        self.consecutive_failures = 0

    def is_available(self) -> bool:
        now = time.time()
        while self.call_times and now - self.call_times[0] > WINDOW_SECONDS:
            self.call_times.popleft()
        return len(self.call_times) < settings.MAX_REQUESTS_PER_MINUTE

    def record_call(self):
        self.call_times.append(time.time())

    def seconds_until_free(self) -> float:
        if not self.call_times:
            return 0
        return max(0, WINDOW_SECONDS - (time.time() - self.call_times[0]))


class LLMRouter:
    def __init__(self):
        self.providers = [
            RateLimitedClient("groq_key1", Groq(api_key=settings.GROQ_API_KEY1), "llama-3.3-70b-versatile"),
            RateLimitedClient("groq_key2", Groq(api_key=settings.GROQ_API_KEY2), "llama-3.3-70b-versatile"),
            RateLimitedClient("mistral_key1", Mistral(api_key=settings.MISTRAL_API_KEY1), "mistral-large-latest"),
            RateLimitedClient("mistral_key2", Mistral(api_key=settings.MISTRAL_API_KEY2), "mistral-large-latest"),
            RateLimitedClient(
                "cerebras_key1",
                OpenAI(api_key=settings.CEREBRAS_API_KEY1, base_url="https://api.cerebras.ai/v1"),
                "llama-3.3-70b",
            ),
            RateLimitedClient(
                "cerebras_key2",
                OpenAI(api_key=settings.CEREBRAS_API_KEY2, base_url="https://api.cerebras.ai/v1"),
                "llama-3.3-70b",
            ),
            RateLimitedClient(
                "openrouter_key1",
                OpenAI(api_key=settings.OPENROUTER_API_KEY1, base_url="https://openrouter.ai/api/v1"),
                "meta-llama/llama-3.3-70b-instruct:free",
            ),
            RateLimitedClient(
                "openrouter_key2",
                OpenAI(api_key=settings.OPENROUTER_API_KEY2, base_url="https://openrouter.ai/api/v1"),
                "meta-llama/llama-3.3-70b-instruct:free",
            ),
            RateLimitedClient(
                "cohere_key1",
                cohere.Client(api_key=settings.COHERE_API_KEY1),
                "command-r-plus",
                provider_type="cohere",
            ),
            RateLimitedClient(
                "cohere_key2",
                cohere.Client(api_key=settings.COHERE_API_KEY2),
                "command-r-plus",
                provider_type="cohere",
            ),
            RateLimitedClient(
                "hpc_key1",
                OpenAI(api_key=settings.HPC_API_KEY1, base_url="https://api.hpc-ai.com/inference/v1"),
                "minimax/minimax-m2.5",
            ),
            RateLimitedClient(
                "hpc_key2",
                OpenAI(api_key=settings.HPC_API_KEY2, base_url="https://api.hpc-ai.com/inference/v1"),
                "minimax/minimax-m2.5",
            ),
        ]

    def _call_openai_style(self, provider, messages, tools, stream):
        kwargs = {"model": provider.model, "messages": messages, "timeout": REQUEST_TIMEOUT}
        if tools:
            kwargs["tools"] = tools
        if stream:
            kwargs["stream"] = True
        return provider.client.chat.completions.create(**kwargs)

    def _call_cohere(self, provider, messages):
        # Cohere's SDK has a different shape — convert our standard message
        # list into Cohere's expected format before calling.
        last_user_msg = messages[-1]["content"]
        chat_history = [
            {"role": "USER" if m["role"] == "user" else "CHATBOT", "message": m["content"]}
            for m in messages[:-1]
            if m["role"] in ("user", "assistant")
        ]
        response = provider.client.chat(
            model=provider.model,
            message=last_user_msg,
            chat_history=chat_history,
        )

        # Wrap it to look like an OpenAI-style response so orchestrator.py
        # doesn't need to know the difference between providers.
        class _FakeMessage:
            content = response.text
            tool_calls = None

        class _FakeChoice:
            message = _FakeMessage()

        class _FakeResponse:
            choices = [_FakeChoice()]

        return _FakeResponse()

    def chat(self, messages: list, tools: list = None, stream: bool = False):
        soonest_wait = None
        last_error = None
        any_available = False

        for provider in self.providers:
            if not provider.is_available():
                wait = provider.seconds_until_free()
                soonest_wait = wait if soonest_wait is None else min(soonest_wait, wait)
                logger.info(f"SKIPPED {provider.name} — locked, free in {wait:.1f}s")
                continue

            any_available = True

            for attempt in range(MAX_RETRIES + 1):
                try:
                    provider.record_call()
                    logger.info(f"CALL {provider.name} (attempt {attempt + 1})")

                    if provider.provider_type == "cohere":
                        response = self._call_cohere(provider, messages)
                    else:
                        response = self._call_openai_style(provider, messages, tools, stream)

                    provider.consecutive_failures = 0
                    logger.info(f"SUCCESS {provider.name}")
                    return response

                except Exception as e:
                    last_error = e
                    provider.consecutive_failures += 1
                    logger.warning(f"FAILED {provider.name} attempt {attempt + 1}: {e}")
                    if attempt < MAX_RETRIES:
                        time.sleep(2 ** attempt)

            logger.warning(f"GIVING UP on {provider.name}")

        if not any_available:
            wait_msg = f"Try again in about {int(soonest_wait)} seconds." if soonest_wait else ""
            msg = (
                f"LOCK ENGAGED: all providers are at the "
                f"{settings.MAX_REQUESTS_PER_MINUTE}-requests-per-minute limit. {wait_msg}"
            )
            logger.error(msg)
            raise RuntimeError(msg)

        msg = f"All providers failed after retries. Last error: {last_error}"
        logger.error(msg)
        raise RuntimeError(msg)

    def status(self) -> dict:
        return {
            p.name: {
                "available": p.is_available(),
                "seconds_until_free": round(p.seconds_until_free(), 1),
                "recent_failures": p.consecutive_failures,
            }
            for p in self.providers
        }