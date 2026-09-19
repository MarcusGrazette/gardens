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


REGIONAL_PLANTS_SYSTEM = "You are an expert UK horticulturist."

REGIONAL_PLANTS_USER = """List 20-30 plants commonly grown in domestic gardens in {region} during {season}.
Include a mix of vegetables, herbs, flowers, and shrubs typical for the area.
Return ONLY a JSON array of objects: [{{"name": "...", "type": "vegetable|herb|flower|shrub|tree"}}]
No other text, just the JSON array."""


RECOMMENDATIONS_SYSTEM = """You are an expert UK gardener and horticulturist. Generate a prioritised weekly action list for this gardener based on their specific situation.

You MUST return ONLY valid JSON matching this schema, with no other text:
{{
  "week": "YYYY-WNN",
  "actions": [
    {{
      "priority": 1,
      "title": "Short action title",
      "detail": "Specific, actionable detail referencing weather and plants",
      "category": "weather-response|seasonal-planting|maintenance|harvesting|pest-control|soil-care",
      "urgent": true/false
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
  "plant_suggestions": ["plant1", "plant2"],
  "notes": "Optional general observations"
}}"""

RECOMMENDATIONS_USER = """Context:
- Location: {postcode}, region: {region}
- Current date: {date}, Week {week}
- Season: {season}
- Weather forecast (next 7 days):
{forecast}
- Plants: {plants}

Generate 5-7 actions for this week, ordered by priority. Each action should be specific (not "water your plants" but "water tomatoes deeply 2-3 times this week due to forecasted dry spell"). Flag any urgent items (frost warnings, pest alerts, time-sensitive planting windows). For new/minimal profiles, include suggestions for what to plant this time of year. Include any inferences you made about the garden."""
