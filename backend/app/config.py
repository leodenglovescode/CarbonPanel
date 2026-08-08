from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    secret_key: str = "dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 hours
    totp_session_expire_minutes: int = 5
    # Paired native clients (Android) can't silently re-auth the way a browser
    # can — re-pairing means physically scanning a QR again — so their tokens
    # long outlive a browser session. Safe because pairing issues a jti that
    # can be revoked from Settings at any time.
    device_token_expire_days: int = 90
    # Single-use pairing codes are short-lived by design: the window between
    # generating the QR and scanning it is seconds, not minutes.
    pairing_code_expire_minutes: int = 5
    # The default install serves plain HTTP (no TLS termination baked in), so the
    # session cookie can't be marked Secure by default or logins would silently
    # break. Flip to true in .env once you've put TLS in front of the panel.
    cookie_secure: bool = False
    # Cookies are scoped by host, not port, so two CarbonPanel instances on the
    # same machine (a prod install and a dev server on another port) share one
    # cookie slot and overwrite each other's sessions. Worse, once the prod one
    # is marked Secure, browsers refuse to let a plain-HTTP dev origin replace
    # it at all — the dev login silently keeps the prod token and every
    # subsequent request 401s. Give each instance its own name to separate them.
    cookie_name: str = "cp_session"

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
