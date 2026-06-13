from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CodeRoute Guinee API",
    description="Plateforme nationale d'examen du code de la route en Guinee",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "CodeRoute Guinee API"}


@app.get("/api/v1/dashboard")
def dashboard() -> dict:
    return {
        "candidates": 1250,
        "accredited_centers": 18,
        "exam_sessions": 96,
        "success_rate": 72,
        "fraud_alerts": 3,
    }


@app.get("/api/v1/centers")
def centers() -> list[dict]:
    return [
        {"name": "Centre agree Kaloum", "city": "Conakry", "status": "active"},
        {"name": "Centre agree Matoto", "city": "Conakry", "status": "active"},
        {"name": "Centre agree Kankan", "city": "Kankan", "status": "pending_audit"},
    ]
