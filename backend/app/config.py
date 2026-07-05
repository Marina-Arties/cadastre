from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cadastre"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    RATE_LIMIT_PER_MINUTE: int = 10
    GEOCODER_ENABLED: bool = False
    GEOCODER_URL: str = "https://nominatim.openstreetmap.org"
    APP_NAME: str = "Кадастр объектов недвижимости"
    DEBUG: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
