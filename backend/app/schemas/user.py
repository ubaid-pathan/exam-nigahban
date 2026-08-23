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
