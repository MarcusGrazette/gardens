# This Week in the Garden

UK gardening recommendation engine for **ornamental home gardens** (beds, borders, pots, containers). FastAPI app that generates personalised weekly gardening actions using weather data and LLM. Server-side user profile stores postcode, location, and task state.

## Setup

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

Then open http://localhost:8000 for the web UI.

## Test (API)

```bash
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"postcode": "SE15 4QN"}'
```

## Architecture

- `app/main.py` — FastAPI app, routes (onboarding, SSE streaming, task state API, JSON API), recommendation caching, extra plant extraction from action text
- `app/user.py` — Server-side user store (`.data/user.json`). Manages profile (postcode, location, garden prefs), per-week task state (done/deferred/skipped), and rolling completion history
- `app/config.py` — Pydantic Settings from `.env` (uses `extra="ignore"` for extra env vars)
- `app/geocode.py` — Postcode validation + postcodes.io geocoding
- `app/weather.py` — Met Office DataHub daily forecast client
- `app/llm.py` — OpenAI SDK wrapper (configurable base_url). Returns `(parsed_json, raw_text)` tuple from `generate_json()`. Uses `json-repair` as fallback for malformed LLM output
- `app/prompts.py` — Prompt templates (ornamental focus, no vegetables) + season detection. LLM returns `summary`, `why_now`, `minutes`, and structured `plant_suggestions`
- `app/cache.py` — JSON file cache for regional plant lists (`.cache/` dir, 10 plants per region/season). Enriches plants with Trefle API data (images, scientific names)
- `app/perenual.py` — Trefle API client for plant search. Best-match logic prefers exact common name matches
- `app/models.py` — Pydantic request/response models (`Action` has `why_now`, `minutes`; `PlantSuggestion` has `name`, `latin`, `note`)
- `app/static/` — Static assets (header image)
- `templates/index.html` — Web UI: onboarding (if no user profile) or auto-loading results with SSE progress, forecast strip, completion ring, lead task with "Why now" panel, task tracking (done/snooze/skip/undo), inferences, plant suggestions. Debug panel gated behind `?debug=1`

## User Profile & Onboarding

Single-user profile stored as `.data/user.json`. No accounts or auth — if the file exists, the user is onboarded.

- **First visit** (`GET /`): no profile → shows onboarding screen (postcode input + "Get started")
- **`POST /onboard`**: validates postcode, geocodes via postcodes.io, creates `.data/user.json` with postcode + location, redirects to `/`
- **Subsequent visits** (`GET /`): profile exists → auto-streams recommendations from stored postcode (no form)
- **Reset**: delete `.data/user.json` to return to onboarding

Task state (done/deferred/skipped per action per week) and completion history are persisted in the same file via `POST /api/task-state`.

## Pipeline

`POST /recommendations` → validate postcode → geocode → weather → regional plants (cached + Trefle enriched) → LLM → extract extra plants from actions → structured JSON response

The web UI uses `GET /recommendations/stream` (reads postcode from user profile) which streams SSE events for each pipeline step, including debug data (raw API responses, LLM prompts/responses). The `postcode` query param is still accepted as an override.

## LLM provider

Any OpenAI-compatible API works. Set `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` in `.env`.

Currently using OpenRouter (`https://openrouter.ai/api/v1`) with `nvidia/nemotron-3-super-120b-a12b`. For local dev, Ollama works (`http://localhost:11434/v1`).

Note: `max_tokens=2048` is the default in `llm.py` (configurable per call) to avoid credit/token limit issues with providers like OpenRouter.

## Plant enrichment

Plants are enriched via the Trefle API (`TREFLE_API_KEY` in `.env`). The enrichment tries multiple search strategies in order: common name → latin name → cleaned latin (strips `×` and cultivar names) → genus only. Only results with images are kept. After recommendations are generated, action text is scanned for additional plant names (from a built-in common plants list) and enriched separately.

## Caching & Data

- **User profile**: `.data/user.json` — postcode, location, garden prefs, per-week task state, completion history. Delete to reset onboarding.
- **Plant lists**: `.cache/plants_{region}_{season}.json` — regional plant lists with Trefle enrichment. Delete to regenerate after prompt changes.
- **Recommendations**: `.cache/recs_{postcode}_{week}.json` — full recommendation results including plant data. Keyed by postcode + ISO week, so the same postcode returns cached results within the same week. Delete to force regeneration.

## Design

Mobile-first single column (max 420px). Three font families: Newsreader (serif headlines), Inter (body), IBM Plex Mono (labels). Design tokens on `:root`: `--paper` #FAF8F3, `--desk` #EDE9E0, `--sage` #7D8545, `--ink` #33281E, `--cream` #F0E5C9, etc. Watercolour masthead with scrim gradient. Card radius 28px (shell), 18px (panels), 12px (inputs). No emoji — only `✓` and `·` as ornament. Dark `--ink` panel for inferences. Debug panel visible only with `?debug=1`.
