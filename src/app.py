"""Streamlit chat UI with an optional voice layer (speech in, speech out).

On startup it runs incremental knowledge ingestion, then serves a chat loop over
the compiled LangGraph supervisor. The Workspace Agent's overwrite interrupt is
surfaced as an in-UI confirm/cancel prompt. Voice is a thin layer: microphone ->
STT -> the same graph -> TTS, with the agents unchanged.

Run from the project root:  streamlit run src/app.py
"""

from __future__ import annotations

import asyncio
import hashlib
import sys
import uuid
from pathlib import Path

import streamlit as st
from langgraph.types import Command

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings          # noqa: E402
from src.graph import build_graph, initial_state, run_config  # noqa: E402
from src.knowledge import indexer        # noqa: E402
from src.voice import stt, tts           # noqa: E402

st.set_page_config(page_title="Personal Research Assistant", page_icon="🔎")


@st.cache_resource(show_spinner="Building the assistant…")
def get_app():
    return build_graph()


@st.cache_resource(show_spinner="Indexing your knowledge base…")
def run_startup_ingestion() -> str:
    settings.ensure_dirs()
    return indexer.sync_index().summary()


def _run(coro):
    return asyncio.run(coro)


def _handle_result(snapshot) -> None:
    tasks = getattr(snapshot, "tasks", [])
    if tasks and getattr(tasks[0], "interrupts", None):
        st.session_state.pending_interrupt = tasks[0].interrupts[0].value
    else:
        values = getattr(snapshot, "values", snapshot)
        if not isinstance(values, dict):
            values = {}
        reply = values.get("final_reply") or "(no reply produced)"
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.session_state.pending_interrupt = None


_NODE_LABELS: dict[str, str] = {
    "orchestrator":      "🧠 Thinking…",
    "knowledge_agent":   "📚 Searching your notes…",
    "research_agent":    "🌐 Searching the web…",
    "report_writer":     "📝 Writing report…",
    "workspace_agent":   "💾 Saving file…",
    "general_assistant": "💬 Composing reply…",
}


async def _stream_graph(prompt: str, thread_id: str) -> str:
    app = get_app()
    status_box = st.empty()
    stream_box = st.empty()          # token-level streaming box
    full_reply = ""

    async for event in app.astream(
        initial_state(prompt), run_config(thread_id), stream_mode=["updates", "messages"]
    ):
        kind, data = event                         # (stream_mode, payload)

        if kind == "updates":
            for node in data:
                status_box.status(_NODE_LABELS.get(node, f"⚙️ {node}…"), state="running")

        elif kind == "messages":
            # data is (AIMessageChunk, metadata)
            chunk, meta = data
            node = meta.get("langgraph_node", "")
            if node == "general_assistant" and hasattr(chunk, "content") and chunk.content:
                if chunk.__class__.__name__ == "AIMessageChunk":
                    full_reply += chunk.content
                else:
                    # It's a full AIMessage (either from LLM callback or state update)
                    # Overwrite instead of appending to avoid duplication
                    full_reply = chunk.content
                stream_box.markdown(full_reply + " ▮")   # live cursor effect

    status_box.empty()
    stream_box.empty()          # clear the live box; the final reply is appended once by _submit
    return full_reply


def _quota_error_msg(e: Exception) -> str | None:
    s = str(e)
    if "429" in s or "rate" in s.lower():
        return ("⏳ The free model is briefly overloaded upstream. Please try your "
                 "request again in a few seconds — this isn't a quota problem.")
    if "401" in s or "API_KEY_INVALID" in s or "invalid" in s.lower() and "key" in s.lower():
        return "⚠️ Invalid API key. Check OPENROUTER_API_KEY in .env."
    return None


def _submit(prompt: str) -> None:
    st.session_state.messages.append({"role": "user", "content": prompt})
    thread_id = str(uuid.uuid4())
    st.session_state.thread_id = thread_id
    try:
        streamed = _run(_stream_graph(prompt, thread_id))
        snapshot = _run(get_app().aget_state(run_config(thread_id)))
        tasks = getattr(snapshot, "tasks", [])
        if tasks and getattr(tasks[0], "interrupts", None):
            st.session_state.pending_interrupt = tasks[0].interrupts[0].value
        else:
            values = getattr(snapshot, "values", {}) or {}
            reply = streamed or values.get("final_reply") or "(no reply produced)"
            st.session_state.messages.append({"role": "assistant", "content": reply})
    except Exception as e:
        friendly = _quota_error_msg(e)
        msg = friendly if friendly else f"⚠️ Something went wrong: {e}"
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.session_state.pending_interrupt = None


