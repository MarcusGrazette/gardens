# Garden Todo — Specification

## Vision

A web app for UK gardeners that generates personalised weekly action lists. Users provide information about their garden (location, plants, conditions) and receive tailored recommendations that account for local weather, soil type, time of year, and their specific plants.

The key differentiator is **degree of customisation** — every recommendation reflects that gardener's actual situation, not generic advice.

## Architecture & Tech Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Backend | **Python + FastAPI** | Async, good LLM ecosystem |
| Frontend | **Jinja2 + HTMX** | Server-rendered, minimal JS |
| CSS | **Tailwind CSS** | Utility-first, build step required |
| Database | **PostgreSQL** | Custom auth (bcrypt + sessions) |
| LLM | **OpenAI-compatible API** | Ollama locally, cloud provider (e.g. OpenCode Zen) in prod. Use `openai` Python SDK with swappable `base_url` |
| Email | **Resend** | For weekly recommendation emails |
| Background jobs | **Cron / external trigger** | Railway cron or similar hits a `/generate` endpoint weekly |
| Deployment | **Railway / Fly.io** | Ollama for local dev only |

## Data Sources

### Personalisation impact ranking

Not all data sources move the needle equally. Ranked by how much they improve the specificity of recommendations:

| Rank | Data Source | Impact | Why |
|------|------------|--------|-----|
| 1 | **Weather forecast** | Critical | Drives the most time-sensitive, location-specific advice (frost protection, watering, planting windows). A gardener in Aberdeen and one in Cornwall need completely different actions this week. |
| 2 | **User's plant list** | Critical | Without knowing what they grow, recommendations are generic. This is user-provided, not an external data source, but it's the highest-impact input after location. |
| 3 | **Soil type** | High | Determines watering frequency, suitable plants, amendment needs, drainage advice. Varies dramatically even within a few miles. |
| 4 | **Frost dates / growing season** | High | Governs planting and harvesting calendars. Derived from historical weather data + location. |
| 5 | **Daylight hours** | Medium | Affects sowing times, growth rates, when to bring plants indoors. Calculable from lat/lon — no API needed. |
| 6 | **Pest/disease risk** | Medium | Valuable when timely (e.g. blight risk from humidity + temp), but much of this is already in the LLM's training data as general seasonal knowledge. |
| 7 | **Plant care database** | Low-Medium | Useful for precise advice (spacing, feed schedules) but the LLM already has good general knowledge of common plants. Incremental rather than transformative. |

### Source catalogue

#### Tier 1 — MVP (free, API-accessible, high impact)

**postcodes.io** — Postcode geocoding
- Access: REST API, JSON, no auth required
- Endpoint: `GET https://api.postcodes.io/postcodes/:postcode`
- Pricing: Completely free, open source (MIT)
- Returns: lat/lon, region, county, admin district
- Use: Foundation for all location-dependent lookups
- Limits: No documented rate limit; generous for reasonable use

**Met Office DataHub** — UK weather forecasts
- Access: REST API, GeoJSON, API key required (free registration)
- Endpoint: `GET https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point/hourly?latitude=X&longitude=Y`
- Auth: API key in `apikey` header
- Pricing: Free tier ~360 requests/day for Site Specific forecasts
- Returns: Hourly/3-hourly/daily forecasts — temperature, wind, precipitation probability, UV, humidity
- Use: Core weather data; frost alerts from min temp forecasts
- Note: Queries by lat/lon only — use postcodes.io first

**Open-Meteo** — Weather forecasts + historical data (alternative/complement to Met Office)
- Access: REST API, JSON, no auth required
- Endpoint: `GET https://api.open-meteo.com/v1/forecast?latitude=X&longitude=Y&daily=temperature_2m_min`
- Pricing: Free for non-commercial use, up to 10,000 requests/day. Paid plans for commercial use.
- Returns: Hourly/daily forecasts, plus historical weather data back to 1940
- Use: Backup weather source; historical data is excellent for deriving frost dates and growing degree days
- Advantage over Met Office: No API key, higher rate limits, historical data included

**Sunrise/sunset — local calculation**
- No API needed. Use Python `astral` library to calculate from lat/lon + date.
- Returns: Sunrise, sunset, day length, twilight times
- Use: Daylight-sensitive recommendations (sowing times, light requirements)

#### Tier 2 — Post-MVP (free or low-cost, moderate integration effort)

**BGS Geology WMS/WFS** — Bedrock and superficial geology
- Access: OGC WMS/WFS services (standard geo APIs)
- Endpoint: `https://map.bgs.ac.uk/arcgis/services/BGS_Detailed_Geology/MapServer/WMSServer`
- Pricing: Free under Open Government Licence
- Returns: Bedrock lithology, superficial deposits — not soil directly, but parent material from which soil type can be inferred (e.g. London Clay → heavy clay soil)
- Use: Infer soil type from geology when user hasn't specified it
- Integration: Query with lat/lon bounding box, parse GML/image response

