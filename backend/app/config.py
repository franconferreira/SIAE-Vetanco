import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Rutas base del proyecto
BACKEND_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
PDF_STORAGE_DIR = DATA_DIR / "pdfs"
INBOX_DROP_DIR = DATA_DIR / "casilla_entrante"
BATCH_OUTPUT_DIR = DATA_DIR / "lotes_batch"
NOTIFICATIONS_DIR = DATA_DIR / "notificaciones"

for directory in [DATA_DIR, PDF_STORAGE_DIR, INBOX_DROP_DIR, BATCH_OUTPUT_DIR, NOTIFICATIONS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    APP_NAME: str = "SIAE-Vetanco"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Base de Datos
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'siae_staging.db'}"

    # Parámetros Vetanco S.A.
    VETANCO_CUIT: str = "30623368939"
    VETANCO_RAZON_SOCIAL: str = "VETANCO S.A."
    SAP_SOCIEDAD: str = "AR01"
    CONFIDENCE_THRESHOLD: float = 0.95

    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Mail / Casilla
    MAIL_INGESTION_MODE: str = "simulated"
    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USER: str = "facturas.proveedores.test.franco@gmail.com"
    IMAP_PASSWORD: str = ""

    # SMTP Notificaciones
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "facturas.proveedores.test.franco@gmail.com"
    SMTP_PASSWORD: str = ""
    NOTIFICACION_DESTINATARIOS: str = "analista.cuentas@vetanco.com,jefe.proveedores@vetanco.com"

    # Cron SAP Batch
    BATCH_CRON_HOUR: int = 17
    BATCH_CRON_MINUTE: int = 0

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
