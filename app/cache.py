import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.llm import generate_json
from app.perenual import search_plant
from app.prompts import REGIONAL_PLANTS_SYSTEM, REGIONAL_PLANTS_USER, current_season

CACHE_DIR = Path(__file__).parent.parent / ".cache"

log = logging.getLogger(__name__)


@dataclass
class PlantResult:
    plants: list[dict]
    cache_hit: bool
    prompt: str | None = None
    raw_response: str | None = None


def _cache_path(region: str, season: str) -> Path:
    CACHE_DIR.mkdir(exist_ok=True)
    safe_key = f"{region}_{season}".lower().replace(" ", "_")
    return CACHE_DIR / f"plants_{safe_key}.json"


def get_cached_plants(region: str, season: str) -> list[dict] | None:
    path = _cache_path(region, season)
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_cached_plants(region: str, season: str, plants: list[dict]) -> None:
    path = _cache_path(region, season)
    path.write_text(json.dumps(plants, indent=2))


def _clean_latin(name: str) -> str:
    """Strip hybrid symbols and cultivar names for better search results."""
    import re
    name = name.replace("×", "").replace("×", "")
    name = re.sub(r"['‘’].+?['‘’]", "", name)
    return " ".join(name.split())


async def _enrich_plant(plant: dict) -> dict:
    """Merge Trefle metadata into an LLM-generated plant dict."""
    if not settings.trefle_api_key:
        return plant
    try:
        queries = [plant["name"]]
        if plant.get("latin"):
            queries.append(plant["latin"])
            cleaned = _clean_latin(plant["latin"])
            if cleaned != plant["latin"]:
                queries.append(cleaned)
            genus = cleaned.split()[0]
            if genus not in queries:
                queries.append(genus)
        info = None
        for q in queries:
            info = await search_plant(q)
            if info and info.get("image_url"):
                break
        if info and not info.get("image_url"):
            info = None
    except Exception as e:
        log.warning("Trefle lookup failed for %s: %s", plant["name"], e)
        return plant
    if info:
        plant.update(info)
    return plant


async def _enrich_plants(plants: list[dict]) -> list[dict]:
    return await asyncio.gather(*[_enrich_plant(p) for p in plants])


async def get_regional_plants(region: str) -> PlantResult:
    season = current_season()
    cached = get_cached_plants(region, season)
    if cached is not None:
        return PlantResult(plants=cached, cache_hit=True)

    prompt = REGIONAL_PLANTS_USER.format(region=region, season=season)
    plants, raw = await generate_json(REGIONAL_PLANTS_SYSTEM, prompt)
    plants = await _enrich_plants(plants)
    save_cached_plants(region, season, plants)
    return PlantResult(plants=plants, cache_hit=False, prompt=prompt, raw_response=raw)
