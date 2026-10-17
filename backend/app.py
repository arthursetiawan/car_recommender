"""FastAPI entrypoint: multi-tenant DriveQuest dealer-group plugin + inventory ingest."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agent import apply_ui_choice, chat, new_session  # noqa: E402
from catalog import get_car, list_cars, load_catalog  # noqa: E402
from dealers import (  # noqa: E402
    DealerNotFound,
    LocationNotFound,
    authenticate_group,
    clear_caches,
    default_group_id,
    list_group_summaries,
    public_group_config,
    resolve_group,
    resolve_location_id,
)
from ev_tradeoffs import DEFAULT_ASSUMPTIONS, fuel_category, summarize_tradeoffs  # noqa: E402
from inventory_ingest import (  # noqa: E402
    apply_paste_inventory,
    apply_upload,
    template_csv_text,
    write_template_files,
)
from models import Car  # noqa: E402
from recommendation_engine import PreferenceState, enrich_car, rank_cars  # noqa: E402
from roi_calculator import calculate_ev_roi, roi_from_cars  # noqa: E402

load_catalog.cache_clear()
clear_caches()

TEMPLATES_DIR = ROOT / "data" / "templates"
write_template_files(TEMPLATES_DIR)

app = FastAPI(title="DriveQuest Dealer Group Plugin", version="3.1.0")

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
    group_id: str | None = None
    dealer_id: str | None = None  # alias for group_id
    location_id: str | None = None


class ChoiceRequest(BaseModel):
    session_id: str | None = None
    group_id: str | None = None
    dealer_id: str | None = None
    location_id: str | None = None
    stage: str
    value: str | float | int


class SessionRequest(BaseModel):
    group_id: str | None = None
    dealer_id: str | None = None
    location_id: str | None = None


class RoiRequest(BaseModel):
    group_id: str | None = None
    dealer_id: str | None = None
    location_id: str | None = None
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


class PasteInventoryRequest(BaseModel):
    group_id: str | None = None
    dealer_id: str | None = None
    text: str = Field(..., min_length=1)
    period: str | None = None
    api_key: str | None = None
    location_id: str | None = None  # default / merge target rooftop
    replace_location: bool = True


def _require_group(
    group_id: str | None = None,
    api_key: str | None = None,
    *,
    dealer_id: str | None = None,
    location_id: str | None = None,
) -> tuple[str, str | None]:
    try:
        gid = resolve_group(group_id=group_id, dealer_id=dealer_id, api_key=api_key)
        loc = resolve_location_id(gid, location_id) if location_id else None
    except DealerNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Unknown dealer group: {exc}") from exc
    except LocationNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Unknown location: {exc}") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    if not authenticate_group(gid, api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return gid, loc


@app.get("/health")
def health():
    return {
        "ok": True,
        "groups": list_group_summaries(),
        "dealers": list_group_summaries(),  # alias
        "default_group": default_group_id(),
        "default_dealer": default_group_id(),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "features": [
            "hex_radar",
            "car_images",
            "ev_tradeoffs",
            "roi_calculator",
            "dealer_groups",
            "locations",
            "embed_widget",
            "inventory_upload",
            "inventory_paste",
        ],
    }


@app.get("/api/groups")
@app.get("/api/dealers")
def api_groups():
    return {
        "groups": [public_group_config(g["id"]) for g in list_group_summaries()],
        "dealers": [public_group_config(g["id"]) for g in list_group_summaries()],
        "default_group": default_group_id(),
        "default_dealer": default_group_id(),
    }


@app.get("/api/groups/{group_id}")
@app.get("/api/dealers/{group_id}")
def api_group(group_id: str, location: str | None = None, location_id: str | None = None):
    loc = location or location_id
    try:
        return public_group_config(group_id, loc)
    except DealerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LocationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/recommendations/")
def get_recommendations(
    budget: float,
    group_id: str | None = None,
    dealer_id: str | None = None,
    location_id: str | None = None,
):
    session = Session()
    try:
        cars = session.query(Car).filter(Car.price <= budget).all()
        if cars and not (group_id or dealer_id):
            return [{"make": car.make, "model": car.model, "price": car.price} for car in cars]
    finally:
        session.close()
    gid, loc = _require_group(group_id=group_id, dealer_id=dealer_id, location_id=location_id)
    prefs = PreferenceState(budget=budget, stage="compare")
    ranked = rank_cars(list_cars(gid, loc), prefs, limit=10)
    return [
        {"make": c["make"], "model": c["model"], "price": c["price"], "overall": c["overall"]}
        for c in ranked
    ]


@app.get("/api/catalog")
def api_catalog(
    budget: float | None = None,
    group_id: str | None = None,
    dealer_id: str | None = None,
    location_id: str | None = None,
):
    gid, loc = _require_group(group_id=group_id, dealer_id=dealer_id, location_id=location_id)
    cars = [enrich_car(c, budget) for c in list_cars(gid, loc)]
    cars.sort(key=lambda c: c["overall"], reverse=True)
    return {"group_id": gid, "dealer_id": gid, "location_id": loc, "cars": cars}


@app.post("/api/session")
def api_new_session(body: SessionRequest | None = None):
    body = body or SessionRequest()
    gid, loc = _require_group(
        group_id=body.group_id,
        dealer_id=body.dealer_id,
        location_id=body.location_id,
    )
    return new_session(group_id=gid, location_id=loc)


@app.post("/api/chat")
def api_chat(body: ChatRequest):
    gid, loc = _require_group(
        group_id=body.group_id,
        dealer_id=body.dealer_id,
        location_id=body.location_id,
    )
    return chat(body.message, body.session_id, group_id=gid, location_id=loc)


@app.post("/api/choice")
def api_choice(body: ChoiceRequest):
    if not body.stage:
        raise HTTPException(status_code=400, detail="stage required")
    gid, loc = _require_group(
        group_id=body.group_id,
        dealer_id=body.dealer_id,
        location_id=body.location_id,
    )
    return apply_ui_choice(
        body.session_id,
        body.stage,
        body.value,
        group_id=gid,
        location_id=loc,
    )


@app.get("/api/ev-tradeoffs")
def api_ev_tradeoffs(topics: str | None = None):
    topic_list = [t.strip() for t in topics.split(",")] if topics else None
    return summarize_tradeoffs(topic_list)


@app.get("/api/roi/defaults")
def api_roi_defaults(
    group_id: str | None = None,
    dealer_id: str | None = None,
    location_id: str | None = None,
):
    gid, loc = _require_group(group_id=group_id, dealer_id=dealer_id, location_id=location_id)
    cars = list_cars(gid, loc)
    evs = [c for c in cars if fuel_category(c) == "electric"] or [
        c for c in cars if fuel_category(c) == "hybrid"
    ]
    gas = [c for c in cars if fuel_category(c) == "gas"]
    pairs = []
    if evs and gas:
        pairs.append(
            {
                "ev_car_id": evs[0]["id"],
                "gas_car_id": gas[0]["id"],
                "label": f"{evs[0]['make']} {evs[0]['model']} vs {gas[0]['make']} {gas[0]['model']}",
            }
        )
    return {
        "group_id": gid,
        "dealer_id": gid,
        "location_id": loc,
        "assumptions": DEFAULT_ASSUMPTIONS,
        "sample_pairs": pairs,
    }


@app.post("/api/roi")
def api_roi(body: RoiRequest):
    gid, loc = _require_group(
        group_id=body.group_id,
        dealer_id=body.dealer_id,
        location_id=body.location_id,
    )
    if body.ev_car_id and body.gas_car_id:
        ev_car = get_car(body.ev_car_id, gid, loc)
        gas_car = get_car(body.gas_car_id, gid, loc)
        if not ev_car or not gas_car:
            raise HTTPException(status_code=404, detail="Unknown car id for this group/location")
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


@app.post("/api/groups/{group_id}/inventory/upload")
@app.post("/api/dealers/{group_id}/inventory/upload")
async def api_inventory_upload(
    group_id: str,
    file: UploadFile = File(...),
    period: str | None = Form(None),
    location_id: str | None = Form(None),
    replace_location: bool = Form(True),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    gid, loc = _require_group(group_id=group_id, api_key=x_api_key, location_id=location_id)
    data = await file.read()
    result = apply_upload(
        gid,
        file.filename or "upload.csv",
        data,
        period=period,
        default_location=loc,
        replace_location=loc if (loc and replace_location) else None,
    )
    return {"group_id": gid, "dealer_id": gid, **result}


@app.post("/api/groups/{group_id}/inventory/paste")
@app.post("/api/dealers/{group_id}/inventory/paste")
def api_inventory_paste(group_id: str, body: PasteInventoryRequest):
    gid, loc = _require_group(
        group_id=group_id or body.group_id,
        dealer_id=body.dealer_id,
        api_key=body.api_key,
        location_id=body.location_id,
    )
    result = apply_paste_inventory(
        gid,
        body.text,
        period=body.period,
        default_location=loc,
        replace_location=loc if (loc and body.replace_location) else None,
    )
    return {"group_id": gid, "dealer_id": gid, **result}


@app.get("/api/templates/inventory.csv")
def api_template_csv():
    return PlainTextResponse(template_csv_text(), media_type="text/csv")


@app.get("/api/templates/inventory.xlsx")
def api_template_xlsx():
    path = TEMPLATES_DIR / "drivequest-dealer-inventory-template.xlsx"
    if not path.exists():
        write_template_files(TEMPLATES_DIR)
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="drivequest-dealer-inventory-template.xlsx",
    )


@app.get("/widget.js")
def widget_js(
    group: str | None = None,
    dealer: str | None = None,
    location: str | None = None,
    api_key: str | None = None,
):
    """Drop-in snippet: injects an iframe for a group, optionally one rooftop."""
    gid = group or dealer or default_group_id()
    js = f"""
