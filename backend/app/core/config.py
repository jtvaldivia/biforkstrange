from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Bifurca"
    cors_origins: list[str] = ["http://localhost:5173"]
    default_runs: int = 2000
    # Para que Claude lea el CV y narre. En Render va como variable de entorno; en local, en backend/.env.
    # El SDK no lee el .env por su cuenta: claude_comun.cliente se la pasa.
    anthropic_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
