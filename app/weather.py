from datetime import datetime

import httpx

from app.config import settings

DAILY_URL = "https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point/daily"


async def fetch_forecast(latitude: float, longitude: float) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            DAILY_URL,
            params={"latitude": latitude, "longitude": longitude},
            headers={
                "apikey": settings.met_office_api_key,
                "accept": "application/json",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

    time_series = data["features"][0]["properties"]["timeSeries"]
    return time_series


def summarise_forecast(time_series: list[dict]) -> str:
    lines = []
    for entry in time_series[:7]:
        time = entry.get("time", "")
        try:
            date_str = datetime.fromisoformat(time.replace("Z", "+00:00")).strftime("%a %d %b")
        except (ValueError, AttributeError):
            date_str = time

        day_max = entry.get("dayMaxScreenTemperature") or entry.get("maxScreenAirTemp")
        night_min = entry.get("nightMinScreenTemperature") or entry.get("minScreenAirTemp")
        precip = entry.get("dayProbabilityOfPrecipitation") or entry.get("probOfPrecipitation")
        wind = entry.get("midday10MWindSpeed") or entry.get("windSpeed10m")
        wind_gust = entry.get("midday10MWindGust") or entry.get("windGustSpeed10m")

        parts = [date_str]
        if day_max is not None:
            parts.append(f"High: {day_max}°C")
        if night_min is not None:
            parts.append(f"Low: {night_min}°C")
        if precip is not None:
            parts.append(f"Rain: {precip}%")
        if wind is not None:
            wind_str = f"Wind: {wind}mph"
            if wind_gust is not None:
                wind_str += f" (gusts {wind_gust}mph)"
            parts.append(wind_str)

        frost_warning = ""
        if night_min is not None and night_min <= 2:
            frost_warning = " ⚠ FROST RISK"

        lines.append(" | ".join(parts) + frost_warning)

    return "\n".join(lines)
