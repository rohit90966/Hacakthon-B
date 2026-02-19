"""SAR narrative formatter for regulatory-grade output.

Converts structured LLM output and rule evidence into human-readable sections.
"""
from __future__ import annotations

from typing import Dict, List

SECTION_ORDER = [
    "Subject Information",
    "Account Details",
    "Alert Summary",
    "Transaction Pattern Analysis",
    "Suspicious Behaviour Indicators",
    "Supporting Evidence",
    "Regulatory Justification",
    "Investigator Assessment",
    "Conclusion & Recommendation",
]


def _as_paragraph(text: str) -> str:
    text = (text or "").strip()
    return text.replace("\n", " ") if text else "Not provided." 


def format_sar_narrative(
    llm_sections: Dict[str, str],
    risk_score: float,
    risk_level: str,
    confidence_level: float,
    evidence_citations: List[str],
    contributing_factors: Dict[str, float] | None = None,
) -> Dict[str, object]:
    """Produce ordered SAR sections with metadata for downstream export."""
    sections = {}
    for section in SECTION_ORDER:
        key = section.lower().replace(" ", "_").replace("&", "and")
        sections[section] = _as_paragraph(llm_sections.get(key) or llm_sections.get(section) or "")

    return {
        "sections": sections,
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "confidence_level": round(confidence_level, 2),
        "evidence_citations": evidence_citations,
        "contributing_factors": contributing_factors or {},
    }


def narrative_as_text(formatted: Dict[str, object]) -> str:
    """Render formatted SAR narrative to a plain-text multi-section document."""
    parts: List[str] = []
    for section in SECTION_ORDER:
        body = formatted.get("sections", {}).get(section, "")
        parts.append(f"{section}\n{body}\n")
    meta = f"Risk Level: {formatted.get('risk_level')} | Risk Score: {formatted.get('risk_score')} | Confidence: {formatted.get('confidence_level')}"
    parts.append(meta)
    return "\n".join(parts)
