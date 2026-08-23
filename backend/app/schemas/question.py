from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AnswerOption = Literal["A", "B", "C", "D"]


class QuestionCreate(BaseModel):
    question_text: str = Field(min_length=1)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: AnswerOption


class QuestionUpdate(BaseModel):
    question_text: str = Field(min_length=1)
    option_a: str = Field(min_length=1, max_length=500)
    option_b: str = Field(min_length=1, max_length=500)
    option_c: str = Field(min_length=1, max_length=500)
    option_d: str = Field(min_length=1, max_length=500)
    correct_answer: AnswerOption


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exam_id: int
    question_text: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    created_at: datetime
