"""Incremental ingestion: reconcile knowledge/ with the vector store.

Compares each file's content hash against a manifest and re-indexes only the
changes (new / modified / deleted). The full store is never rebuilt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from ..config import settings
from ..utils.helpers import file_sha256
from ..utils.logger import get_logger
from . import vector_store
from .chunker import chunk_documents
from .loader import load_file

logger = get_logger(__name__)


@dataclass
class SyncReport:
    new: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (f"new={len(self.new)} modified={len(self.modified)} "
                f"deleted={len(self.deleted)} unchanged={len(self.unchanged)}")


def _load_manifest() -> dict[str, dict]:
    path = settings.manifest_path
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("Manifest unreadable; treating as empty.")
        return {}


def _save_manifest(manifest: dict[str, dict]) -> None:
    settings.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    settings.manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def _scan() -> dict[str, Path]:
    root = settings.knowledge_dir.resolve()
    vector_root = settings.vector_store_dir.resolve()
    found: dict[str, Path] = {}
    for path in root.rglob("*"):
        if (path.is_file() and vector_root not in path.parents
                and not path.name.startswith(".")
                and path.suffix.lower() in settings.supported_extensions):
            found[path.relative_to(root).as_posix()] = path
    return found


def _index(source: str, path: Path) -> int:
    return vector_store.add_source_chunks(source, chunk_documents(load_file(path)))


def sync_index() -> SyncReport:
    manifest = _load_manifest()
    current = _scan()
    report = SyncReport()

    for source in sorted(set(manifest) - set(current)):
        vector_store.delete_source(source)
        manifest.pop(source, None)
        report.deleted.append(source)

    for source in sorted(current):
        digest = file_sha256(current[source])
        prior = manifest.get(source)
        if prior is None:
            manifest[source] = {"hash": digest, "chunks": _index(source, current[source])}
            report.new.append(source)
        elif prior.get("hash") != digest:
            vector_store.delete_source(source)
            manifest[source] = {"hash": digest, "chunks": _index(source, current[source])}
            report.modified.append(source)
        else:
            report.unchanged.append(source)

    _save_manifest(manifest)
    logger.info("Knowledge sync complete: %s", report.summary())
    return report
