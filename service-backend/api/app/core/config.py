from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "kkthon-service-api"
    app_debug: bool = True
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str
    sync_database_url: str

    supabase_url: str
    supabase_anon_key: str

    cors_origins: str | None = None

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "eu-west-1"
    aws_s3_bucket: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
