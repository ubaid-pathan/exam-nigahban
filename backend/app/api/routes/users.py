from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import hash_password
from app.db.models import Student, User
from app.db.session import get_db
from app.schemas.student import (
    StudentDetailResponse,
    StudentListItem,
    StudentListResponse,
    StudentStatusUpdate,
    StudentUpdate,
)
from app.schemas.user import (
    AdminCreateRequest,
    AdminListItem,
    AdminListResponse,
    AdminStatusUpdate,
    StudentCreateRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/users", tags=["users"])


def _student_response_fields(student: Student, user: User) -> dict:
    return {
        "id": student.id,
        "user_id": user.id,
        "username": user.username,
        "student_id": student.student_id,
        "full_name": student.full_name,
        "email": user.email,
        "department": student.department,
        "class_name": student.class_name,
        "is_active": student.is_active,
        "account_status": user.status,
        "created_at": student.created_at,
    }


def _get_student_row_or_404(student_id: int, db: Session) -> tuple[Student, User]:
    # student_id here is Student.id (the roster row's primary key), matching
    # the {exam_id}-is-Exam.id convention already used in exams.py -- not to
    # be confused with Student.student_id, the separate business code
    # (e.g. "STU-1001") returned in the response body.
    row = (
        db.query(Student, User)
        .join(User, User.id == Student.user_id)
        .filter(Student.id == student_id)
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    return row


@router.post(
    "/students",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_student(payload: StudentCreateRequest, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    if db.query(Student).filter(Student.student_id == payload.student_id).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Student ID already exists",
        )

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="student",
        status=True,
        email=payload.email,
    )
    db.add(user)
    db.flush()

    student = Student(
        user_id=user.id,
        student_id=payload.student_id,
        full_name=payload.full_name,
        department=payload.department,
        class_name=payload.class_name,
        is_active=True,
    )
    db.add(student)
    db.commit()
    db.refresh(user)

    return user


@router.get(
    "/students",
    response_model=StudentListResponse,
    dependencies=[Depends(require_admin)],
)
def list_students(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> StudentListResponse:
    # Explicit join, no ORM relationship traversal -- mirrors the pattern
    # used by GET /api/audit (app/api/routes/audit.py).
    query = db.query(Student, User).join(User, User.id == Student.user_id)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Student.full_name.ilike(pattern),
                Student.student_id.ilike(pattern),
                User.username.ilike(pattern),
            )
        )

    total = query.count()

    rows = query.order_by(Student.id).offset((page - 1) * page_size).limit(page_size).all()

    items = [StudentListItem(**_student_response_fields(student, user)) for student, user in rows]
    total_pages = (total + page_size - 1) // page_size

    return StudentListResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/students/{student_id}",
    response_model=StudentDetailResponse,
    dependencies=[Depends(require_admin)],
)
def get_student(student_id: int, db: Session = Depends(get_db)) -> StudentDetailResponse:
    student, user = _get_student_row_or_404(student_id, db)
    return StudentDetailResponse(**_student_response_fields(student, user))


@router.put(
    "/students/{student_id}",
    response_model=StudentDetailResponse,
    dependencies=[Depends(require_admin)],
)
def update_student(
    student_id: int, payload: StudentUpdate, db: Session = Depends(get_db)
) -> StudentDetailResponse:
    student, user = _get_student_row_or_404(student_id, db)

    # Profile fields only, per the approved Phase 9 scope -- username,
    # student_id, and password are intentionally not editable here.
    student.full_name = payload.full_name
    student.department = payload.department
    student.class_name = payload.class_name
    db.commit()
    db.refresh(student)

    return StudentDetailResponse(**_student_response_fields(student, user))


@router.patch(
    "/students/{student_id}/status",
    response_model=StudentDetailResponse,
    dependencies=[Depends(require_admin)],
)
def update_student_status(
    student_id: int, payload: StudentStatusUpdate, db: Session = Depends(get_db)
) -> StudentDetailResponse:
    student, user = _get_student_row_or_404(student_id, db)

    # User.status and Student.is_active are kept in lockstep: User.status is
    # the field actually enforced at login/auth (app/api/deps.py), while
    # Student.is_active is the profile-facing flag. Deactivation only blocks
    # future login/access -- an in-progress ExamSession is untouched here.
    student.is_active = payload.is_active
    user.status = payload.is_active
    db.commit()
    db.refresh(student)
    db.refresh(user)

    return StudentDetailResponse(**_student_response_fields(student, user))


@router.post(
    "/admins",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_admin(payload: AdminCreateRequest, db: Session = Depends(get_db)) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="admin",
        status=True,
        full_name=payload.full_name,
        email=payload.email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def _get_admin_or_404(user_id: int, db: Session) -> User:
    admin = db.query(User).filter(User.id == user_id, User.role == "admin").first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrator not found",
        )
    return admin


def _other_active_admin_count(db: Session, excluding_user_id: int) -> int:
    return (
        db.query(User)
        .filter(User.role == "admin", User.status.is_(True), User.id != excluding_user_id)
        .count()
    )


@router.get(
    "/admins",
    response_model=AdminListResponse,
    dependencies=[Depends(require_admin)],
)
def list_admins(
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> AdminListResponse:
    query = db.query(User).filter(User.role == "admin")

    if search:
        query = query.filter(User.username.ilike(f"%{search}%"))

    total = query.count()

    rows = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()

    total_pages = (total + page_size - 1) // page_size

    return AdminListResponse(
        items=[AdminListItem.model_validate(row) for row in rows],
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


@router.get(
    "/admins/{user_id}",
    response_model=AdminListItem,
    dependencies=[Depends(require_admin)],
)
def get_admin(user_id: int, db: Session = Depends(get_db)) -> User:
    return _get_admin_or_404(user_id, db)


@router.patch(
    "/admins/{user_id}/status",
    response_model=AdminListItem,
)
def update_admin_status(
    user_id: int,
    payload: AdminStatusUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> User:
    target = _get_admin_or_404(user_id, db)

    if not payload.status:
        # Checked in this order deliberately: the caller is always active
        # (enforced by get_current_user), so "deactivating this target would
        # leave zero active admins" is only ever true when target == caller.
        # Checking it first means a sole active admin deactivating themself
        # gets the more informative "last remaining admin" message, while a
        # self-deactivation attempt with other active admins still around
        # (no last-admin risk) falls through to the plain self-account rule.
        if _other_active_admin_count(db, excluding_user_id=target.id) == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot deactivate the last remaining active administrator",
            )
        if target.id == current_admin.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Admins cannot deactivate their own account",
            )

    # Activation (payload.status is True) is always allowed -- no business
    # rule restricts re-enabling an inactive admin.
    target.status = payload.status
    db.commit()
    db.refresh(target)

    return target
