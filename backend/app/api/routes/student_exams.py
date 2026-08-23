from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.models import Exam, ExamSession, Question, Student, StudentAnswer, User
from app.db.session import get_db
from app.schemas.student_exam import (
    AnswerResponse,
    AnswerSaveRequest,
    SessionResponse,
    StudentExamSummary,
    StudentQuestionResponse,
    SubmitResponse,
)

router = APIRouter(prefix="/api/student", tags=["student-exams"])


def get_current_student(
    current_user: User = Depends(require_student),
    db: Session = Depends(get_db),
) -> Student:
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )
    return student


def _get_active_exam_or_404(exam_id: int, db: Session) -> Exam:
    exam = (
        db.query(Exam)
        .filter(Exam.id == exam_id, Exam.status == "active")
        .first()
    )
    if exam is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found or not currently active",
        )
    return exam


def _get_owned_session_or_404(session_id: int, student: Student, db: Session) -> ExamSession:
    session_row = (
        db.query(ExamSession)
        .filter(ExamSession.id == session_id, ExamSession.student_id == student.id)
        .first()
    )
    if session_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found",
        )
    return session_row


def _sync_expiry(session_row: ExamSession, exam: Exam, db: Session) -> ExamSession:
    if session_row.status != "in_progress":
        return session_row

    deadline = session_row.started_at + timedelta(minutes=exam.duration_minutes)
    if datetime.utcnow() >= deadline:
        session_row.status = "expired"
        session_row.ended_at = deadline
        db.commit()
        db.refresh(session_row)

    return session_row


def _remaining_seconds(session_row: ExamSession, exam: Exam) -> int:
    if session_row.status != "in_progress":
        return 0
    deadline = session_row.started_at + timedelta(minutes=exam.duration_minutes)
    remaining = (deadline - datetime.utcnow()).total_seconds()
    return max(0, int(remaining))


def _to_session_response(session_row: ExamSession, exam: Exam) -> SessionResponse:
    return SessionResponse(
        id=session_row.id,
        exam_id=session_row.exam_id,
        status=session_row.status,
        started_at=session_row.started_at,
        ended_at=session_row.ended_at,
        remaining_seconds=_remaining_seconds(session_row, exam),
        score=session_row.score,
    )


