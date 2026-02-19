"""Regulatory validation v2 with expanded checks."""
from __future__ import annotations

from typing import Dict, List

REQUIRED_SECTIONS = [
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


def validate_v2(formatted_narrative: Dict[str, object], explainability_trace: List[dict]) -> Dict[str, object]:
    errors: List[str] = []
    warnings: List[str] = []

    sections = formatted_narrative.get("sections", {})
    for sec in REQUIRED_SECTIONS:
        if sec not in sections:
            errors.append(f"Missing section: {sec}")
        elif not str(sections.get(sec, "")).strip():
            errors.append(f"Empty section: {sec}")

    citations = formatted_narrative.get("evidence_citations", [])
    if not citations:
        errors.append("No evidence citations provided")

    # Each trace entry should have evidence mapping
    missing_evidence = [t for t in explainability_trace if not t.get("supporting_evidence_id")]
    if missing_evidence:
        warnings.append("Some statements lack evidence ids")

    # Narrative clarity: simple length heuristic
    for sec, text in sections.items():
        text_str = str(text)
        if len(text_str) < 40:
            warnings.append(f"Narrative clarity low in section: {sec}")
        if len(text_str) > 0 and any(char.isdigit() for char in text_str) and len(text_str) > 6:
            # crude PII detection heuristic
            if any(token.isdigit() and len(token) >= 6 for token in text_str.split()):
                warnings.append(f"Possible unmasked PII detected in {sec}")

    # Minimum explanation coverage: ensure each section has at least one trace entry
    for sec in REQUIRED_SECTIONS:
        if not any(t.get("section") == sec for t in explainability_trace):
            warnings.append(f"No explainability coverage for {sec}")

    passed = len(errors) == 0
    return {
        "passed": passed,
        "errors": errors,
        "warnings": warnings,
        "summary": "Validation passed" if passed else "Validation requires attention",
    }
