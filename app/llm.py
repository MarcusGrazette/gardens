import json

from openai import AsyncOpenAI

from app.config import settings


def _client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


async def generate(system_prompt: str, user_prompt: str) -> str:
    client = _client()
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=2048,
    )
    return response.choices[0].message.content


async def generate_json(system_prompt: str, user_prompt: str) -> tuple[dict | list, str]:
    """Returns (parsed_json, raw_response_text)."""
    raw = await generate(system_prompt, user_prompt)
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text), raw
