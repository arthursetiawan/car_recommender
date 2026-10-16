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
from catalog import get_car, list_cars, load_catalog  # noqa: E402
from ev_tradeoffs import DEFAULT_ASSUMPTIONS, summarize_tradeoffs  # noqa: E402
from models import Car  # noqa: E402
from recommendation_engine import PreferenceState, enrich_car, rank_cars  # noqa: E402
from roi_calculator import calculate_ev_roi, roi_from_cars  # noqa: E402

# Reload catalog if JSON changed while server was up (dev convenience)
load_catalog.cache_clear()

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


class RoiRequest(BaseModel):
    ev_price: float | None = None
    gas_price: float | None = None
    incentive: float = 0.0
    home_charger_cost: float | None = None
    miles_per_year: float | None = None
    gas_mpg: float | None = None
    gas_price_per_gallon: float | None = None
    ev_kwh_per_100mi: float | None = None
    electricity_rate_per_kwh: float | None = None
    annual_maintenance_delta: float | None = None
    ev_car_id: str | None = None
    gas_car_id: str | None = None


@app.get("/health")
def health():
    return {
        "ok": True,
        "catalog_size": len(list_cars()),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "features": ["hex_radar", "car_images", "ev_tradeoffs", "roi_calculator"],
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


@app.get("/api/ev-tradeoffs")
def api_ev_tradeoffs(topics: str | None = None):
    topic_list = [t.strip() for t in topics.split(",")] if topics else None
    return summarize_tradeoffs(topic_list)


@app.get("/api/roi/defaults")
def api_roi_defaults():
    return {
        "assumptions": DEFAULT_ASSUMPTIONS,
        "sample_pairs": [
            {"ev_car_id": "tesla-model3-2021", "gas_car_id": "toyota-camry-2022", "label": "Model 3 vs Camry"},
            {"ev_car_id": "chevrolet-bolt-2022", "gas_car_id": "honda-civic-2023", "label": "Bolt vs Civic"},
            {"ev_car_id": "tesla-model3-2021", "gas_car_id": "toyota-corolla-2023", "label": "Model 3 vs Corolla"},
        ],
    }


@app.post("/api/roi")
def api_roi(body: RoiRequest):
    if body.ev_car_id and body.gas_car_id:
        ev_car = get_car(body.ev_car_id)
        gas_car = get_car(body.gas_car_id)
        if not ev_car or not gas_car:
            raise HTTPException(status_code=404, detail="Unknown car id")
        return roi_from_cars(
            ev_car,
            gas_car,
            incentive=body.incentive,
            miles_per_year=body.miles_per_year,
            gas_price_per_gallon=body.gas_price_per_gallon,
            electricity_rate_per_kwh=body.electricity_rate_per_kwh,
            home_charger_cost=body.home_charger_cost,
        )
    if body.ev_price is None or body.gas_price is None:
        raise HTTPException(status_code=400, detail="Provide ev_price+gas_price or car ids")
    return calculate_ev_roi(
        body.ev_price,
        body.gas_price,
        incentive=body.incentive,
        home_charger_cost=body.home_charger_cost,
        miles_per_year=body.miles_per_year,
        gas_mpg=body.gas_mpg,
        gas_price_per_gallon=body.gas_price_per_gallon,
        ev_kwh_per_100mi=body.ev_kwh_per_100mi,
        electricity_rate_per_kwh=body.electricity_rate_per_kwh,
        annual_maintenance_delta=body.annual_maintenance_delta,
    )


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