(function () {{
  var script = document.currentScript;
  var params = new URL(script.src);
  var group = params.searchParams.get('group') || params.searchParams.get('dealer') || {gid!r};
  var location = params.searchParams.get('location') || {location!r} || '';
  var key = params.searchParams.get('api_key') || '';
  var height = params.searchParams.get('height') || '820';
  var origin = script.src.split('/widget.js')[0];
  var qs = [];
  if (location) qs.push('location=' + encodeURIComponent(location));
  if (key) qs.push('api_key=' + encodeURIComponent(key));
  var frame = document.createElement('iframe');
  frame.src = origin + '/embed/' + encodeURIComponent(group) + (qs.length ? ('?' + qs.join('&')) : '');
  frame.title = 'DriveQuest — ' + group + (location ? (' / ' + location) : '');
  frame.style.cssText = 'width:100%;max-width:1120px;height:' + height + 'px;border:0;border-radius:16px;box-shadow:0 18px 50px rgba(16,28,40,.18);background:#fff;';
  frame.loading = 'lazy';
  frame.setAttribute('allow', 'clipboard-write');
  script.parentNode.insertBefore(frame, script.nextSibling);
}})();
"""
    return Response(content=js.strip() + "\n", media_type="application/javascript")


def _inject_embed(html: str, group_id: str, location_id: str | None) -> str:
    loc_js = "null" if not location_id else repr(location_id)
    boot = (
        f"<script>window.__DQ_GROUP__={group_id!r};window.__DQ_DEALER__={group_id!r};"
        f"window.__DQ_LOCATION__={loc_js};window.__DQ_EMBED__=true;</script>\n"
    )
    return html.replace(
        '<script src="/static/app.js"></script>',
        boot + '<script src="/static/app.js"></script>',
    )


@app.get("/embed/{group_id}", response_class=HTMLResponse)
def embed_group(group_id: str, location: str | None = None, location_id: str | None = None):
    loc = location or location_id
    try:
        public_group_config(group_id, loc)
    except DealerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LocationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(_inject_embed(html, group_id, loc))


@app.get("/embed/{group_id}/{location_id}", response_class=HTMLResponse)
def embed_group_location(group_id: str, location_id: str):
    try:
        public_group_config(group_id, location_id)
    except DealerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LocationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(_inject_embed(html, group_id, location_id))


@app.get("/admin/{group_id}")
def admin_group(group_id: str, location: str | None = None):
    try:
        public_group_config(group_id, location)
    except DealerNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except LocationNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    admin = FRONTEND_DIR / "admin.html"
    html = admin.read_text(encoding="utf-8")
    html = html.replace('value="northstar-motors"', f'value="{group_id}"')
    if location:
        html = html.replace('id="location" type="text" value=""', f'id="location" type="text" value="{location}"')
    return HTMLResponse(html)


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def index():
        landing = FRONTEND_DIR / "landing.html"
        if landing.exists():
            return FileResponse(landing)
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
