from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

from .config import settings

try:
    # openai >= 1.0 style client
    from openai import AsyncOpenAI  # type: ignore
except Exception as e:  # pragma: no cover
    AsyncOpenAI = None  # type: ignore


@dataclass(frozen=True)
class OpenAIModels:
    text_model: str
    transcribe_model: str


_client: Optional["AsyncOpenAI"] = None
_models = OpenAIModels(
    text_model=settings.openai_model_text or "gpt-4o-mini",
    transcribe_model=settings.openai_model_transcribe or "whisper-1",
)


def _get_client() -> "AsyncOpenAI":
    global _client
    if _client is None:
        if AsyncOpenAI is None:
            raise RuntimeError("openai package is not installed. Add it to requirements.txt")
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment")
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def generate_text(
    prompt: str,
    *,
    user_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, int]]:
    """
    Call OpenAI Responses API to generate text.

    Returns: (text, usage)
    usage = {"input_tokens": int, "output_tokens": int, "total_tokens": int}
    """
    client = _get_client()

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Responses API via client.responses.create
    resp = await client.responses.create(
        model=_models.text_model,
        input=messages,
        user=user_id,
        **(extra or {}),
    )

    # Extract text
    text = ""
    if resp.output and len(resp.output) > 0:
        # New-style Responses API collections
        for item in resp.output:
            if getattr(item, "type", None) == "output_text":
                text += getattr(item, "text", "")
    elif hasattr(resp, "output_text"):
        text = getattr(resp, "output_text", "")

    usage = {
        "input_tokens": int(getattr(getattr(resp, "usage", None) or {}, "input_tokens", 0) or 0),
        "output_tokens": int(getattr(getattr(resp, "usage", None) or {}, "output_tokens", 0) or 0),
        "total_tokens": int(getattr(getattr(resp, "usage", None) or {}, "total_tokens", 0) or 0),
    }
    return text.strip(), usage


async def transcribe_audio(
    *,
    file_path: str,
    language: Optional[str] = None,
) -> Tuple[str, float]:
    """
    Transcribe audio using OpenAI transcription model.
    Returns: (text, duration_seconds_estimate)
    """
    client = _get_client()

    # Prefer whisper-1 if set; some newer models accept responses.create with input_audio,
    # but here use the stable audio.transcriptions.create endpoint.
    model = _models.transcribe_model

    # open file in binary mode
    import aiofiles

    async with aiofiles.open(file_path, "rb") as f:
        data = await f.read()

    # The SDK requires file-like; we can use bytes via content param (some versions require actual file IO)
    # To ensure compatibility, re-open with normal open in a thread
    def _sync_open() -> str:
        return file_path

    path = await asyncio.to_thread(_sync_open)

    with open(path, "rb") as fh:
        tr = await client.audio.transcriptions.create(
            model=model,
            file=fh,  # type: ignore
            language=language,
        )

    text = getattr(tr, "text", "") or ""
    # Duration is not returned; caller should pass known duration from Telegram metadata
    return text.strip(), 0.0
