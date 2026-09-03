from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# The exact placeholder shipped in .env.example. A real deployment must
# never boot with this value -- it's public, so anyone could forge a
# valid JWT for any user/role. Settings.validate_secret_key below rejects
# it explicitly rather than relying on an insecure fallback default.
INSECURE_SECRET_KEY_PLACEHOLDER = "CHANGE_THIS_TO_A_SECURE_RANDOM_SECRET"
MIN_SECRET_KEY_LENGTH = 32

# Supported database drivers.  "mysql" keeps the original behaviour;
# "postgresql" enables deployment to platforms like Render / Neon that
# offer free-tier Postgres.  SQLAlchemy abstracts the dialect so no
# model / route / schema code needs to change.
_DB_DRIVERS: dict[str, tuple[str, int]] = {
    "mysql": ("mysql+pymysql", 3306),
    "postgresql": ("postgresql+psycopg2", 5432),
}


class Settings(BaseSettings):
    app_name: str = "Exam Nigahban API"
    app_version: str = "1.0.0"
    environment: str = "development"

    # Set to "postgresql" for Render/Neon deployment, or "mysql" for
    # local development.  Defaults to MySQL for backward compatibility.
    db_driver: str = "mysql"
    db_host: str = "localhost"
    db_port: int | None = None  # auto-resolved from db_driver when None
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "exam_nigahban"

    secret_key: str
    cors_origins: str = "http://localhost:5173"

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # Local-filesystem evidence storage root. May be absolute, or relative
    # to the repository root. See app/services/evidence_storage.py -- this
    # is the only setting that abstraction depends on, so switching to
    # object storage later never touches model/route/schema code.
    evidence_storage_root: str = "evidence"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("SECRET_KEY must not be empty.")
        if value == INSECURE_SECRET_KEY_PLACEHOLDER:
            raise ValueError(
                "SECRET_KEY is still set to the example placeholder value "
                "from .env.example. Set a unique, random SECRET_KEY in "
                "your .env file before starting the application."
            )
        if len(value) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} "
                f"characters long (got {len(value)})."
            )
        return value

    @field_validator("db_driver")
    @classmethod
    def validate_db_driver(cls, value: str) -> str:
        if value not in _DB_DRIVERS:
            supported = ", ".join(sorted(_DB_DRIVERS))
            raise ValueError(
                f"Unsupported DB_DRIVER '{value}'. "
                f"Supported values: {supported}"
            )
        return value

    @property
    def database_url(self) -> str:
        drivername, default_port = _DB_DRIVERS[self.db_driver]
        port = self.db_port if self.db_port is not None else default_port
        return URL.create(
            drivername=drivername,
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


settings = Settings()