from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BiforkStrange"
    supabase_url: str = ""
    supabase_service_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]
    default_runs: int = 2000
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"  # gemelo: preguntas, examen, informe
    anthropic_story_model: str = "claude-haiku-5-5"  # narrador de la historia: barato y rápido

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
