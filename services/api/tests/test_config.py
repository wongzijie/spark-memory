import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_require_real_secrets():
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://spark:spark@localhost:5432/spark",
            redis_url="redis://localhost:6379/0",
            telegram_bot_token="short",
            telegram_bot_id="spark",
            telegram_allowed_user_id=1,
            telegram_webhook_path_secret="short",
            telegram_webhook_header_secret="short",
            public_base_url="https://example.com",
            _env_file=None,
        )


def test_settings_default_timezone_is_shanghai(valid_settings_data):
    settings = Settings(**valid_settings_data, _env_file=None)

    assert settings.default_timezone == "Asia/Shanghai"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("database_url", "sqlite+aiosqlite:///spark.db", r"postgresql\+psycopg"),
        ("redis_url", "http://localhost:6379", "redis URL"),
    ],
)
def test_settings_reject_invalid_service_urls(valid_settings_data, field, value, message):
    values = valid_settings_data | {field: value}

    with pytest.raises(ValidationError, match=message):
        Settings(**values, _env_file=None)


def test_production_rejects_placeholder_credentials(valid_settings_data):
    values = valid_settings_data | {
        "app_env": "production",
        "telegram_bot_token": "replace-this-with-a-botfather-token-0000000000",
    }

    with pytest.raises(ValidationError, match="placeholder"):
        Settings(**values, _env_file=None)
