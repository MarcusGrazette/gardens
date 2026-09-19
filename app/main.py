from datetime import date

from fastapi import FastAPI, HTTPException

from app.cache import get_regional_plants
from app.geocode import geocode_postcode
from app.models import RecommendationRequest, RecommendationResponse
from app.prompts import RECOMMENDATIONS_SYSTEM, RECOMMENDATIONS_USER, current_season
from app.llm import generate_json
from app.weather import fetch_forecast, summarise_forecast

app = FastAPI(title="Garden Todo")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/recommendations", response_model=RecommendationResponse)
async def recommendations(req: RecommendationRequest):
    # 1. Geocode
    try:
        geo = await geocode_postcode(req.postcode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Weather
    try:
        time_series = await fetch_forecast(geo.latitude, geo.longitude)
        forecast = summarise_forecast(time_series)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Weather API error: {e}")

    # 3. Regional plants (cached)
    regional_plants = await get_regional_plants(geo.region)
    if req.plants:
        plants_str = ", ".join(req.plants)
    else:
        plant_names = [p["name"] for p in regional_plants]
        plants_str = ", ".join(plant_names) + " (regional defaults — user has not specified their plants)"

    # 4. Generate recommendations
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
        result = await generate_json(RECOMMENDATIONS_SYSTEM, user_prompt)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    return RecommendationResponse(**result)