**Soilscapes (Cranfield/LandIS)** — Broad soil classification
- Access: Web viewer at `http://www.landis.org.uk/soilscapes/`, backed by WMS layers
- Pricing: Free to view; no official public API but WMS endpoint can be queried programmatically
- Returns: One of 27 soil type categories (e.g. "slowly permeable seasonally wet acid loamy and clayey soils") plus drainage characteristics
- Use: Quick soil type classification by location — coarse (1:250,000 scale) but sufficient for gardening advice
- Caveat: Reverse-engineering the WMS is fragile; no SLA or documentation

**Met Office Historic Station Data** — Historical monthly temperatures
- Access: CSV downloads from Met Office website
- Pricing: Free
- Returns: Monthly min/max temperatures for ~37 UK stations, decades of history
- Use: Pre-calculate average first/last frost dates per station, map postcodes to nearest station
- Integration: One-time download + processing, serve as static dataset

#### Tier 3 — Nice-to-have (limited access or lower impact)

**RHS Plant Data** — The gold standard for UK plant info
- Access: **No public API**. Website only at `rhs.org.uk/plants/search-form`
- Pricing: N/A — data is proprietary
- Data: ~90,000 plants with hardiness ratings (H1-H7), AGM status, growing conditions, care info
- Status: Cannot be used programmatically without a licensing agreement. Scraping likely violates ToS.
- Alternative: Rely on LLM knowledge (which has absorbed much of this information from training data) and let users correct via feedback loops

**PFAF (Plants For A Future)** — Useful/edible plant database
- Access: Bulk database download (historically ~£30-50)
- Data: ~7,000-8,000 plants with soil/sun/water requirements, edibility, hardiness
- Use: Good for edible gardening focus; less relevant for ornamental gardens
- Integration: One-time purchase, import to local DB

**Perenual** — Plant care API
- Access: REST API, freemium
- Data: Watering, sunlight, hardiness data for plants globally
- Use: Could supplement LLM knowledge for specific care instructions
- Caveat: Verify current status; global not UK-specific

**DEFRA MAGIC Map** — Agricultural Land Classification
- Access: WMS layers at `magic.defra.gov.uk`
- Pricing: Free
- Data: ALC grades 1-5 (soil quality for agriculture)
- Use: Rough proxy for soil quality; low resolution

#### Not viable / not recommended

| Source | Why not |
|--------|---------|
| RHS API | Doesn't exist |
| Cranfield LandIS detailed data | Paid licence (£hundreds+), bulk GIS delivery, no API |
| DEFRA Plant Health Portal | Statutory pests only, no API, too formal for garden use |
| NBN Atlas / GBIF | Biodiversity occurrence data, not horticultural — wrong kind of data |

### Recommended phasing

**Phase 1 (MVP):** postcodes.io + Met Office DataHub (or Open-Meteo) + LLM knowledge + `astral` for daylight. This gives location-aware, weather-driven, seasonally-appropriate recommendations with zero cost.

**Phase 2:** Add soil type via BGS geology WMS and/or Soilscapes. Pre-compute frost date dataset from Met Office historical CSVs. This significantly improves soil-specific advice and planting calendar accuracy.

**Phase 3:** Curate a static pest/disease dataset with weather-triggered alerts (e.g. Smith Period calculation for blight from temp + humidity). Build a static planting calendar dataset adjusted by region or growing degree days.

**Phase 4:** Evaluate whether plant-specific data (PFAF, Perenual) adds enough value over LLM knowledge to justify the integration. Consider RHS data licensing if the app reaches commercial scale.

## User Data Model

```
User:
  - email (unique, used for auth)
  - password_hash
  - postcode (required — minimum viable input)
  - garden_orientation (N/S/E/W, optional)
  - shade_level (full sun / partial / full shade, optional)
  - garden_size (small/medium/large, optional)
  - plants[] (list of plant names/types, optional)
  - soil_type (optional — can be inferred from postcode)
  - experience_level (beginner/intermediate/experienced, optional)
  - created_at
  - updated_at
```

## Core LLM Pipeline

This is the heart of the app and the focus of the MVP.

### MVP flow (step by step)

