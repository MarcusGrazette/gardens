import re

import httpx
from pydantic import BaseModel


POSTCODE_RE = re.compile(r"^[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}$")


class GeocodedPostcode(BaseModel):
    postcode: str
    latitude: float
    longitude: float
    region: str
    admin_district: str | None = None


def validate_postcode(postcode: str) -> str:
    postcode = postcode.strip().upper()
    if not POSTCODE_RE.match(postcode):
        raise ValueError(f"Invalid UK postcode: {postcode}")
    return postcode


async def geocode_postcode(postcode: str) -> GeocodedPostcode:
    postcode = validate_postcode(postcode)
    clean = postcode.replace(" ", "")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://api.postcodes.io/postcodes/{clean}")
        resp.raise_for_status()
        data = resp.json()

    if data["status"] != 200 or data["result"] is None:
        raise ValueError(f"Postcode not found: {postcode}")

    r = data["result"]
    return GeocodedPostcode(
        postcode=r["postcode"],
        latitude=r["latitude"],
        longitude=r["longitude"],
        region=r.get("region") or r.get("country", "Unknown"),
        admin_district=r.get("admin_district"),
    )
