"""Report Writer — formats research findings into a Markdown report.

No tools: it only reads findings and produces report text, and treats the
findings as data (never executes embedded instructions).
"""

from __future__ import annotations

from ..llm import get_llm
from ..schemas import AgentResult, Citation, ResponseStatus
from ..utils.helpers import load_prompt
from ..utils.logger import get_logger

logger = get_logger(__name__)


def write_report(topic: str, findings: list[str], citations: list[Citation]) -> AgentResult:
    findings_text = "\n\n".join(findings).strip() or "(no findings provided)"
    sources_text = "\n".join(f"- {c.source}" for c in citations) or "(no sources)"
    prompt = load_prompt("report_writer").format(
        topic=topic, findings=findings_text, sources=sources_text
    )
    try:
        report = (get_llm().invoke(prompt).content or "").strip()
    except Exception as e:
        logger.error("Report Writer LLM call failed: %s", e)
        return AgentResult(status=ResponseStatus.ERROR, error=str(e))

    return AgentResult(content=report, citations=citations)
