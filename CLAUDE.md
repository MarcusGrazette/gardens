# Garden Todo

UK gardening recommendation engine. FastAPI app that takes a postcode and returns personalised weekly gardening actions using weather data and LLM.

## Setup

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

## Test

```bash
curl -X POST http://localhost:8000/recommendations \
  -H "Content-Type: application/json" \
  -d '{"postcode": "SE15 4QN"}'
```

## Architecture

- `app/main.py` — FastAPI app, routes
- `app/config.py` — Pydantic Settings from `.env`
- `app/geocode.py` — Postcode validation + postcodes.io geocoding
- `app/weather.py` — Met Office DataHub daily forecast client
- `app/llm.py` — OpenAI SDK wrapper (configurable base_url for Ollama/cloud)
- `app/prompts.py` — Prompt templates + season detection
- `app/cache.py` — JSON file cache for regional plant lists
- `app/models.py` — Pydantic request/response models

## Pipeline

`POST /recommendations` → validate postcode → geocode → weather → regional plants (cached) → LLM → structured JSON response
