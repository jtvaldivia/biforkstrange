from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Agarrar la pala"
    supabase_url: str = ""
    supabase_service_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173"]
    default_runs: int = 2000
    anthropic_api_key: str = ""  # también vale exportada en el entorno o un perfil de `ant auth login`
    anthropic_model: str = "claude-sonnet-5-5"  # el gemelo: encuestas, examen y perfil desde tu contexto

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
