from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM provider: "vllm" (AMD-local, default) | "anthropic" (cloud) | "auto"
    llm_provider: str = "vllm"

    # vLLM — AMD MI300X local inference (primary)
    # Port 8001 avoids conflict with FastAPI on 8000
    vllm_base_url: str = "http://localhost:8001/v1"
    vllm_api_key: str = "abc-123"
    vllm_model: str = "Qwen3-14B"
    # Set True for Qwen3 models; strips <think>...</think> from outputs
    vllm_model_has_thinking: bool = True
    # Per-request token ceiling for agent calls
    vllm_max_tokens: int = 1024

    # Anthropic cloud (fallback / optional)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # LangSmith observability
    langchain_tracing_v2: str = "true"
    langchain_api_key: str = ""
    langchain_project: str = "idtcc-production"

    # Resilience: retries + timeout for every LLM call
    llm_max_retries: int = 2
    llm_timeout_seconds: float = 60.0

    # App
    default_location: str = "CHN"
    default_twin_count: int = 50_000
    log_level: str = "INFO"
    json_logs: bool = False  # set True for machine-parseable logs


settings = Settings()
