from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    max_bot_token: str = Field(alias="MAX_BOT_TOKEN")
    max_api_base: str = Field(default="https://platform-api.max.ru", alias="MAX_API_BASE")

    max_long_poll_timeout: int = Field(default=30, alias="MAX_LONG_POLL_TIMEOUT")
    max_long_poll_limit: int = Field(default=100, alias="MAX_LONG_POLL_LIMIT")
    max_allowed_update_types: str = Field(
        default="message_created,message_callback",
        alias="MAX_ALLOWED_UPDATE_TYPES",
    )

    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    max_webhook_secret: str = Field(default="", alias="MAX_WEBHOOK_SECRET")
    max_webhook_path: str = Field(default="/max/webhook", alias="MAX_WEBHOOK_PATH")

    crm_base_url: str = Field(default="http://localhost:8081", alias="CRM_BASE_URL")
    crm_api_key: str = Field(default="", alias="CRM_API_KEY")
    crm_max_retries: int = Field(default=3, alias="CRM_MAX_RETRIES")
    crm_retry_base_delay: float = Field(default=1.0, alias="CRM_RETRY_BASE_DELAY")

    @property
    def allowed_update_types(self) -> list[str]:
        return [x.strip() for x in self.max_allowed_update_types.split(",") if x.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()