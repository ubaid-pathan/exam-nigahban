from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StudentListItem(BaseModel):
    """A single row of the admin student roster (Phase 9 / Student Management).

    Built manually from a joined Student+User query (see
    app/api/routes/users.py::list_students) rather than via from_attributes,
    since it combines fields from both tables -- mirrors the pattern already
    used by AuditLogEntryResponse (app/schemas/audit.py). Never selects
    User.password_hash.

    Two independent "active" flags are surfaced deliberately: is_active is
    the Student profile flag, account_status is the User.status field that
    actually gates login (app/api/routes/auth.py). Both are set together by
    the future activate/deactivate endpoint.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    username: str
    student_id: str
    full_name: str
    email: str | None = None
    department: str | None
    class_name: str | None
    is_active: bool
    account_status: bool
    created_at: datetime


class StudentDetailResponse(StudentListItem):
    pass


class StudentUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    department: str | None = None
    class_name: str | None = None


class StudentStatusUpdate(BaseModel):
    is_active: bool


class StudentListResponse(BaseModel):
    items: list[StudentListItem]
    page: int
    page_size: int
    total: int
    total_pages: int
