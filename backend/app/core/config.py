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
    app_version: str = "0.4.0"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str

    # SMTP
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@korrijo.com"
    # Email donde se reciben los mensajes del formulario de contacto.
    contact_recipient_email: str = "acs@gmail.com"
    # Rate limiting del formulario de contacto (por IP).
    contact_rate_limit_max: int = 3
    contact_rate_limit_window_minutes: int = 10

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
    max_context_upload_bytes: int = 7 * 1024 * 1024  # 7 MB (contexto)
    max_document_upload_bytes: int = 3 * 1024 * 1024  # 3 MB (examen modelo y rúbrica)

    # Exámenes a corregir (fase 2): escaneados/imágenes.
    max_exam_upload_bytes: int = 5 * 1024 * 1024  # 5 MB por examen
    max_exams_per_upload: int = 3  # exámenes admitidos en una sola subida

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