def _resume(decision: bool) -> None:
    try:
        _run(get_app().ainvoke(Command(resume=decision), run_config(st.session_state.thread_id)))
        snapshot = _run(get_app().aget_state(run_config(st.session_state.thread_id)))
        _handle_result(snapshot)
    except Exception as e:
        st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Something went wrong: {e}"})
        st.session_state.pending_interrupt = None


def _speak_latest_reply() -> None:
    """Play the latest assistant reply once, if voice output is enabled."""
    if not st.session_state.get("voice_output"):
        return
    messages = st.session_state.messages
    idx = len(messages) - 1
    if idx < 0 or messages[idx]["role"] != "assistant" or st.session_state.spoken_index == idx:
        return
    try:
        audio = tts.synthesize(messages[idx]["content"])
        if audio:
            st.audio(audio, format="audio/mp3", autoplay=True)
            st.session_state.spoken_index = idx
    except Exception:
        pass


ingest_summary = run_startup_ingestion()

st.session_state.setdefault("messages", [])
st.session_state.setdefault("pending_interrupt", None)
st.session_state.setdefault("thread_id", None)
st.session_state.setdefault("voice_output", False)
st.session_state.setdefault("spoken_index", -1)
st.session_state.setdefault("last_audio_id", None)

with st.sidebar:
    st.header("🔎 Personal Research Assistant")
    st.caption("Multi-agent · LangGraph · Gemma (OpenRouter)")
    st.markdown(f"**Knowledge synced:** `{ingest_summary}`")
    st.session_state.voice_output = st.toggle("🔊 Speak replies", value=st.session_state.voice_output)
    st.markdown(
        "**Try:**\n"
        "- What is in my note about AI voice agents?\n"
        "- Look up the Model Context Protocol and summarize it.\n"
        "- Research vector databases and save a report to `reports/vdb.md`."
    )

st.title("Personal Research Assistant")

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

_speak_latest_reply()

# Overwrite confirmation (Human-in-the-Loop).
if st.session_state.pending_interrupt:
    info = st.session_state.pending_interrupt
    with st.chat_message("assistant"):
        st.warning(f"⚠️ The file `{info.get('path')}` already exists. Overwrite it?")
        c1, c2 = st.columns(2)
        if c1.button("✅ Overwrite"):
            _resume(True)
            st.rerun()
        if c2.button("❌ Cancel"):
            _resume(False)
            st.rerun()

# CSS Hack to float the audio input widget above the chat input
st.markdown(
    """
    <style>
    div[data-testid="stAudioInput"] {
        position: fixed;
        bottom: 25px; /* Aligned horizontally with the chat input */
        right: 30px;  /* Pushed to the right edge */
        z-index: 999999;
        width: 260px; /* Compact width */
        background: linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%); /* Premium gradient color */
        border: 2px solid #ffffff;
        border-radius: 30px; /* Very rounded edges */
        padding: 5px 10px;
        box-shadow: 0px 8px 16px rgba(0, 0, 0, 0.15);
        transition: all 0.3s ease;
    }
    div[data-testid="stAudioInput"]:hover {
        transform: translateY(-2px);
        box-shadow: 0px 12px 20px rgba(0, 0, 0, 0.2);
    }
    /* Hide the label */
    div[data-testid="stAudioInput"] label {
        display: none !important;
    }
    /* Make room in the chat input so they don't overlap */
    div[data-testid="stChatInputContainer"] {
        padding-right: 270px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Voice input.
audio = st.audio_input("🎤 Speak your request")
if audio is not None:
    data = audio.getvalue()
    audio_id = hashlib.md5(data).hexdigest()
    if audio_id != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_id
        try:
            # Guess language from last user message to avoid Whisper hallucinating
            last_user_msgs = [m["content"] for m in st.session_state.messages if m["role"] == "user"]
            lang_hint = stt._guess_language(last_user_msgs[-1] if last_user_msgs else None)
            text = stt.transcribe(data, language_hint=lang_hint)
        except Exception as e:
            text = ""
            st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Voice input failed: {e}"})
        if text:
            # Draw the user's message immediately before blocking on graph execution
            with st.chat_message("user"):
                st.markdown(text)
            _submit(text)
        st.rerun()

# Text input.
if prompt := st.chat_input("Ask from your notes, research the web, or save a report…"):
    # Show user message IMMEDIATELY (before LLM starts) — same pattern as voice input
    with st.chat_message("user"):
        st.markdown(prompt)
    _submit(prompt)
    st.rerun()
