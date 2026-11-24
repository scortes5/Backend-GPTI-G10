from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./agrotracker.db"
    frontend_url: str = "http://localhost:8501"
    instacrops_api_url: str = "https://api.instacrops.com"
    instacrops_api_key: str = ""
    instacrops_cache_minutos: int = 5
    sensores_proveedor: str = "ninguno"
    apis_simuladas: bool = False  # Agromet e Instacrops apuntan a simuladores/: se avisa en la app
    clima_proveedor: str = "simulado"
    agromet_url: str = "https://www.agromet.cl/ext/aux/getGraphData.php"
    agromet_cache_minutos: int = 15
    ia_proveedor: str = "simulado"  # simulado | gemini | claude
    ia_habilitada: bool = True  # interruptor para desactivar las recomendaciones (LA-G10-05)
    ia_limite_diario: int = 20  # consultas por usuario al día; 0 = sin límite
    gemini_api_key: str = ""
    gemini_modelo: str = "gemini-2.5-flash"
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
