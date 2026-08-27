from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin_dashboard,
    audit,
    auth,
    evidence,
    exams,
    monitoring,
    questions,
    student_exams,
    users,
)
from app.core.config import settings

app = FastAPI(
    title="Exam Nigahban API",
    description="AI-assisted online examination monitoring system",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(exams.router)
app.include_router(questions.router)
app.include_router(student_exams.router)
app.include_router(monitoring.router)
app.include_router(evidence.router)
app.include_router(admin_dashboard.router)
app.include_router(audit.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "exam-nigahban-api",
    }