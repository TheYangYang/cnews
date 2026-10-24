"""One place that talks to Ollama, so every call shares the same model options."""

from __future__ import annotations

import httpx

from realtime_ingestion import config


def _options(temperature: float, num_predict: int) -> dict:
    # num_ctx must match across calls; a different value makes Ollama reload the model.
    return {"temperature": temperature, "num_predict": num_predict, "num_ctx": config.OLLAMA_NUM_CTX}


async def chat(
    client: httpx.AsyncClient,
    *,
    system: str,
    user: str,
    temperature: float,
    num_predict: int,
) -> str:
    response = await client.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={
            "model": config.OLLAMA_MODEL,
            "stream": False,
            "keep_alive": config.OLLAMA_KEEP_ALIVE,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": _options(temperature, num_predict),
        },
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


async def unload(client: httpx.AsyncClient) -> bool:
    """Ask Ollama to drop the model from VRAM. Returns False when Ollama is unreachable."""
    try:
        response = await client.post(
            f"{config.OLLAMA_URL}/api/generate",
            json={"model": config.OLLAMA_MODEL, "keep_alive": 0},
            timeout=30.0,
        )
        return response.status_code == 200
    except httpx.HTTPError:
        return False


async def installed_models(client: httpx.AsyncClient) -> list[str]:
    response = await client.get(f"{config.OLLAMA_URL}/api/tags")
    response.raise_for_status()
    return [item["name"] for item in response.json().get("models", [])]
