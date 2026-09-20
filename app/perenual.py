import httpx

from app.config import settings

TREFLE_SEARCH_URL = "https://trefle.io/api/v1/plants/search"


def _best_match(query: str, results: list[dict]) -> dict | None:
    """Pick the result whose common_name best matches the query."""
    q = query.lower()
    for plant in results:
        if (plant.get("common_name") or "").lower() == q:
            return plant
    for plant in results:
        if q in (plant.get("common_name") or "").lower():
            return plant
    return results[0] if results else None


async def search_plant(name: str) -> dict | None:
    """Search Trefle for a plant by name. Returns enriched data or None."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            TREFLE_SEARCH_URL,
            params={"token": settings.trefle_api_key, "q": name},
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

    plant = _best_match(name, data)
    if not plant:
        return None

    return {
        "trefle_id": plant["id"],
        "common_name": plant.get("common_name"),
        "scientific_name": plant.get("scientific_name"),
        "image_url": plant.get("image_url"),
    }
