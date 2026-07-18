from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    secret_key: str = "dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours
    totp_session_expire_minutes: int = 5
    # The default install serves plain HTTP (no TLS termination baked in), so the
    # session cookie can't be marked Secure by default or logins would silently
    # break. Flip to true in .env once you've put TLS in front of the panel.
    cookie_secure: bool = False

    admin_username: str = "admin"
    admin_password: str = "changeme"

    database_url: str = "sqlite+aiosqlite:///./carbonpanel.db"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
    ]

    metrics_interval_seconds: float = 2.0
    process_limit: int = 25


settings = Settings()
