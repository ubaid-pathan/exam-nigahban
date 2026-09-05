import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.seed_monitoring_rules import seed_monitoring_rules
from app.db.session import get_db
from app.main import app
from app.db.models import Student, User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def _reset_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        seed_monitoring_rules(db)
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _isolate_evidence_storage(tmp_path, monkeypatch):
    # Evidence files are real filesystem writes, independent of the
    # in-memory test database above. Redirect them to a pytest-managed
    # temp directory so test runs never write into the repository's real
    # evidence/ folder.
    monkeypatch.setattr(settings, "evidence_storage_root", str(tmp_path))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_user(db_session):
    user = User(
        username="admin1",
        password_hash=hash_password("adminpass123"),
        role="admin",
        status=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_user(db_session):
    user = User(
        username="student1",
        password_hash=hash_password("studentpass123"),
        role="student",
        status=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def student_profile(db_session, student_user):
    student = Student(
        user_id=student_user.id,
        student_id="STU-1001",
        full_name="Test Student",
        department="Computer Science",
        class_name="CS-101",
        is_active=True,
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def inactive_user(db_session):
    user = User(
        username="inactive1",
        password_hash=hash_password("inactivepass123"),
        role="student",
        status=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def auth_headers(client: TestClient, username: str, password: str) -> dict:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
