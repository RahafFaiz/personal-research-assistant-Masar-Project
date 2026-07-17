"""Render citations into a Markdown sources block."""

from __future__ import annotations

from ..schemas import Citation


def render_citations(citations: list[Citation]) -> str:
    if not citations:
        return ""
    lines, seen = ["", "**Sources:**"], set()
    for c in citations:
        if c.source not in seen:
            seen.add(c.source)
            lines.append(f"- {c.source}")
    return "\n".join(lines)
