from fastapi import FastAPI

app = FastAPI(
    title="Exam Nigahban API",
    description="AI-assisted online examination monitoring system",
    version="1.0.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "exam-nigahban-api",
    }