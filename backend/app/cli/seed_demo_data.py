"""Seed the database with demo data for hackathon presentations.

Creates:
  - 1 admin account (username: admin, password: Admin@2026)
  - 5 student accounts with profiles
  - 2 active exams with 5 questions each

Usage:
    python -m app.cli.seed_demo_data

Refuses to run if any admin already exists (same safety gate as
create_admin).  Idempotent for students/exams — skips records that
already exist by username or student_id.
"""

from __future__ import annotations

import sys

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import Exam, Question, Student, User
from app.db.session import SessionLocal


# ---------------------------------------------------------------------------
# Demo data
# ---------------------------------------------------------------------------

ADMIN_ACCOUNT = {
    "username": "admin",
    "password": "Admin@2026",
    "full_name": "System Administrator",
    "email": "admin@examnigahban.pk",
}

STUDENTS = [
    {
        "username": "ahmad.khan",
        "password": "Student@2026",
        "student_id": "FA22-BCS-001",
        "full_name": "Ahmad Khan",
        "department": "Computer Science",
        "class_name": "BS-CS Semester 6",
        "email": "ahmad.khan@university.edu.pk",
    },
    {
        "username": "fatima.zahra",
        "password": "Student@2026",
        "student_id": "FA22-BCS-002",
        "full_name": "Fatima Zahra",
        "department": "Computer Science",
        "class_name": "BS-CS Semester 6",
        "email": "fatima.zahra@university.edu.pk",
    },
    {
        "username": "ali.hassan",
        "password": "Student@2026",
        "student_id": "FA22-BCS-003",
        "full_name": "Ali Hassan",
        "department": "Software Engineering",
        "class_name": "BS-SE Semester 4",
        "email": "ali.hassan@university.edu.pk",
    },
    {
        "username": "aisha.malik",
        "password": "Student@2026",
        "student_id": "FA22-BCS-004",
        "full_name": "Aisha Malik",
        "department": "Computer Science",
        "class_name": "BS-CS Semester 6",
        "email": "aisha.malik@university.edu.pk",
    },
    {
        "username": "usman.tariq",
        "password": "Student@2026",
        "student_id": "FA22-BCS-005",
        "full_name": "Usman Tariq",
        "department": "Artificial Intelligence",
        "class_name": "BS-AI Semester 5",
        "email": "usman.tariq@university.edu.pk",
    },
]

