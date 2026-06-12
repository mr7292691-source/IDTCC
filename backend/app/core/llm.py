"""LLM client factory — supports Anthropic and vLLM/OpenAI-compatible endpoints."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from app.config import settings


def _configure_langsmith() -> None:
    os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.langchain_tracing_v2)
    if settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)


@lru_cache(maxsize=1)
def get_llm(temperature: float = 0.3):
    """Return a LangChain chat model. Prefers Anthropic; falls back to vLLM."""
    _configure_langsmith()

    if settings.anthropic_api_key:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=512,
        )

    # vLLM / OpenAI-compatible fallback
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=settings.vllm_model,
        base_url=settings.vllm_base_url,
        api_key=settings.vllm_api_key,
        temperature=temperature,
        max_tokens=512,
    )


def call_llm_simple(system: str, user: str, max_tokens: int = 400) -> str:
    """Synchronous LLM call with graceful fallback."""
    try:
        llm = get_llm()
        from langchain_core.messages import HumanMessage, SystemMessage
        msgs = [SystemMessage(content=system), HumanMessage(content=user)]
        response = llm.invoke(msgs)
        return response.content.strip()
    except Exception as exc:
        return f"[LLM unavailable: {exc}]"
