from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

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

    # Full database URL override.  When set (e.g. from Neon's connection
    # string), this takes priority over the individual db_host/user/
    # password/name fields.  The driver prefix is automatically rewritten
    # to the correct SQLAlchemy dialect (postgresql+psycopg2).
    database_url: str | None = None

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

    # Evidence image storage backend.  "local" writes to the filesystem at
    # evidence_storage_root (fine for development, but ephemeral on hosts
    # like Render); "s3" uploads to S3-compatible object storage (e.g.
    # Cloudflare R2), which survives redeploys.  See
    # app/services/evidence_storage.py -- only that module knows the
    # difference between the backends.
    evidence_backend: str = "local"
    evidence_s3_endpoint_url: str | None = None
    evidence_s3_bucket: str | None = None
    evidence_s3_region: str = "auto"
    evidence_s3_access_key_id: str | None = None
    evidence_s3_secret_access_key: str | None = None

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

    @field_validator("evidence_backend")
    @classmethod
    def validate_evidence_backend(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ("local", "s3"):
            raise ValueError(
                f"Unsupported EVIDENCE_BACKEND '{value}'. "
                "Supported values: local, s3"
            )
        return normalized

    @model_validator(mode="after")
    def validate_evidence_s3_settings(self) -> "Settings":
        # Fail fast at startup: an s3 backend with missing credentials would
        # otherwise fail only when the first evidence image is saved,
        # silently losing proctoring evidence in the meantime.
        if self.evidence_backend == "s3":
            missing = [
                name
                for name, value in (
                    ("EVIDENCE_S3_BUCKET", self.evidence_s3_bucket),
                    (
                        "EVIDENCE_S3_ACCESS_KEY_ID",
                        self.evidence_s3_access_key_id,
                    ),
                    (
                        "EVIDENCE_S3_SECRET_ACCESS_KEY",
                        self.evidence_s3_secret_access_key,
                    ),
                )
                if not value or not value.strip()
            ]
            if missing:
                raise ValueError(
                    "EVIDENCE_BACKEND=s3 requires "
                    + ", ".join(missing)
                    + " to be set."
                )
        return self

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
    def database_url_resolved(self) -> str:
        # If a full DATABASE_URL was provided, rewrite its driver to the
        # correct SQLAlchemy dialect and return it directly.  This avoids
        # all encoding issues with individual fields.
        if self.database_url:
            url = make_url(self.database_url)
            if "postgres" in url.drivername:
                url = url.set(drivername="postgresql+psycopg2")
            elif "mysql" in url.drivername:
                url = url.set(drivername="mysql+pymysql")
            return url.render_as_string(hide_password=False)

        drivername, default_port = _DB_DRIVERS[self.db_driver]
        port = self.db_port if self.db_port is not None else default_port
        # Neon (and most managed Postgres) requires SSL. Adding sslmode
        # unconditionally is harmless for local MySQL and mandatory for
        # cloud Postgres providers.
        query: dict[str, str] = {}
        if self.db_driver == "postgresql":
            query["sslmode"] = "require"
        return URL.create(
            drivername=drivername,
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=port,
            database=self.db_name,
            query=query,
        ).render_as_string(hide_password=False)


settings = Settings()