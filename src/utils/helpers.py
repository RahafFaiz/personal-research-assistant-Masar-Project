"""Content hashing and prompt loading."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import PROJECT_ROOT

_PROMPTS_DIR = PROJECT_ROOT / "src" / "prompts"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
