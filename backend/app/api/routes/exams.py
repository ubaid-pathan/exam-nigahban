from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import Exam, ExamSession, Question
from app.db.session import get_db
from app.schemas.exam import (
    ExamCreate,
    ExamResponse,
    ExamStatusUpdate,
    ExamUpdate,
)
from app.schemas.question import QuestionCreate, QuestionResponse

router = APIRouter(
    prefix="/api/exams",
    tags=["exams"],
    dependencies=[Depends(require_admin)],
)


def _get_exam_or_404(exam_id: int, db: Session) -> Exam:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    return exam


def _question_count(exam_id: int, db: Session) -> int:
    return db.query(Question).filter(Question.exam_id == exam_id).count()


def _to_exam_response(exam: Exam, question_count: int) -> ExamResponse:
    return ExamResponse(
        id=exam.id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        status=exam.status,
        created_at=exam.created_at,
        question_count=question_count,
    )


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(payload: ExamCreate, db: Session = Depends(get_db)) -> ExamResponse:
    exam = Exam(
        title=payload.title,
        description=payload.description,
        duration_minutes=payload.duration_minutes,
        status="draft",
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return _to_exam_response(exam, question_count=0)


@router.get("", response_model=list[ExamResponse])
def list_exams(db: Session = Depends(get_db)) -> list[ExamResponse]:
    # Single grouped query (outer join + COUNT) instead of one COUNT per
    # exam, so listing N exams never issues N+1 queries.
    rows = (
        db.query(Exam, func.count(Question.id))
        .outerjoin(Question, Question.exam_id == Exam.id)
        .group_by(Exam.id)
        .order_by(Exam.id)
        .all()
    )
    return [_to_exam_response(exam, count) for exam, count in rows]


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(exam_id: int, db: Session = Depends(get_db)) -> ExamResponse:
    exam = _get_exam_or_404(exam_id, db)
    return _to_exam_response(exam, _question_count(exam_id, db))


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int, payload: ExamUpdate, db: Session = Depends(get_db)
) -> ExamResponse:
    exam = _get_exam_or_404(exam_id, db)
    exam.title = payload.title
    exam.description = payload.description
    exam.duration_minutes = payload.duration_minutes
    db.commit()
    db.refresh(exam)
    return _to_exam_response(exam, _question_count(exam_id, db))


@router.patch("/{exam_id}/status", response_model=ExamResponse)
def update_exam_status(
    exam_id: int, payload: ExamStatusUpdate, db: Session = Depends(get_db)
) -> ExamResponse:
    exam = _get_exam_or_404(exam_id, db)
    exam.status = payload.status
    db.commit()
    db.refresh(exam)
    return _to_exam_response(exam, _question_count(exam_id, db))


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(exam_id: int, db: Session = Depends(get_db)) -> None:
    exam = _get_exam_or_404(exam_id, db)

    has_questions = db.query(Question).filter(Question.exam_id == exam_id).first() is not None
    has_sessions = (
        db.query(ExamSession).filter(ExamSession.exam_id == exam_id).first() is not None
    )
    if has_questions or has_sessions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an exam that has questions or exam sessions",
        )

    db.delete(exam)
    db.commit()


@router.post(
    "/{exam_id}/questions",
    response_model=QuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    exam_id: int, payload: QuestionCreate, db: Session = Depends(get_db)
) -> Question:
    _get_exam_or_404(exam_id, db)

    question = Question(
        exam_id=exam_id,
        question_text=payload.question_text,
        option_a=payload.option_a,
        option_b=payload.option_b,
        option_c=payload.option_c,
        option_d=payload.option_d,
        correct_answer=payload.correct_answer,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("/{exam_id}/questions", response_model=list[QuestionResponse])
def list_questions(exam_id: int, db: Session = Depends(get_db)) -> list[Question]:
    _get_exam_or_404(exam_id, db)
    return db.query(Question).filter(Question.exam_id == exam_id).order_by(Question.id).all()
