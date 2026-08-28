from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExamStatus = Literal["draft", "active", "inactive"]


class ExamCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    duration_minutes: int = Field(gt=0)


class ExamUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    duration_minutes: int = Field(gt=0)


class ExamStatusUpdate(BaseModel):
    status: ExamStatus


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    duration_minutes: int
    status: str
    created_at: datetime
    question_count: int = 0
