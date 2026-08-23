from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.models import Question, StudentAnswer
from app.db.session import get_db
from app.schemas.question import QuestionResponse, QuestionUpdate

router = APIRouter(
    prefix="/api/questions",
    tags=["questions"],
    dependencies=[Depends(require_admin)],
)


def _get_question_or_404(question_id: int, db: Session) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found",
        )
    return question


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: int, db: Session = Depends(get_db)) -> Question:
    return _get_question_or_404(question_id, db)


@router.put("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int, payload: QuestionUpdate, db: Session = Depends(get_db)
) -> Question:
    question = _get_question_or_404(question_id, db)
    question.question_text = payload.question_text
    question.option_a = payload.option_a
    question.option_b = payload.option_b
    question.option_c = payload.option_c
    question.option_d = payload.option_d
    question.correct_answer = payload.correct_answer
    db.commit()
    db.refresh(question)
    return question


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(question_id: int, db: Session = Depends(get_db)) -> None:
    question = _get_question_or_404(question_id, db)

    has_answers = (
        db.query(StudentAnswer).filter(StudentAnswer.question_id == question_id).first()
        is not None
    )
    if has_answers:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a question that already has student answers",
        )

    db.delete(question)
    db.commit()
