import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

# Deliberately simple format check rather than adding the email-validator
# dependency (needed for Pydantic's EmailStr) -- this project has no
# existing use for it elsewhere, so a plain regex keeps validation
# dependency-free per the project's "avoid unnecessary packages" rule.
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_optional_email(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    if not _EMAIL_PATTERN.match(value):
        raise ValueError("Enter a valid email address")
    return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    status: bool
    full_name: str | None = None
    email: str | None = None
    # Exposed so the admin roster can badge the protected account and
    # disable its controls with an explanation. Deliberately not hidden: a
    # control that is disabled for a stated reason reads as intentional,
    # whereas a missing row reads as a bug.
    is_system_admin: bool = False
    created_at: datetime


class AdminCreateRequest(BaseModel):
    username: str
    password: str
    # Optional at the schema level so existing callers that only send
    # username/password (see tests/test_auth.py) keep working unchanged --
    # the frontend's Create User dialog enforces these as required before
    # ever calling the API.
    full_name: str | None = None
    email: str | None = None

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        return _validate_optional_email(value)


class StudentCreateRequest(BaseModel):
    username: str
    password: str
    student_id: str
    full_name: str
    department: str | None = None
    class_name: str | None = None
    # Optional for the same backward-compatibility reason as
    # AdminCreateRequest.email above.
    email: str | None = None

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: str | None) -> str | None:
        return _validate_optional_email(value)


class AdminListItem(UserResponse):
    """A single row of the admin roster (Phase 9 / Administrator Management).

    Same shape as UserResponse -- admins have no separate profile table the
    way students do -- kept as a distinct name to match AdminListResponse's
    `items` typing and mirror StudentListItem's naming in schemas/student.py.
    """


class AdminStatusUpdate(BaseModel):
    status: bool


class AdminListResponse(BaseModel):
    items: list[AdminListItem]
    page: int
    page_size: int
    total: int
    total_pages: int
