from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App metadata
    app_name: str = "API de Korrijo"
    app_version: str = "0.3.0"

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

    # Almacenamiento de ficheros subidos (rúbricas, contextos, exámenes...).
    storage_root: Path = _BACKEND_DIR / "storage"

    # Máximo de sesiones activas por usuario.
    max_active_sessions_per_user: int = 5

    # Tamaño máximo de los documentos iniciales subidos a una sesión (en bytes).
    max_context_upload_bytes: int = 10 * 1024 * 1024  # 10 MB (contexto)
    max_document_upload_bytes: int = 5 * 1024 * 1024  # 5 MB (examen modelo y rúbrica)

    # Ollama / pipeline
    ollama_base_url: str = "http://localhost:11434"
    pipeline_llm_model: str | None = None
    pipeline_vlm_model: str | None = None
    # Ventana de contexto en tokens. Por defecto.
    pipeline_llm_num_ctx: int = 16384
    pipeline_vlm_num_ctx: int = 16384
    # Timeout (segundos) de la llamada al proveedor de inferencia.
    pipeline_llm_timeout: float = 300.0
    pipeline_vlm_timeout: float = 200.0


settings = Settings()
