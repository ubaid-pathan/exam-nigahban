from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

AnswerOption = Literal["A", "B", "C", "D"]


class StudentExamSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    duration_minutes: int
    session_status: str | None = None
    session_id: int | None = None
    question_count: int = 0


class StudentQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str


class SessionResponse(BaseModel):
    id: int
    exam_id: int
    status: str
    started_at: datetime
    ended_at: datetime | None
    remaining_seconds: int
    score: int | None


class AnswerSaveRequest(BaseModel):
    selected_answer: AnswerOption


class AnswerResponse(BaseModel):
    id: int
    session_id: int
    question_id: int
    selected_answer: str | None
    answered_at: datetime


class SubmitResponse(BaseModel):
    id: int
    exam_id: int
    status: str
    ended_at: datetime | None
    score: int | None
    total_questions: int
    answered_questions: int
