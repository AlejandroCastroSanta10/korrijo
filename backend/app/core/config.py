from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App metadata
    app_name: str = "API de Korrijo"
    app_version: str = "0.2.0"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str

    # SMTP
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@korrijo.local"

    # Magic link
    magic_link_expiration_minutes: int = 15
    app_base_url: str = "http://localhost:3000"

    # Session
    session_secret_key: str
    session_cookie_name: str = "korrijo_session"
    session_max_age_days: int = 30


settings = Settings()
