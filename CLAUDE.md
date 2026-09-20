# This Week in the Garden

UK gardening recommendation engine for **ornamental home gardens** (beds, borders, pots, containers). FastAPI app that takes a postcode and returns personalised weekly gardening actions using weather data and LLM.

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

- `app/main.py` — FastAPI app, routes (HTML page, SSE streaming endpoint, JSON API), recommendation caching, extra plant extraction from action text
- `app/config.py` — Pydantic Settings from `.env` (uses `extra="ignore"` for extra env vars)
- `app/geocode.py` — Postcode validation + postcodes.io geocoding
- `app/weather.py` — Met Office DataHub daily forecast client
- `app/llm.py` — OpenAI SDK wrapper (configurable base_url). Returns `(parsed_json, raw_text)` tuple from `generate_json()`. Uses `json-repair` as fallback for malformed LLM output
- `app/prompts.py` — Prompt templates (ornamental focus, no vegetables) + season detection. Plant list prompt requests both common and latin names
- `app/cache.py` — JSON file cache for regional plant lists (`.cache/` dir, 10 plants per region/season). Enriches plants with Trefle API data (images, scientific names)
- `app/perenual.py` — Trefle API client for plant search. Best-match logic prefers exact common name matches
- `app/models.py` — Pydantic request/response models
- `app/static/` — Static assets (header image)
- `templates/index.html` — Web UI with SSE progress bar, plant thumbnails on action cards, latin name tooltips, collapsible debug panel. Uses "secret forest" colour palette

## Pipeline

`POST /recommendations` → validate postcode → geocode → weather → regional plants (cached + Trefle enriched) → LLM → extract extra plants from actions → structured JSON response

The web UI uses `GET /recommendations/stream?postcode=...` which streams SSE events for each pipeline step, including debug data (raw API responses, LLM prompts/responses).

## LLM provider

Any OpenAI-compatible API works. Set `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` in `.env`.

Currently using OpenRouter (`https://openrouter.ai/api/v1`) with `nvidia/nemotron-3-super-120b-a12b`. For local dev, Ollama works (`http://localhost:11434/v1`).

Note: `max_tokens=2048` is the default in `llm.py` (configurable per call) to avoid credit/token limit issues with providers like OpenRouter.

## Plant enrichment

Plants are enriched via the Trefle API (`TREFLE_API_KEY` in `.env`). The enrichment tries multiple search strategies in order: common name → latin name → cleaned latin (strips `×` and cultivar names) → genus only. Only results with images are kept. After recommendations are generated, action text is scanned for additional plant names (from a built-in common plants list) and enriched separately.

## Caching

- **Plant lists**: `.cache/plants_{region}_{season}.json` — regional plant lists with Trefle enrichment. Delete to regenerate after prompt changes.
- **Recommendations**: `.cache/recs_{postcode}_{week}.json` — full recommendation results including plant data. Keyed by postcode + ISO week, so the same postcode returns cached results within the same week. Delete to force regeneration.

## Design

UI uses the "secret forest" colour palette: olive green (#9BA657) accents, dark brown (#594433) text, warm sand (#F0E5C9) backgrounds, light grey (#F4F4F4) page background. Watercolour header image. Action cards show plant thumbnails from Trefle on the left edge; plant names in text have dotted-underline tooltips showing latin/scientific names on hover.
