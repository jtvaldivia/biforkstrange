from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "{{cookiecutter.project_name}}"
    cors_origins: list[str] = ["http://localhost:5173"]
    default_runs: int = 2000


@lru_cache
def get_settings() -> Settings:
    return Settings()
