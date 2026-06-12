"""LLM client factory — vLLM (AMD MI300X primary) with Anthropic cloud fallback.

Mirrors the OpenAI-compatible vLLM pattern from build_airbnb_agent_mcp.ipynb:

    BASE_URL = "http://localhost:8001/v1"
    provider  = OpenAIProvider(base_url=BASE_URL, api_key="abc-123")
    model     = OpenAIModel("Qwen3-14B", provider=provider)

Here we wrap that in LangChain's ChatOpenAI so the existing LangGraph graph,
LangSmith tracing, and agent nodes require zero changes.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache

from app.config import settings


def _configure_langsmith() -> None:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.langchain_tracing_v2)
    if settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)


def _strip_thinking(text: str) -> str:
    """Remove Qwen3 <think>...</think> blocks from model output."""
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL).strip()


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.3):
    """Return a LangChain ChatModel.

    Priority (controlled by LLM_PROVIDER env var):
      1. vllm  — local AMD MI300X server (default)
      2. anthropic — cloud fallback when ANTHROPIC_API_KEY is set
    """
    _configure_langsmith()

    provider = settings.llm_provider.lower()

    # ── Primary: local vLLM server (AMD MI300X, OpenAI-compatible) ──────────
    if provider in ("vllm", "auto"):
        from langchain_openai import ChatOpenAI

        # Qwen3 thinking models: disable chain-of-thought for structured outputs.
        # Passed as extra request body field to vLLM's chat completions endpoint.
        extra_body: dict = {}
        if settings.vllm_model_has_thinking:
            extra_body["chat_template_kwargs"] = {"enable_thinking": False}

        return ChatOpenAI(
            model=settings.vllm_model,
            base_url=settings.vllm_base_url,
            api_key=settings.vllm_api_key,
            temperature=temperature,
            max_tokens=1024,
            model_kwargs=extra_body if extra_body else {},
        )

    # ── Fallback: Anthropic cloud ────────────────────────────────────────────
    if settings.anthropic_api_key:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=1024,
        )

    raise RuntimeError(
        "No LLM configured. "
        "Set LLM_PROVIDER=vllm + VLLM_BASE_URL, or ANTHROPIC_API_KEY."
    )


def call_llm_simple(system: str, user: str, max_tokens: int = 512) -> str:
    """Synchronous LLM call. Strips Qwen3 thinking blocks; returns fallback on error."""
    try:
        llm = get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage

        msgs = [SystemMessage(content=system), HumanMessage(content=user)]
        response = llm.invoke(msgs)
        text = response.content

        # Strip <think>...</think> if the model emitted reasoning traces
        if settings.vllm_model_has_thinking and "<think>" in text:
            text = _strip_thinking(text)

        return text.strip()
    except Exception as exc:
        return f"[LLM unavailable: {exc}]"
