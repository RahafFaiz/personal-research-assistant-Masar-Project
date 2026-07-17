# AI Voice Agent

An **AI voice agent** is a conversational system that lets a user speak to an
application and hear a spoken reply. It combines speech recognition, language
understanding, and speech synthesis so the interaction feels like a natural
phone or in-person conversation instead of typing.

## Core Pipeline

A voice agent is usually built from three stages chained together:

1. **Speech-to-Text (STT / ASR)** — converts the user's spoken audio into text.
   Common engines: Whisper, Google Speech-to-Text, Deepgram.
2. **Reasoning (LLM)** — a language model interprets the text, keeps track of
   the conversation, calls tools or APIs when needed, and decides what to say.
3. **Text-to-Speech (TTS)** — turns the model's text reply back into natural
   audio. Common engines: ElevenLabs, Amazon Polly, Google TTS.

Audio in → STT → LLM → TTS → Audio out.

## Key Components

- **Turn detection / VAD** — voice activity detection decides when the user has
  stopped speaking so the agent can respond at the right moment.
- **Barge-in** — lets the user interrupt the agent while it is talking.
- **Latency budget** — the whole loop should feel real-time (ideally under ~1
  second) or the conversation feels slow and unnatural.
- **Context memory** — the agent remembers earlier turns in the call.

## Common Use Cases

- Customer support and call-center automation.
- Appointment booking and reminders (for example, healthcare clinics).
- Medication refill and follow-up calls.
- Voice assistants for hands-free tasks.

## Main Challenges

- **Latency** — keeping the STT → LLM → TTS loop fast enough to feel live.
- **Interruptions** — handling barge-in and overlapping speech gracefully.
- **Accuracy in noise** — recognizing speech correctly with background noise or
  accents.
- **Grounding** — making sure the agent answers from real data instead of
  hallucinating, especially for bookings and sensitive tasks.

## Relation to This Project

The Personal Research Assistant is text-based, but a voice layer could be added
on top: speech-to-text for the user's request and text-to-speech for the
General Assistant's final reply, without changing the underlying agents.
