from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import hash_password
from app.db.models import Student, User
from app.db.session import get_db
from app.schemas.user import AdminCreateRequest, StudentCreateRequest, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])


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
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user
