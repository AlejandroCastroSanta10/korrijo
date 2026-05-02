from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App metadata
    app_name: str = "API de Korrijo"
    app_version: str = "0.1.0"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str


settings = Settings()
