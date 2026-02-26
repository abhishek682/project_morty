from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "rick-morty-api"
    environment: str = "dev"
    log_level: str = "info"
    log_file: str | None = None

    rick_morty_base_url: str = "https://rickandmortyapi.com/api"
    request_timeout_seconds: int = 10
    max_retries: int = 3
    backoff_seconds: float = 0.5

    cache_ttl_seconds: int = 300
    sync_interval_seconds: int = 900

    database_url: str = "postgresql+psycopg2://app:app@localhost:5432/rickmorty"
    redis_url: str = "redis://localhost:6379/0"

    rate_limit_per_minute: int = 60
    rate_limit_storage_uri: str | None = None

    otel_service_name: str = "rick-morty-api"
    otel_exporter_otlp_endpoint: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="RM_")


settings = Settings()
