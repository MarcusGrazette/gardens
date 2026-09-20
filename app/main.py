import json
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.cache import get_regional_plants, _enrich_plant
from app.geocode import geocode_postcode
from app.models import RecommendationRequest, RecommendationResponse
from app.prompts import (
    RECOMMENDATIONS_SYSTEM,
    RECOMMENDATIONS_USER,
    REGIONAL_PLANTS_SYSTEM,
    current_season,
)
from app.llm import generate_json
from app.user import load_user, create_user, set_task_status, update_history, get_task_state, current_week, get_garden_plants, set_garden_plants
from app.weather import fetch_forecast, summarise_forecast

import re

CACHE_DIR = Path(__file__).parent.parent / ".cache"

COMMON_PLANTS = {
    "tulip", "daffodil", "crocus", "allium", "snowdrop", "hyacinth",
    "bluebell", "iris", "lily", "peony", "dahlia", "geranium", "fuchsia",
    "cyclamen", "lavender", "heather", "clematis", "wisteria", "jasmine",
    "hydrangea", "camellia", "magnolia", "azalea", "rhododendron", "rose",
    "foxglove", "lupin", "delphinium", "hollyhock", "sunflower", "pansy",
    "primrose", "viola", "aster", "verbena", "salvia", "cosmos",
}


def _extract_extra_plants(actions: list[dict], known: set[str]) -> list[str]:
    """Find plant names in action text not already in the known set."""
    text = " ".join(a.get("title", "") + " " + a.get("detail", "") for a in actions)
    candidates = set()
    for word in re.findall(r"\b[A-Za-z][a-z]{2,}\b", text):
        if word.lower() in COMMON_PLANTS and word.lower() not in known:
            candidates.add(word.lower())
    return list(candidates)


