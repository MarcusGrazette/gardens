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
    )
    return response.choices[0].message.content


async def generate_json(system_prompt: str, user_prompt: str) -> dict | list:
    raw = await generate(system_prompt, user_prompt)
    # Try to extract JSON from the response (LLMs often wrap in markdown code blocks)
    text = raw.strip()
    if text.startswith("```"):
        # Remove code block markers
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)
