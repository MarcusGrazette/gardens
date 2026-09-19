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

### Phase 1 (MVP)
- **Weather**: Met Office DataHub API (free tier) — forecasts by postcode/coordinates
- **LLM knowledge**: Built-in knowledge of UK gardening seasons, common plants, pest lifecycles

### Phase 2 (post-MVP)
- **Soil**: BGS/Cranfield soil data by postcode
- **Plant database**: RHS or similar for species-specific care data
- **Pest calendars**: Seasonal pest/disease risk data

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

### Input assembly
1. Take user's garden profile (postcode at minimum)
2. Fetch current weather forecast for their location (Met Office API)
3. Determine current week/season
4. If postcode only: LLM infers likely soil type, suggests common local plants
5. Assemble a structured prompt with all available context

### Prompt structure
```
System: You are an expert UK gardener and horticulturist. Generate a prioritised
weekly action list for this gardener based on their specific situation.

Context:
- Location: {postcode}, {inferred_region}
- Current date: {date}, Week {week_number}
- Weather forecast (next 7 days): {forecast_summary}
- Garden: {orientation}, {shade_level}, {size}
- Soil type: {soil_type or "inferred from postcode: likely {type}"}
- Plants: {plant_list or "not specified — suggest common plants for this area"}
- Experience level: {level}

Generate:
1. Top 5-7 actions for this week, ordered by priority
2. Each action should be specific (not "water your plants" but "water tomatoes deeply
   2-3 times this week due to forecasted dry spell")
3. Flag any urgent items (frost warnings, pest alerts, time-sensitive planting windows)
4. For new/minimal profiles, include suggestions for what to plant this time of year
```

### Output format
Structured JSON response:
```json
{
  "week": "2025-W03",
  "actions": [
    {
      "priority": 1,
      "title": "Protect tender plants from forecast frost",
      "detail": "Temperatures dropping to -2°C Thursday night. Cover dahlias and move potted herbs indoors.",
      "category": "weather-response",
      "urgent": true
    }
  ],
  "plant_suggestions": [],
  "notes": "Optional general observations"
}
```

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
2. **Met Office API integration** — fetch 5-day forecast by postcode
3. **Postcode → coordinates lookup** — using postcodes.io (free, no auth)
4. **LLM orchestration** — assemble prompt, call OpenAI-compatible API, parse structured response
5. **Config** — environment-based switching between Ollama (dev) and cloud API (prod)

### What to defer:
- User accounts and database
- Web UI and templates
- Email sending
- Background job scheduling
- Soil/pest/plant database integrations

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
