from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    app_name: str = "Exam Nigahban API"
    app_version: str = "1.0.0"
    environment: str = "development"

    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "exam_nigahban"

    secret_key: str = "CHANGE_THIS_TO_A_SECURE_RANDOM_SECRET"
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

    @property
    def database_url(self) -> str:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)


settings = Settings()