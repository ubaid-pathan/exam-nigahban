from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    status: bool
    created_at: datetime


class AdminCreateRequest(BaseModel):
    username: str
    password: str


class StudentCreateRequest(BaseModel):
    username: str
    password: str
    student_id: str
    full_name: str
    department: str | None = None
    class_name: str | None = None


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
