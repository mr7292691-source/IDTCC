from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_api_key: str = "abc-123"
    vllm_model: str = "Qwen3-4B"

    langchain_tracing_v2: str = "true"
    langchain_api_key: str = ""
    langchain_project: str = "idtcc-production"

    default_location: str = "CHN"
    default_twin_count: int = 50_000
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
