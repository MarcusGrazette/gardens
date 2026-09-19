import json
from pathlib import Path

from app.llm import generate_json
from app.prompts import REGIONAL_PLANTS_SYSTEM, REGIONAL_PLANTS_USER, current_season

CACHE_DIR = Path(__file__).parent.parent / ".cache"


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


async def get_regional_plants(region: str) -> list[dict]:
    season = current_season()
    cached = get_cached_plants(region, season)
    if cached is not None:
        return cached

    prompt = REGIONAL_PLANTS_USER.format(region=region, season=season)
    plants = await generate_json(REGIONAL_PLANTS_SYSTEM, prompt)
    save_cached_plants(region, season, plants)
    return plants