@router.get("/exams", response_model=list[StudentExamSummary])
def list_available_exams(
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> list[StudentExamSummary]:
    exams = db.query(Exam).filter(Exam.status == "active").order_by(Exam.id).all()
    sessions_by_exam = {
        s.exam_id: s.status
        for s in db.query(ExamSession).filter(ExamSession.student_id == student.id).all()
    }
    return [
        StudentExamSummary(
            id=exam.id,
            title=exam.title,
            description=exam.description,
            duration_minutes=exam.duration_minutes,
            session_status=sessions_by_exam.get(exam.id),
        )
        for exam in exams
    ]


@router.get("/exams/{exam_id}", response_model=StudentExamSummary)
def get_available_exam(
    exam_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> StudentExamSummary:
    exam = _get_active_exam_or_404(exam_id, db)
    existing = (
        db.query(ExamSession)
        .filter(ExamSession.exam_id == exam.id, ExamSession.student_id == student.id)
        .first()
    )
    return StudentExamSummary(
        id=exam.id,
        title=exam.title,
        description=exam.description,
        duration_minutes=exam.duration_minutes,
        session_status=existing.status if existing else None,
    )


@router.post(
    "/exams/{exam_id}/start",
    response_model=SessionResponse,
)
def start_exam(
    exam_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> SessionResponse:
    exam = _get_active_exam_or_404(exam_id, db)

    existing = (
        db.query(ExamSession)
        .filter(ExamSession.exam_id == exam.id, ExamSession.student_id == student.id)
        .first()
    )

    if existing is not None:
        existing = _sync_expiry(existing, exam, db)
        if existing.status == "in_progress":
            return _to_session_response(existing, exam)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This exam has already been attempted",
        )

    session_row = ExamSession(
        student_id=student.id,
        exam_id=exam.id,
        started_at=datetime.utcnow(),
        status="in_progress",
    )
    db.add(session_row)
    db.commit()
    db.refresh(session_row)
    return _to_session_response(session_row, exam)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> SessionResponse:
    session_row = _get_owned_session_or_404(session_id, student, db)
    exam = db.get(Exam, session_row.exam_id)
    session_row = _sync_expiry(session_row, exam, db)
    return _to_session_response(session_row, exam)


@router.get("/sessions/{session_id}/questions", response_model=list[StudentQuestionResponse])
def get_session_questions(
    session_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> list[Question]:
    session_row = _get_owned_session_or_404(session_id, student, db)
    exam = db.get(Exam, session_row.exam_id)
    session_row = _sync_expiry(session_row, exam, db)

    if session_row.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exam session is not active",
        )

    return (
        db.query(Question)
        .filter(Question.exam_id == session_row.exam_id)
        .order_by(Question.id)
        .all()
    )


@router.get("/sessions/{session_id}/answers", response_model=list[AnswerResponse])
def get_session_answers(
    session_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> list[StudentAnswer]:
    session_row = _get_owned_session_or_404(session_id, student, db)
    return (
        db.query(StudentAnswer)
        .filter(StudentAnswer.session_id == session_row.id)
        .order_by(StudentAnswer.question_id)
        .all()
    )


@router.put(
    "/sessions/{session_id}/answers/{question_id}",
    response_model=AnswerResponse,
)
def save_answer(
    session_id: int,
    question_id: int,
    payload: AnswerSaveRequest,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> StudentAnswer:
    session_row = _get_owned_session_or_404(session_id, student, db)
    exam = db.get(Exam, session_row.exam_id)
    session_row = _sync_expiry(session_row, exam, db)

    if session_row.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exam session is not active; answers can no longer be modified",
        )

    question = db.get(Question, question_id)
    if question is None or question.exam_id != session_row.exam_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found for this exam session",
        )

    answer = (
        db.query(StudentAnswer)
        .filter(
            StudentAnswer.session_id == session_row.id,
            StudentAnswer.question_id == question_id,
        )
        .first()
    )

    if answer is None:
        answer = StudentAnswer(
            session_id=session_row.id,
            question_id=question_id,
            selected_answer=payload.selected_answer,
            answered_at=datetime.utcnow(),
        )
        db.add(answer)
    else:
        answer.selected_answer = payload.selected_answer
        answer.answered_at = datetime.utcnow()

    db.commit()
    db.refresh(answer)
    return answer


@router.post("/sessions/{session_id}/submit", response_model=SubmitResponse)
def submit_exam(
    session_id: int,
    student: Student = Depends(get_current_student),
    db: Session = Depends(get_db),
) -> SubmitResponse:
    session_row = _get_owned_session_or_404(session_id, student, db)
    exam = db.get(Exam, session_row.exam_id)
    session_row = _sync_expiry(session_row, exam, db)

    if session_row.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exam session cannot be submitted (already finalized)",
        )

    questions = db.query(Question).filter(Question.exam_id == session_row.exam_id).all()
    answers = (
        db.query(StudentAnswer).filter(StudentAnswer.session_id == session_row.id).all()
    )
    correct_by_question = {q.id: q.correct_answer for q in questions}
    answered_count = 0
    correct_count = 0

    for answer in answers:
        expected = correct_by_question.get(answer.question_id)
        is_correct = expected is not None and answer.selected_answer == expected
        answer.is_correct = is_correct
        if answer.selected_answer is not None:
            answered_count += 1
        if is_correct:
            correct_count += 1

    total_questions = len(questions)
    score = round((correct_count / total_questions) * 100) if total_questions else 0

    session_row.status = "submitted"
    session_row.ended_at = datetime.utcnow()
    session_row.score = score
    db.commit()
    db.refresh(session_row)

    return SubmitResponse(
        id=session_row.id,
        exam_id=session_row.exam_id,
        status=session_row.status,
        ended_at=session_row.ended_at,
        score=session_row.score,
        total_questions=total_questions,
        answered_questions=answered_count,
    )
