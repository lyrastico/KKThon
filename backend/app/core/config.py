from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "apocalipssi-api"
    app_debug: bool = True

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    database_url: str
    sync_database_url: str

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None

    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_default_region: str | None = None
    s3_bucket_name: str | None = None
    s3_endpoint_url: str | None = None
    s3_key_prefix: str = "documents"

    cors_origins: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
