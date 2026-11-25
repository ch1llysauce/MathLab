from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    notebook_db_path: str = "mathlab_notebooks.db"
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    vite_supabase_url: str | None = None
    vite_supabase_anon_key: str | None = None
    vite_supabase_publishable_key: str | None = None
    vite_supabase_publishable_default_key: str | None = None
    auth_required: bool = False
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str | None = None

    @model_validator(mode="after")
    def _fallback_vite_supabase_vars(self) -> "Settings":
        if not self.supabase_url and self.vite_supabase_url:
            self.supabase_url = self.vite_supabase_url
        if not self.supabase_anon_key:
            self.supabase_anon_key = (
                self.vite_supabase_anon_key
                or self.vite_supabase_publishable_key
                or self.vite_supabase_publishable_default_key
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
