"""Explainability layer linking statements to evidence and rules."""
from __future__ import annotations

from typing import Dict, List


def build_explainability_trace(formatted_narrative: Dict[str, object], evidence_blocks: List[dict]) -> List[dict]:
    """Link each narrative section to supporting evidence and rule metadata."""
    evidence_by_rule = {b.get("rule_id"): b for b in evidence_blocks}
    trace: List[dict] = []

    for section, text in formatted_narrative.get("sections", {}).items():
        for rule_id, evidence in evidence_by_rule.items():
            confidence = evidence.get("confidence_score", 0.0)
            trace.append({
                "section": section,
                "statement": text[:240],
                "supporting_evidence_id": rule_id,
                "rule_triggered": evidence.get("rule_name"),
                "confidence_weight": confidence,
                "evidence_details": evidence.get("evidence", []),
            })
    return trace
