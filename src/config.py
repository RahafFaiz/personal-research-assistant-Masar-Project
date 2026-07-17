"""Application settings, loaded from environment / .env."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM — OpenRouter (used by every agent)
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="google/gemma-4-26b-a4b-it:free", alias="OPENROUTER_MODEL")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")

    # Embeddings
    embedding_model: str = Field(default="intfloat/multilingual-e5-base", alias="EMBEDDING_MODEL")

    # Voice (cloud STT via Groq; TTS via edge-tts needs no key)
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    stt_model: str = Field(default="whisper-large-v3-turbo", alias="STT_MODEL")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Knowledge base
    knowledge_dir: Path = PROJECT_ROOT / "knowledge"
    notes_dir: Path = PROJECT_ROOT / "knowledge" / "notes"
    vector_store_dir: Path = PROJECT_ROOT / "knowledge" / "vector_store"
    manifest_path: Path = PROJECT_ROOT / "knowledge" / "vector_store" / ".index_manifest.json"
    collection_name: str = "personal_knowledge"
    supported_extensions: tuple[str, ...] = (".pdf", ".md", ".txt")

    # Chunking / retrieval. chunk_size caps a section; sections stay whole when smaller.
    chunk_size: int = 750
    chunk_overlap: int = 100
    retriever_top_k: int = 4

    # Workspace (Filesystem MCP sandbox root)
    workspace_dir: Path = PROJECT_ROOT / "workspace"
    reports_dir: Path = PROJECT_ROOT / "workspace" / "reports"

    # Orchestration
    recursion_limit: int = 15
    error_budget: int = 3

    # Research (ddgs)
    research_max_results: int = 5
    research_max_retries: int = 3

    def ensure_dirs(self) -> None:
        for path in (self.knowledge_dir, self.notes_dir, self.vector_store_dir,
                     self.workspace_dir, self.reports_dir):
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