EXAMS = [
    {
        "title": "Introduction to Artificial Intelligence",
        "description": (
            "Covers fundamental AI concepts including search algorithms, "
            "knowledge representation, machine learning basics, and neural "
            "networks. Designed for BS Computer Science Semester 6."
        ),
        "duration_minutes": 45,
        "status": "active",
        "questions": [
            {
                "question_text": (
                    "Which search algorithm guarantees an optimal solution "
                    "when all edge costs are non-negative?"
                ),
                "option_a": "Depth-First Search",
                "option_b": "Breadth-First Search",
                "option_c": "A* Search with an admissible heuristic",
                "option_d": "Greedy Best-First Search",
                "correct_answer": "C",
            },
            {
                "question_text": (
                    "In a neural network, what is the primary purpose of "
                    "the backpropagation algorithm?"
                ),
                "option_a": "To initialize weights randomly",
                "option_b": (
                    "To compute gradients and update weights to minimize "
                    "the loss function"
                ),
                "option_c": "To normalize input features",
                "option_d": "To select the best activation function",
                "correct_answer": "B",
            },
            {
                "question_text": (
                    "Which of the following is an example of unsupervised "
                    "learning?"
                ),
                "option_a": "Spam email classification",
                "option_b": "Customer segmentation using K-Means clustering",
                "option_c": "Predicting house prices from historical data",
                "option_d": "Handwritten digit recognition",
                "correct_answer": "B",
            },
            {
                "question_text": (
                    "What does the heuristic function h(n) estimate in "
                    "informed search?"
                ),
                "option_a": "The exact cost from start to goal",
                "option_b": "The cost from the current node to the start",
                "option_c": "The estimated cost from node n to the goal",
                "option_d": "The total path cost through node n",
                "correct_answer": "C",
            },
            {
                "question_text": (
                    "Which AI technique is most suitable for game-playing "
                    "agents like chess engines?"
                ),
                "option_a": "K-Nearest Neighbors",
                "option_b": "Minimax algorithm with alpha-beta pruning",
                "option_c": "Linear regression",
                "option_d": "Naive Bayes classifier",
                "correct_answer": "B",
            },
        ],
    },
    {
        "title": "Database Management Systems",
        "description": (
            "Tests understanding of relational database concepts, SQL "
            "queries, normalization, transactions, and indexing strategies. "
            "Suitable for BS-CS Semester 4-6."
        ),
        "duration_minutes": 30,
        "status": "active",
        "questions": [
            {
                "question_text": (
                    "Which normal form eliminates transitive dependencies?"
                ),
                "option_a": "First Normal Form (1NF)",
                "option_b": "Second Normal Form (2NF)",
                "option_c": "Third Normal Form (3NF)",
                "option_d": "Boyce-Codd Normal Form (BCNF)",
                "correct_answer": "C",
            },
            {
                "question_text": (
                    "In SQL, what does the HAVING clause do that WHERE "
                    "cannot?"
                ),
                "option_a": "Filter individual rows before grouping",
                "option_b": "Filter groups after aggregation",
                "option_c": "Sort the result set",
                "option_d": "Join two tables",
                "correct_answer": "B",
            },
            {
                "question_text": (
                    "Which isolation level in database transactions "
                    "prevents dirty reads but allows non-repeatable reads?"
                ),
                "option_a": "Read Uncommitted",
                "option_b": "Read Committed",
                "option_c": "Repeatable Read",
                "option_d": "Serializable",
                "correct_answer": "B",
            },
            {
                "question_text": (
                    "What is the primary advantage of a B+ tree index over "
                    "a hash index?"
                ),
                "option_a": "Faster equality lookups",
                "option_b": "Supports range queries efficiently",
                "option_c": "Uses less disk space",
                "option_d": "Requires no maintenance",
                "correct_answer": "B",
            },
            {
                "question_text": (
                    "Which SQL statement is used to enforce referential "
                    "integrity?"
                ),
                "option_a": "CREATE INDEX",
                "option_b": "ALTER TABLE ... ADD CONSTRAINT FOREIGN KEY",
                "option_c": "CREATE VIEW",
                "option_d": "GRANT SELECT",
                "correct_answer": "B",
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------


def _seed_admin(db: Session) -> str:
    """Create the demo admin account. Returns a status message."""
    existing = db.query(User).filter(User.role == "admin").first()
    if existing:
        return f"Admin already exists ('{existing.username}'), skipping."

    admin = User(
        username=ADMIN_ACCOUNT["username"],
        password_hash=hash_password(ADMIN_ACCOUNT["password"]),
        role="admin",
        status=True,
        full_name=ADMIN_ACCOUNT["full_name"],
        email=ADMIN_ACCOUNT["email"],
    )
    db.add(admin)
    db.flush()
    return (
        f"Admin created: {admin.username} "
        f"(password: {ADMIN_ACCOUNT['password']})"
    )


def _seed_student(db: Session, data: dict) -> str:
    """Create one student + user. Idempotent by username."""
    existing = db.query(User).filter(User.username == data["username"]).first()
    if existing:
        return f"Student '{data['username']}' already exists, skipping."

    user = User(
        username=data["username"],
        password_hash=hash_password(data["password"]),
        role="student",
        status=True,
        full_name=data["full_name"],
        email=data["email"],
    )
    db.add(user)
    db.flush()

    student = Student(
        user_id=user.id,
        student_id=data["student_id"],
        full_name=data["full_name"],
        department=data["department"],
        class_name=data["class_name"],
        is_active=True,
    )
    db.add(student)
    return f"Student created: {data['full_name']} ({data['student_id']})"


def _seed_exam(db: Session, data: dict) -> str:
    """Create one exam with questions. Idempotent by title."""
    existing = db.query(Exam).filter(Exam.title == data["title"]).first()
    if existing:
        return f"Exam '{data['title']}' already exists, skipping."

    exam = Exam(
        title=data["title"],
        description=data["description"],
        duration_minutes=data["duration_minutes"],
        status=data["status"],
    )
    db.add(exam)
    db.flush()

    for q in data["questions"]:
        question = Question(exam_id=exam.id, **q)
        db.add(question)

    return f"Exam created: {data['title']} ({len(data['questions'])} questions)"


def seed_demo_data(db: Session) -> list[str]:
    """Seed all demo data. Returns a list of status messages."""
    messages: list[str] = []

    messages.append(_seed_admin(db))

    for student_data in STUDENTS:
        messages.append(_seed_student(db, student_data))

    for exam_data in EXAMS:
        messages.append(_seed_exam(db, exam_data))

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return messages


def main() -> int:
    db = SessionLocal()
    try:
        print("=" * 60)
        print("  Exam Nigahban — Demo Data Seeder")
        print("  AI National Hackathon Pakistan 2026")
        print("=" * 60)
        print()

        messages = seed_demo_data(db)
        for msg in messages:
            print(f"  [OK] {msg}")

        print()
        print("-" * 60)
        print("Demo credentials:")
        print(f"  Admin  → username: {ADMIN_ACCOUNT['username']}, "
              f"password: {ADMIN_ACCOUNT['password']}")
        for s in STUDENTS:
            print(f"  Student → username: {s['username']}, "
                  f"password: {s['password']}")
        print("-" * 60)
        return 0

    except Exception as exc:
        print(f"\nError: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
