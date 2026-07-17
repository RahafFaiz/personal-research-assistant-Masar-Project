# Personal Research Assistant

A local, privacy-first multi-agent research assistant built on **LangGraph**.
All document processing happens on your machine; only the final answer generation
sends a small context window to the OpenRouter API.

---

## What It Does

The assistant handles three categories of request:

| Request type | What happens |
|---|---|
| Question about your notes/documents | Knowledge Agent runs semantic retrieval over a local Chroma index and returns an answer with citations |
| Web research question | Research Agent searches the web via DuckDuckGo and summarises results with source URLs |
| "Research X and save a report" | Research Agent + Report Writer compose a Markdown report; Workspace Agent writes it to `workspace/reports/` |

Every request can be typed or spoken: use the microphone for input and, optionally, hear the reply read aloud.

---

## Architecture

```
User
 └── Streamlit UI  (src/app.py)
      └── Orchestrator  (src/agents/orchestrator.py)
           ├── General Assistant    (src/agents/general_assistant.py)
           ├── Knowledge Agent      (src/agents/knowledge_agent.py)
           ├── Research Agent       (src/agents/research_agent.py)
           ├── Report Writer        (src/agents/report_writer.py)
           └── Workspace Agent      (src/agents/workspace_agent.py)
```

The **Orchestrator** reads each user turn and emits a structured routing
decision (`NextAction`). It dispatches to exactly one specialist per turn and
loops until the task is complete or the recursion limit is reached.

State is shared across agents via a typed `GraphState` (LangGraph
`StateGraph`). The Workspace Agent is the only agent that can write files,
and it is sandboxed to the `workspace/` directory.

---

## Knowledge Pipeline (RAG)

All document processing is fully local and runs on first use or when files change.

```
knowledge/
  *.pdf / *.md / *.txt
        │
        ▼
  loader.py          Reads files; PyPDF for PDFs, plain text for .md / .txt.
        │             Attaches source + page metadata to every Document.
        ▼
  chunker.py         RecursiveCharacterTextSplitter
                       chunk_size   = 750 characters  (cap; most entries stay whole)
                       chunk_overlap= 100 characters  (bridges split sections)
                     Each chunk gets a stable per-source index for incremental updates.
        │
        ▼
  embeddings.py      intfloat/multilingual-e5-base  (≈ 1 GB, downloaded once,
                     runs fully on CPU, supports Arabic + English).
        │
        ▼
  vector_store.py    ChromaDB persistent store at knowledge/vector_store/
        │
        ▼
  indexer.py         sync_index() — called on every startup.
                     Compares SHA-256 file hashes against .index_manifest.json.
                     Only processes new / modified / deleted files; unchanged files
                     are skipped in < 1 second regardless of collection size.
        │
        ▼
  retriever.py       retrieve(query, k=4)
                     Converts the question to an embedding and returns the
                     top-4 most semantically similar chunks (Cosine similarity).
```

At answer time:

```
User question
      │
      ▼
  retriever.py       top-4 chunks with source metadata
      │
      ▼
  knowledge_agent.py _build_context() — labels each chunk with its source
                     Loads knowledge_agent.md prompt, injects {context} + {question}
                     Calls the LLM (Gemma via OpenRouter, temperature=0.2)
      │
      ▼
  LLM                Reads only the retrieved chunks. Strict grounding rules:
                       • Answer only from the provided context.
                       • If the answer is absent → reply exactly:
                         "I don't know based on your notes."
                       • Never guess, infer beyond the text, or fabricate.
      │
      ▼
  AgentResult        content (answer) + citations (source name + snippet per chunk)
```

---

## Grounding and Refusal

The Knowledge Agent is **fully grounded**: the model is instructed to use only the
retrieved context and to reply with a fixed refusal string when the answer is
not present. The refusal string is detected in code; citations are suppressed
when the agent refuses, so the user never sees misleading source references.

The prompt also includes a **prompt-injection defence**: context documents are
treated as untrusted data, not instructions, so a malicious PDF cannot hijack
the agent's behaviour.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemma via OpenRouter `google/gemma-4-26b-a4b-it:free` |
| Embeddings | `intfloat/multilingual-e5-base` via `sentence-transformers` (local) |
| Vector store | ChromaDB (persistent, local) |
| Orchestration | LangGraph `StateGraph` |
| Web search | `ddgs` (DuckDuckGo, no API key required) |
| File access | Filesystem MCP server (`@modelcontextprotocol/server-filesystem`) |
| UI | Streamlit |
| Voice input (STT) | Groq Whisper `whisper-large-v3-turbo` (cloud) |
| Voice output (TTS) | `edge-tts` — Microsoft voices, no key |
| Config | Pydantic-Settings (`.env` override for every setting) |

