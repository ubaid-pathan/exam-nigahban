from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    admin_dashboard,
    audit,
    auth,
    enforcement,
    evidence,
    exams,
    monitoring,
    monitoring_rules,
    questions,
    student_exams,
    users,
)
from app.core.config import settings
from app.websocket import router as websocket_router

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
app.include_router(monitoring_rules.router)
app.include_router(enforcement.router)
app.include_router(audit.router)
app.include_router(websocket_router.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "exam-nigahban-api",
    }