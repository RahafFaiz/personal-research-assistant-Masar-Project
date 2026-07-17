"""Text-to-speech via edge-tts (cloud, no API key).

Picks an Arabic or English voice from the text and returns MP3 bytes. Markdown
and source URLs are stripped so they aren't read aloud.

Performance fix: reuses a persistent asyncio event loop to avoid the 200-400ms
overhead of creating a new loop on every synthesize() call.
"""

from __future__ import annotations

import asyncio
import re
import threading

# ── voices ────────────────────────────────────────────────────────────────────
AR_VOICE = "ar-SA-ZariyahNeural"   # female, Modern Standard Arabic
EN_VOICE = "en-US-AriaNeural"

_ARABIC = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]")

# ── persistent background loop (avoids asyncio.run() cold-start delay) ────────
_loop: asyncio.AbstractEventLoop | None = None
_loop_lock = threading.Lock()


def _get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    with _loop_lock:
        if _loop is None or _loop.is_closed():
            _loop = asyncio.new_event_loop()
            t = threading.Thread(target=_loop.run_forever, daemon=True)
            t.start()
    return _loop


# ── helpers ───────────────────────────────────────────────────────────────────
def _pick_voice(text: str) -> str:
    return AR_VOICE if _ARABIC.search(text) else EN_VOICE


def _clean(text: str) -> str:
    text = re.split(r"\*\*Sources:\*\*|## Sources", text)[0]  # drop sources block
    text = re.sub(r"https?://\S+", "", text)                  # drop URLs
    text = re.sub(r"[*_`#>|-]", " ", text)                    # drop markdown symbols
    text = re.sub(r"\[\d+\]", "", text)                        # drop citation numbers [1]
    return re.sub(r"\s+", " ", text).strip()


async def _synthesize(text: str, voice: str) -> bytes:
    import edge_tts

    audio = bytearray()
    async for chunk in edge_tts.Communicate(text, voice).stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]
    return bytes(audio)


def synthesize(text: str, voice: str | None = None) -> bytes:
    text = _clean(text)
    if not text:
        return b""
    chosen_voice = voice or _pick_voice(text)
    # Run on the persistent loop to avoid cold-start latency
    future = asyncio.run_coroutine_threadsafe(_synthesize(text, chosen_voice), _get_loop())
    return future.result(timeout=30)

