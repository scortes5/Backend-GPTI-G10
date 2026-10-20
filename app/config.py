from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./agrotracker.db"
    frontend_url: str = "http://localhost:8501"
    instacrops_api_url: str = "https://api.instacrops.com"
    instacrops_api_key: str = ""
    ia_proveedor: str = "simulado"
    ia_modelo: str = "claude-opus-5-5"
    anthropic_api_key: str = ""
    secret_key: str = ""
    token_minutos: int = 480
    admin_nombre: str = "Administrador"
    admin_email: str = ""
    admin_clave: str = ""
    correo_proveedor: str = "simulado"
    correo_remitente: str = "AgroTracker <no-reply@agrotracker.cl>"
    smtp_host: str = "smtp.gmail.com"
    smtp_puerto: int = 587
    smtp_usuario: str = ""
    smtp_clave: str = ""


settings = Settings()