def _recs_cache_path(postcode: str, week: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    safe_key = f"{postcode}_{week}".lower().replace(" ", "_")
    return CACHE_DIR / f"recs_{safe_key}.json"


def get_cached_recs(postcode: str, week: str) -> dict | None:
    path = _recs_cache_path(postcode, week)
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_cached_recs(postcode: str, week: str, data: dict) -> None:
    path = _recs_cache_path(postcode, week)
    path.write_text(json.dumps(data, indent=2))

app = FastAPI(title="This Week in the Garden")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = load_user()
    return templates.TemplateResponse(request, "index.html", {
        "user": user,
        "week": current_week(),
        "task_state": get_task_state(user) if user else {},
    })


@app.post("/onboard")
async def onboard(request: Request):
    form = await request.form()
    postcode = form.get("postcode", "").strip()
    if not postcode:
        raise HTTPException(status_code=400, detail="Postcode required")
    geo = await geocode_postcode(postcode)
    create_user(geo.postcode, {
        "latitude": geo.latitude,
        "longitude": geo.longitude,
        "region": geo.region,
        "admin_district": geo.admin_district,
    })
    return RedirectResponse("/", status_code=303)


class TaskStateUpdate(BaseModel):
    priority: int
    status: str | None = None
    done_count: int | None = None
    total_count: int | None = None


@app.post("/api/task-state")
async def api_task_state(update: TaskStateUpdate):
    user = load_user()
    if not user:
        raise HTTPException(status_code=404, detail="No user profile")
    user = set_task_status(user, update.priority, update.status)
    if update.done_count is not None and update.total_count is not None:
        user = update_history(user, update.done_count, update.total_count)
    return {"ok": True}


@app.get("/api/task-state")
async def api_get_task_state():
    user = load_user()
    if not user:
        return {"tasks": {}, "history": []}
    return {
        "tasks": get_task_state(user),
        "history": user.get("history", []),
    }


class PlantsUpdate(BaseModel):
    plants: list[str]


@app.get("/api/plants")
async def api_get_plants():
    user = load_user()
    if not user:
        return {"plants": []}
    return {"plants": get_garden_plants(user)}


@app.post("/api/plants")
async def api_set_plants(update: PlantsUpdate):
    user = load_user()
    if not user:
        raise HTTPException(status_code=404, detail="No user profile")
    set_garden_plants(user, update.plants)
    return {"ok": True, "plants": update.plants}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/recommendations/stream")
async def recommendations_stream(postcode: str | None = None):
    if not postcode:
        user = load_user()
        if not user:
            async def no_user():
                yield _sse("error", {"message": "No user profile. Please complete onboarding."})
            return StreamingResponse(no_user(), media_type="text/event-stream")
        postcode = user["postcode"]
    async def generate():
        today = date.today()
        week = today.strftime("%G-W%V")

        # Check recommendation cache
        cached_recs = get_cached_recs(postcode, week)
        if cached_recs is not None:
            yield _sse("step", {"step": 6, "label": "Loaded from cache"})
            yield _sse("done", cached_recs)
            return

        # 1. Validate + geocode
        yield _sse("step", {"step": 0, "label": "Validating postcode..."})
        try:
            geo = await geocode_postcode(postcode)
        except ValueError as e:
            yield _sse("error", {"message": str(e)})
            return
        yield _sse("step", {"step": 1, "label": f"Located: {geo.admin_district or geo.region}"})
        yield _sse("debug", {
            "section": "geocode",
            "data": geo.model_dump(),
        })

        # 2. Weather
        yield _sse("step", {"step": 2, "label": "Fetching weather forecast..."})
        try:
            time_series = await fetch_forecast(geo.latitude, geo.longitude)
            forecast = summarise_forecast(time_series)
        except Exception as e:
            yield _sse("error", {"message": f"Weather API error: {e}"})
            return
        yield _sse("step", {"step": 3, "label": "Weather forecast received"})
        yield _sse("debug", {
            "section": "weather",
            "data": {
                "raw_days": time_series[:7],
                "summary": forecast,
            },
        })

        # 3. Regional plants
        yield _sse("step", {"step": 4, "label": "Loading regional plant data..."})
        try:
            plant_result = await get_regional_plants(geo.region)
        except Exception as e:
            yield _sse("error", {"message": f"Plant data error: {e}"})
            return
        plant_names = [p["name"] for p in plant_result.plants]
        plants_str = ", ".join(plant_names) + " (regional defaults)"
        cache_label = "from cache" if plant_result.cache_hit else "generated by LLM"
        yield _sse("step", {"step": 5, "label": f"Loaded {len(plant_result.plants)} plants ({cache_label})"})
        yield _sse("debug", {
            "section": "plants",
            "data": {
                "cache_hit": plant_result.cache_hit,
                "plants": plant_result.plants,
                "llm_prompt": plant_result.prompt,
                "llm_system_prompt": REGIONAL_PLANTS_SYSTEM if not plant_result.cache_hit else None,
                "llm_raw_response": plant_result.raw_response,
            },
        })

        # 4. Generate recommendations
        yield _sse("step", {"step": 6, "label": "Generating your garden plan..."})
        user_prompt = RECOMMENDATIONS_USER.format(
            postcode=geo.postcode,
            region=geo.region,
            date=today.isoformat(),
            week=week,
            season=current_season(),
            forecast=forecast,
            plants=plants_str,
        )
        try:
            result, raw_response = await generate_json(RECOMMENDATIONS_SYSTEM, user_prompt)
        except Exception as e:
            yield _sse("error", {"message": f"LLM error: {e}"})
            return

        yield _sse("debug", {
            "section": "recommendations",
            "data": {
                "system_prompt": RECOMMENDATIONS_SYSTEM,
                "user_prompt": user_prompt,
                "raw_response": raw_response,
            },
        })
        # 5. Enrich any extra plants mentioned in actions but not in regional list
        all_plants = list(plant_result.plants)
        known_names = {p["name"].lower() for p in all_plants}
        extra_names = _extract_extra_plants(result.get("actions", []), known_names)
        for s in result.get("plant_suggestions", []):
            sname = s["name"].lower() if isinstance(s, dict) else s.lower()
            if sname not in known_names and sname not in extra_names:
                extra_names.append(sname)
        if extra_names:
            import asyncio
            extras = await asyncio.gather(*[
                _enrich_plant({"name": n}) for n in extra_names
            ])
            all_plants.extend([e for e in extras if e.get("image_url")])

        result["regional_plants"] = all_plants
        save_cached_recs(postcode, week, result)
        yield _sse("done", result)

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/recommendations", response_model=RecommendationResponse)
async def recommendations(req: RecommendationRequest):
    try:
        geo = await geocode_postcode(req.postcode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        time_series = await fetch_forecast(geo.latitude, geo.longitude)
        forecast = summarise_forecast(time_series)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {e}")

    plant_result = await get_regional_plants(geo.region)
    if req.plants:
        plants_str = ", ".join(req.plants)
    else:
        plant_names = [p["name"] for p in plant_result.plants]
        plants_str = ", ".join(plant_names) + " (regional defaults — user has not specified their plants)"

    today = date.today()
    user_prompt = RECOMMENDATIONS_USER.format(
        postcode=geo.postcode,
        region=geo.region,
        date=today.isoformat(),
        week=today.strftime("%G-W%V"),
        season=current_season(),
        forecast=forecast,
        plants=plants_str,
    )

    try:
        result, _ = await generate_json(RECOMMENDATIONS_SYSTEM, user_prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    return RecommendationResponse(**result)
