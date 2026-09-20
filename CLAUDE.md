# Garden Todo

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

- `app/main.py` — FastAPI app, routes (HTML page, SSE streaming endpoint, JSON API)
- `app/config.py` — Pydantic Settings from `.env` (uses `extra="ignore"` for extra env vars)
- `app/geocode.py` — Postcode validation + postcodes.io geocoding
- `app/weather.py` — Met Office DataHub daily forecast client
- `app/llm.py` — OpenAI SDK wrapper (configurable base_url). Returns `(parsed_json, raw_text)` tuple from `generate_json()`
- `app/prompts.py` — Prompt templates (ornamental focus, no vegetables) + season detection
- `app/cache.py` — JSON file cache for regional plant lists (`.cache/` dir, 10 plants per region/season)
- `app/models.py` — Pydantic request/response models
- `templates/index.html` — Web UI with SSE progress bar and collapsible debug panel

## Pipeline

`POST /recommendations` → validate postcode → geocode → weather → regional plants (cached) → LLM → structured JSON response

The web UI uses `GET /recommendations/stream?postcode=...` which streams SSE events for each pipeline step, including debug data (raw API responses, LLM prompts/responses).

## LLM provider

Any OpenAI-compatible API works. Set `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY` in `.env`.

Currently using OpenRouter (`https://openrouter.ai/api/v1`) with `nvidia/nemotron-3-super-120b-a12b`. For local dev, Ollama works (`http://localhost:11434/v1`).

Note: `max_tokens=2048` is set in `llm.py` to avoid credit/token limit issues with providers like OpenRouter.

## Plant cache

Regional plant lists are cached as JSON files in `.cache/` keyed by `{region}_{season}`. Delete `.cache/` to regenerate after prompt changes.
