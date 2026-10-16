from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GearLoop API"
    app_version: str = "1.0.0"
    database_url: str = "postgresql+psycopg://gearloop:gearloop@localhost:5432/gearloop"
    # Longest checkout a borrower can ask for, in days.
    max_loan_days: int = 30
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
