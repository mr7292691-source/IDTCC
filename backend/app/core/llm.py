"""LLM client factory — vLLM (AMD MI300X primary) with Anthropic cloud fallback.

Mirrors the OpenAI-compatible vLLM pattern from build_airbnb_agent_mcp.ipynb:

    BASE_URL = "http://localhost:8001/v1"
    provider  = OpenAIProvider(base_url=BASE_URL, api_key="abc-123")
    model     = OpenAIModel("Qwen3-14B", provider=provider)

Here we wrap that in LangChain's ChatOpenAI so the existing LangGraph graph,
LangSmith tracing, and agent nodes require zero changes. Adds: automatic retry
with exponential backoff, token-usage metrics, and a structured-JSON helper
backed by the guardrails module.
"""
from __future__ import annotations

import logging
import os
import re
from functools import lru_cache
from typing import Any, Dict, Optional

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings
from app.core.guardrails import extract_json
from app.core.logging_config import get_logger, log_event
from app.core.metrics import METRICS

log = get_logger("idtcc.llm")


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
        extra_body: dict = {}
        if settings.vllm_model_has_thinking:
            extra_body["chat_template_kwargs"] = {"enable_thinking": False}

        return ChatOpenAI(
            model=settings.vllm_model,
            base_url=settings.vllm_base_url,
            api_key=settings.vllm_api_key,
            temperature=temperature,
            max_tokens=settings.vllm_max_tokens,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,  # retries handled by tenacity below
            model_kwargs=extra_body if extra_body else {},
        )

    # ── Fallback: Anthropic cloud ────────────────────────────────────────────
    if settings.anthropic_api_key:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=temperature,
            max_tokens=settings.vllm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )

    raise RuntimeError(
        "No LLM configured. "
        "Set LLM_PROVIDER=vllm + VLLM_BASE_URL, or ANTHROPIC_API_KEY."
    )


def _record_tokens(response: Any, agent: str) -> None:
    """Best-effort token accounting from a LangChain response."""
    try:
        meta = getattr(response, "usage_metadata", None) or {}
        total = meta.get("total_tokens") or 0
        if total:
            METRICS.inc("idtcc_llm_tokens_total", float(total), agent=agent)
            METRICS.inc("idtcc_llm_calls_total", agent=agent)
    except Exception:  # noqa: BLE001 — never let metrics break inference
        pass


def _invoke_with_retry(system: str, user: str, *, agent: str = "unknown"):
    from langchain_core.messages import HumanMessage, SystemMessage

    @retry(
        reraise=True,
        stop=stop_after_attempt(settings.llm_max_retries + 1),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type(Exception),
    )
    def _call():
        llm = get_llm()
        return llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])

    response = _call()
    _record_tokens(response, agent)
    return response


def call_llm_simple(system: str, user: str, max_tokens: int = 512,
                    agent: str = "unknown") -> str:
    """Synchronous LLM call with retry. Strips Qwen3 thinking; safe fallback on error."""
    try:
        response = _invoke_with_retry(system, user, agent=agent)
        text = response.content if isinstance(response.content, str) else str(response.content)
        if settings.vllm_model_has_thinking and "<think>" in text:
            text = _strip_thinking(text)
        return text.strip()
    except Exception as exc:  # noqa: BLE001
        METRICS.inc("idtcc_llm_failures_total", agent=agent)
        log_event(log, logging.WARNING, "llm.fallback", agent=agent, error=str(exc))
        return f"[LLM unavailable: {exc}]"


def call_llm_json(system: str, user: str, *, agent: str = "unknown",
                  fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """LLM call that returns a validated dict, applying the JSON guardrail.

    Always returns a dict. On any parse/transport failure returns `fallback`
    (or `{}`) so callers never crash on malformed model output.
    """
    raw = call_llm_simple(system, user, agent=agent)
    parsed = extract_json(raw)
    if parsed is None:
        METRICS.inc("idtcc_llm_json_parse_failures_total", agent=agent)
        log_event(log, logging.WARNING, "llm.json_parse_failed", agent=agent)
        return dict(fallback or {})
    return parsed
