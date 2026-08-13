from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI BankSim API"
    app_env: str = "development"
    database_url: str = "sqlite:///./ai_banksim.sqlite3"
    auto_create_tables: bool = False
    auth_token_ttl_hours: int = 12
    enable_dev_seed: bool = False
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ai_provider: str = "mock"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
