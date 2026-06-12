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

    # Anthropic cloud (fallback / optional)
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    langchain_tracing_v2: str = "true"
    langchain_api_key: str = ""
    langchain_project: str = "idtcc-production"

    default_location: str = "CHN"
    default_twin_count: int = 50_000
    log_level: str = "INFO"


settings = Settings()
