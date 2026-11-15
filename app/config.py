from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_token: str = ""
    bot_webhook_secret: str = ""
    public_base_url: str = "http://localhost:8000"
    # /tmp is the only writable location in a Vercel function. It is a local
    # fallback for health checks only; production must use PostgreSQL.
    database_url: str = "sqlite+aiosqlite:////tmp/livebot.db"
    jwt_secret: str = "development-only-change-me"
    allowed_telegram_ids: str = ""
    admin_telegram_ids: str = ""
    webhook_path: str = "/api/telegram/webhook"
    session_ttl_minutes: int = 120
    rate_limit_per_minute: int = 12
    worker_callback_secret: str = "development-only-change-me"
    worker_url: str = ""
    auto_create_tables: bool = False
    @field_validator("database_url", mode="before")
    @classmethod
    def async_database_driver(cls, value: str) -> str:
        """Accept Vercel/Neon standard URLs while SQLAlchemy uses asyncpg."""
        if not value: return "sqlite+aiosqlite:////tmp/livebot.db"
        if value.startswith("postgres://"): return "postgresql+asyncpg://" + value[len("postgres://"):]
        if value.startswith("postgresql://"): return "postgresql+asyncpg://" + value[len("postgresql://"):]
        return value
    @property
    def allowed_ids(self): return {int(x) for x in self.allowed_telegram_ids.split(",") if x.strip()}
    @property
    def admin_ids(self): return {int(x) for x in self.admin_telegram_ids.split(",") if x.strip()}
@lru_cache
def settings() -> Settings: return Settings()
