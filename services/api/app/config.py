from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SPARK_", extra="ignore")

    app_env: str = "development"
    database_url: str
    redis_url: str
    default_timezone: str = "Asia/Shanghai"
    session_cookie_name: str = "spark_session"
    session_ttl_seconds: int = 604_800
    session_cookie_secure: bool = False
    telegram_bot_token: SecretStr = Field(min_length=32)
    telegram_bot_id: str = Field(min_length=1)
    telegram_allowed_user_id: int = Field(gt=0)
    telegram_webhook_path_secret: SecretStr = Field(min_length=32)
    telegram_webhook_header_secret: SecretStr = Field(min_length=32)
    public_base_url: AnyHttpUrl

    @field_validator("database_url")
    @classmethod
    def require_async_postgres_url(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("database URL must use postgresql+psycopg")
        return value

    @field_validator("redis_url")
    @classmethod
    def require_redis_url(cls, value: str) -> str:
        if not value.startswith(("redis://", "rediss://")):
            raise ValueError("redis URL must use redis or rediss")
        return value

    @model_validator(mode="after")
    def reject_production_placeholders(self) -> "Settings":
        if self.app_env.casefold() in {"development", "test"}:
            return self

        values = (
            self.database_url,
            self.telegram_bot_token.get_secret_value(),
            self.telegram_bot_id,
            self.telegram_webhook_path_secret.get_secret_value(),
            self.telegram_webhook_header_secret.get_secret_value(),
            str(self.public_base_url),
        )
        markers = ("replace-this", "example.invalid", "spark-local-only")
        if any(marker in value for value in values for marker in markers):
            raise ValueError("placeholder credentials are forbidden outside development and test")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
