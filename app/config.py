from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./agrotracker.db"
    frontend_url: str = "http://localhost:8501"
    instacrops_api_url: str = "https://api.instacrops.com"
    instacrops_api_key: str = ""


settings = Settings()