```
User enters postcode (e.g. "SE15 4QN")
        │
        ▼
Step 1: Validate postcode
        Regex: ^[A-Za-z]{1,2}\d[A-Za-z\d]?\s?\d[A-Za-z]{2}$
        │
        ▼
Step 2: Geocode via postcodes.io
        GET https://api.postcodes.io/postcodes/SE154QN
        → lat/lon, region (e.g. "London"), county, admin district
        │
        ▼
Step 3: Fetch weather forecast
        GET https://data.hub.api.metoffice.gov.uk/sitespecific/v0/point/hourly
            ?latitude=51.47&longitude=-0.06
        → 5-7 day forecast (temp, rain, wind, frost risk)
        │
        ▼
Step 4: Get typical plants for region (CACHED)
        Cache key: region + season (e.g. "London:autumn")
        Cache miss → LLM call: "What plants are commonly grown in
            domestic gardens in {region} in {season}? Return as JSON list."
        Cache hit → skip LLM call, use cached list
        │
        ▼
Step 5: Generate recommendations (LLM call)
        Combine: weather + regional plant list + date/season
        → Structured JSON todo list
```

The regional plant list cache avoids repeated LLM calls. Region granularity (from postcodes.io `region` field — ~12 UK regions) is coarse enough to cache efficiently but specific enough to be useful. The user refines their actual plant list via the feedback loop.

### Prompt structure (Step 5)
```
System: You are an expert UK gardener and horticulturist. Generate a prioritised
weekly action list for this gardener based on their specific situation.

Context:
- Location: {postcode}, region: {region}
- Current date: {date}, Week {week_number}
- Weather forecast (next 7 days): {forecast_summary}
- Garden: {orientation}, {shade_level}, {size}
- Soil type: {soil_type or "not specified"}
- Plants: {user_plant_list or regional_default_plants}
- Experience level: {level}
- Confirmed inferences: {confirmed_inferences or "none yet"}
- Rejected inferences: {rejected_inferences or "none yet"}
- Recently completed tasks: {completed_tasks or "none yet"}

Generate:
1. Top 5-7 actions for this week, ordered by priority
2. Each action should be specific (not "water your plants" but "water tomatoes deeply
   2-3 times this week due to forecasted dry spell")
3. Flag any urgent items (frost warnings, pest alerts, time-sensitive planting windows)
4. For new/minimal profiles, include suggestions for what to plant this time of year
5. Include any inferences you made about the garden in the "inferences" field so the user can confirm or correct them
6. Do not re-suggest tasks the user has already completed this season unless a repeat is genuinely needed
```

### Regional plant list prompt (Step 4, cached)
```
System: You are an expert UK horticulturist.

List 20-30 plants commonly grown in domestic gardens in {region} during {season}.
Include a mix of vegetables, herbs, flowers, and shrubs typical for the area.
Return as a JSON array of objects: [{"name": "...", "type": "vegetable|herb|flower|shrub|tree"}]
```

Cache strategy (MVP): simple JSON file on disk keyed by `{region}:{season}`. ~12 regions × 4 seasons = ~48 entries max. Upgrade to Redis/DB when needed.

### Output format
Structured JSON response:
```json
{
  "week": "2025-W03",
  "actions": [
    {
      "task_id": "a1b2c3",
      "priority": 1,
      "title": "Protect tender plants from forecast frost",
      "detail": "Temperatures dropping to -2°C Thursday night. Cover dahlias and move potted herbs indoors.",
      "category": "weather-response",
      "urgent": true,
      "recurrence": "one-off"
    },
    {
      "task_id": "d4e5f6",
      "priority": 3,
      "title": "Plant spring bulbs (tulips, daffodils)",
      "detail": "October is ideal for spring bulbs. Plant 10-15cm deep in well-drained spots.",
      "category": "seasonal-planting",
      "urgent": false,
      "recurrence": "seasonal"
    }
  ],
  "inferences": [
    {
      "field": "soil_type",
      "value": "heavy clay",
      "confidence": "high",
      "reasoning": "SE London postcodes are predominantly London Clay"
    }
  ],
  "plant_suggestions": [],
  "notes": "Optional general observations"
}
```

## Feedback Loops

Two critical feedback mechanisms ensure recommendations improve over time and stay relevant.

### 1. Inference confirmation

When the LLM infers information the user hasn't explicitly provided (e.g. soil type from postcode, or suggesting plants common in their area), those inferences are surfaced as editable suggestions rather than hidden assumptions.

**How it works:**
- LLM output includes an `inferences` field alongside actions:
```json
{
  "inferences": [
    {
      "field": "soil_type",
      "value": "heavy clay",
      "confidence": "high",
      "reasoning": "SE London postcodes are predominantly London Clay"
    },
    {
      "field": "plants",
      "value": ["roses", "lavender", "buddleia", "apple tree"],
      "confidence": "medium",
      "reasoning": "Common plants for south-facing suburban gardens in this area"
    }
  ]
}
```
- In the web UI, inferences appear as pre-filled but editable fields: "We think you might have these plants — adjust to match your garden"
- When the user confirms or corrects an inference, it's saved to their profile and becomes explicit data for future prompts
- Confirmed inferences are no longer re-inferred — they're treated as user-provided facts

