"""Speech-to-text via Groq Whisper (cloud). Auto-detects Arabic/English."""

from __future__ import annotations

from ..config import settings

# Whisper language codes to pass explicitly
_AR = "ar"
_EN = "en"


def _guess_language(text_hint: str | None) -> str | None:
    """Return a Whisper language code if we can guess from prior context."""
    if text_hint:
        import re
        if re.search(r"[\u0600-\u06FF]", text_hint):
            return _AR
    return None  # let Whisper auto-detect for English/other


def transcribe(audio_bytes: bytes, filename: str = "audio.wav", language_hint: str | None = None) -> str:
    from groq import Groq

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to .env to use voice input.")

    client = Groq(api_key=settings.groq_api_key)

    # Build kwargs — only pass language when we have a strong hint to avoid
    # Whisper hallucinating French / other languages for short Arabic clips.
    kwargs: dict = dict(
        file=(filename, audio_bytes),
        model=settings.stt_model,
        response_format="verbose_json",   # gives us detected_language for logging
    )
    if language_hint:
        kwargs["language"] = language_hint

    result = client.audio.transcriptions.create(**kwargs)
    return (result.text or "").strip()
