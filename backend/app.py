"""FastAPI entrypoint: recommendations API + DriveQuest chat + static UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Allow `uvicorn backend.app:app` and `python backend/app.py`
BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent import apply_ui_choice, chat, new_session  # noqa: E402
from catalog import list_cars  # noqa: E402
from models import Car  # noqa: E402
from recommendation_engine import PreferenceState, enrich_car, rank_cars  # noqa: E402

app = FastAPI(title="DriveQuest Car Recommender", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = create_engine("sqlite:///cars.db")
Session = sessionmaker(bind=engine)

FRONTEND_DIR = ROOT / "frontend"


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None


class ChoiceRequest(BaseModel):
    session_id: str | None = None
    stage: str
    value: str | float | int


@app.get("/health")
def health():
    return {
        "ok": True,
        "catalog_size": len(list_cars()),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.get("/recommendations/")
def get_recommendations(budget: float):
    """Legacy SQLite endpoint — kept for compatibility with the original app."""
    session = Session()
    try:
        cars = session.query(Car).filter(Car.price <= budget).all()
        if cars:
            return [{"make": car.make, "model": car.model, "price": car.price} for car in cars]
    finally:
        session.close()
    # Fall back to catalog when DB is empty
    prefs = PreferenceState(budget=budget, stage="compare")
    ranked = rank_cars(list_cars(), prefs, limit=10)
    return [
        {"make": c["make"], "model": c["model"], "price": c["price"], "overall": c["overall"]}
        for c in ranked
    ]


@app.get("/api/catalog")
def api_catalog(budget: float | None = None):
    cars = [enrich_car(c, budget) for c in list_cars()]
    cars.sort(key=lambda c: c["overall"], reverse=True)
    return {"cars": cars}


@app.post("/api/session")
def api_new_session():
    return new_session()


@app.post("/api/chat")
def api_chat(body: ChatRequest):
    return chat(body.message, body.session_id)


@app.post("/api/choice")
def api_choice(body: ChoiceRequest):
    if not body.stage:
        raise HTTPException(status_code=400, detail="stage required")
    return apply_ui_choice(body.session_id, body.stage, body.value)


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
