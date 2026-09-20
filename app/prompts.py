from datetime import date

SEASONS = {
    (3, 4, 5): "spring",
    (6, 7, 8): "summer",
    (9, 10, 11): "autumn",
    (12, 1, 2): "winter",
}


def current_season() -> str:
    month = date.today().month
    for months, name in SEASONS.items():
        if month in months:
            return name
    return "spring"


REGIONAL_PLANTS_SYSTEM = "You are an expert UK horticulturist specialising in ornamental and home gardens."

REGIONAL_PLANTS_USER = """List the 10 most popular ornamental plants grown in home gardens in {region} during {season}.
Focus on flowers, shrubs, climbers and perennials typical of beds, borders, pots and containers.
Do NOT include vegetables, crops or agricultural plants.
Use specific common names (e.g. "English lavender" not "lavender", "Floribunda rose" not "rose").
Return ONLY a JSON array of objects: [{{"name": "...", "latin": "...", "type": "flower|shrub|climber|perennial|bulb|tree"}}]
No other text, just the JSON array."""


RECOMMENDATIONS_SYSTEM = """You are an expert UK gardener specialising in ornamental home gardens — beds, borders, pots and containers. Generate a prioritised weekly action list for this home gardener.

Focus on flowers, shrubs, climbers, perennials and bulbs. Do NOT suggest vegetable growing, crop rotation or agricultural tasks unless the user has specifically listed edible plants.

You MUST return ONLY valid JSON matching this schema, with no other text:
{{
  "week": "YYYY-WNN",
  "summary": "One punchy sentence joining the weather forecast to the top gardening priority this week, max 120 characters. E.g. 'Seven mild, dry days on clay loam — the best bulb-planting window before the ground cools.'",
  "actions": [
    {{
      "priority": 1,
      "title": "Short action title",
      "detail": "Specific, actionable detail referencing weather and plants",
      "category": "weather-response|seasonal-planting|maintenance|pruning|pest-control|soil-care",
      "urgent": true/false,
      "why_now": "One sentence explicitly connecting the forecast numbers to why this task matters this week",
      "minutes": 20
    }}
  ],
  "inferences": [
    {{
      "field": "soil_type|plants|etc",
      "value": "inferred value",
      "confidence": "high|medium|low",
      "reasoning": "why you inferred this"
    }}
  ],
  "plant_suggestions": [
    {{
      "name": "Common name",
      "latin": "Scientific name",
      "note": "Short reason to plant now, e.g. 'Jan colour', 'Scent', 'Pollinator-friendly'"
    }}
  ],
  "notes": "Optional general observations"
}}"""

RECOMMENDATIONS_USER = """Context:
- Location: {postcode}, region: {region}
- Current date: {date}, Week {week}
- Season: {season}
- Weather forecast (next 7 days):
{forecast}
- Plants in garden: {plants}

Generate 5-7 actions for this week, ordered by priority. Each action should be specific to ornamental home gardening (not "water your plants" but "water dahlias deeply 2-3 times this week due to forecasted dry spell"). Flag any urgent items (frost warnings, pest alerts, time-sensitive planting windows). For new/minimal profiles, suggest ornamental plants to add this time of year. Include any inferences you made about the garden."""