**In the prompt**, previously confirmed/rejected inferences are included:
```
- Soil type: heavy clay (confirmed by user)
- Plants: roses, lavender, buddleia (user-confirmed); apple tree (removed by user)
```

### 2. Task completion tracking

Actions can span multiple weeks (e.g. "plant spring bulbs" is relevant throughout October). The user can mark tasks as done so they aren't repeated, and this history informs future recommendations.

**Data model:**
```
TaskCompletion:
  - user_id
  - task_title
  - task_category
  - week_generated (e.g. "2025-W40")
  - completed_at (timestamp)
```

**How it works:**
- Each weekly todo list includes a stable `task_id` (hash of title + category + season) so the same recurring task can be recognised across weeks
- User marks a task as done via the web UI (or a link in the email)
- Completed tasks are included in the next LLM prompt:
```
Recently completed tasks:
- "Plant spring bulbs (tulips, daffodils)" — completed 2025-W41
- "Apply autumn lawn feed" — completed 2025-W40
```
- The prompt instructs the LLM: "Do not re-suggest tasks the user has already completed this season unless there is a specific reason to repeat them (e.g. a second application is needed)"
- For multi-week tasks, the LLM can still mention related follow-up actions (e.g. after "plant bulbs" is done, it might suggest "water in newly planted bulbs if no rain forecast")

### Future feedback extensions
- **Task dismissal**: "Not relevant to me" — teaches the LLM to avoid similar suggestions
- **Task snoozing**: "Remind me next week" — defers without completing
- **Ratings**: Simple thumbs up/down on individual recommendations to tune quality

## Onboarding Flow (post-MVP, but designed for now)

The onboarding is progressive — the user can stop at any point and still get value:

1. **Enter postcode** → immediately get a basic todo list (LLM infers everything else)
2. **Optional: select plants** from a suggested list (LLM picks common local plants) or type their own
3. **Optional: garden details** — orientation, shade, size
4. **Optional: create account** to save profile and receive weekly emails

This "value before signup" approach means the first screen is just a postcode input and a "Get my garden todos" button.

## MVP Scope (Phase 1)

**CLI/API only** — prove the core recommendation engine works before building the web UI.

### What to build:
1. **FastAPI app** with a single endpoint: `POST /recommendations`
   - Accepts: `{ postcode, plants?, orientation?, shade?, soil_type?, experience_level? }`
   - Returns: structured JSON todo list
2. **Postcode validation** — regex check before any API calls
3. **Postcode → coordinates + region** — postcodes.io lookup (free, no auth)
4. **Weather forecast** — Met Office DataHub or Open-Meteo, queried by lat/lon
5. **Regional plant list** — LLM generates common plants for the region + season, cached as JSON file (~48 entries: 12 regions × 4 seasons)
6. **Recommendation generation** — LLM combines weather + plant list + date to produce structured todo list
7. **Config** — environment-based switching between Ollama (dev) and cloud API (prod)

### Two LLM calls per request (worst case):
1. Regional plant list (cache miss only) — generic, reusable across all users in that region
2. Personalised recommendations — unique per request, uses weather + plants + user context

On cache hit, only one LLM call is needed.

### What to defer:
- User accounts and database
- Web UI and templates
- Email sending
- Background job scheduling
- Soil/pest/plant database integrations
- Feedback loops (inference confirmation, task completion) — designed but require accounts/persistence

### Dev environment:
- Ollama running locally with a capable model (e.g. llama3, mistral)
- `.env` file for config: `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, `MET_OFFICE_API_KEY`
- `uv` for Python dependency management

## Phase 2 — Web UI + Accounts

- Jinja2 templates with HTMX for dynamic interactions
- Tailwind CSS for styling
- PostgreSQL database for user profiles
- Auth: email + password (bcrypt), session cookies
- Profile editing page to update garden info

## Phase 3 — Weekly Emails

- Resend integration for HTML emails
- Cron endpoint: `POST /generate-weekly` — iterates all users, generates recommendations, sends emails
- Unsubscribe handling

## Phase 4 — Richer Data

- Soil type lookup from BGS data
- Plant-specific care data from RHS or similar
- Pest/disease seasonal alerts
- Historical weather patterns

## Project Structure (MVP)

```
gardens/
├── app/
│   ├── main.py              # FastAPI app, routes
│   ├── config.py             # Settings from env vars
│   ├── llm.py                # LLM client (OpenAI SDK wrapper)
│   ├── weather.py            # Met Office API client
│   ├── geocode.py            # Postcode → lat/lon (postcodes.io)
│   ├── prompts.py            # Prompt templates
│   └── models.py             # Pydantic request/response models
├── tests/
│   ├── test_recommendations.py
│   ├── test_weather.py
│   └── test_geocode.py
├── .env.example
├── pyproject.toml
├── SPEC.md
└── CLAUDE.md
```