---

## Project Layout

```
personal-research-assistant/
├── knowledge/
│   ├── *.pdf / notes/*.md        your personal documents
│   └── vector_store/             auto-generated Chroma index (do not edit)
├── workspace/
│   └── reports/                  saved research reports (MCP sandbox root)
├── config/
│   └── mcp_servers.json          Filesystem MCP server configuration
├── src/
│   ├── app.py                    Streamlit chat UI
│   ├── graph.py                  LangGraph graph assembly
│   ├── state.py                  shared GraphState definition
│   ├── schemas.py                Pydantic schemas (AgentResult, Citation, …)
│   ├── config.py                 all tuneable settings (paths, model names, sizes)
│   ├── llm.py                    LLM factory (OpenRouter — single place to swap the provider)
│   ├── mcp_clients.py            MCP client helper for the Workspace Agent
│   ├── agents/
│   │   ├── orchestrator.py       supervisor — reads intent, emits NextAction
│   │   ├── general_assistant.py  conversational reply (no tools)
│   │   ├── knowledge_agent.py    RAG — retrieval + grounded generation + citations
│   │   ├── research_agent.py     DuckDuckGo search + summarisation
│   │   ├── report_writer.py      formats research into a structured Markdown report
│   │   └── workspace_agent.py    writes/reads files via MCP (sandboxed to workspace/)
│   ├── knowledge/
│   │   ├── loader.py             file reader (PDF + plain text)
│   │   ├── chunker.py            RecursiveCharacterTextSplitter wrapper
│   │   ├── embeddings.py         HuggingFace e5 embedding loader (cached locally)
│   │   ├── vector_store.py       ChromaDB wrapper (add / delete / search)
│   │   ├── retriever.py          similarity search + Citation builder
│   │   └── indexer.py            incremental sync (hash-based, startup hook)
│   ├── prompts/
│   │   ├── orchestrator.md       routing rules + NextAction schema
│   │   ├── knowledge_agent.md    grounding rules + refusal instruction
│   │   ├── general_assistant.md  conversational tone guidelines
│   │   ├── research_agent.md     search + summarisation instructions
│   │   └── report_writer.md      report structure template
│   ├── utils/
│   │   ├── logging.py            structured logger factory
│   │   ├── hashing.py            SHA-256 file fingerprinting for the indexer
│   │   └── citations.py          render Citation lists as Markdown source blocks
│   └── voice/
│       ├── stt.py               speech-to-text via Groq Whisper (cloud)
│       └── tts.py               text-to-speech via edge-tts (no key)
├── requirements.txt
├── .env.example                  template — copy to .env and add OPENROUTER_API_KEY
├── test_system.py                manual smoke test (indexer → retriever → agent)
└── README.md
```

---

## Setup

Requirements: **Python 3.10+** and **Node.js** (for the Filesystem MCP server).

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Set your API keys
cp .env.example .env
# open .env and set OPENROUTER_API_KEY=<your key>
# optional: set GROQ_API_KEY=<your key> to enable voice input

# 3. Add your documents
# Drop .pdf, .md, or .txt files into knowledge/  (or knowledge/notes/)

# 4. Run the assistant
streamlit run src/app.py
```

On first run the e5 embedding model (~1 GB) downloads automatically and is
cached locally. The knowledge index builds on startup and updates only changed
files on subsequent runs.

Text and voice both work out of the box. Spoken replies (TTS) need no key;
voice input (STT) needs `GROQ_API_KEY`. In the app, toggle "🔊 Speak replies"
in the sidebar and use the 🎤 microphone to speak a request.

---

## Configuration

All settings live in `src/config.py` and can be overridden via `.env`:

| Setting | Default | Description |
|---|---|---|
| `OPENROUTER_MODEL` | `google/gemma-4-26b-a4b-it:free` | model used by all agents |
| `LLM_TEMPERATURE` | `0.2` | Low temperature for factual, grounded answers |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-base` | Local embedding model |
| `chunk_size` | `750` | Max characters per chunk |
| `chunk_overlap` | `100` | Character overlap between adjacent chunks |
| `retriever_top_k` | `4` | Chunks retrieved per query |
| `research_max_results` | `5` | DuckDuckGo results per search |

---

## Smoke Test

```bash
python test_system.py
```

Runs indexer sync → retrieval → Knowledge Agent in sequence and prints the
results to the terminal. Use this to verify the pipeline after adding new
documents or changing settings.
