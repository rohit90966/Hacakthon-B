import re

from .config import PROHIBITED_PHRASES

REQUIRED_FIELDS = [
    "subject_summary",
    "suspicious_activity_description",
    "transaction_timeline",
    "behavioral_indicators",
    "typology_mapping",
    "supporting_evidence",
    "reason_for_suspicion",
    "reporting_justification",
]


def validate_narrative(narrative, evidence_blocks):
    errors = []
    warnings = []

    for field in REQUIRED_FIELDS:
        if field not in narrative:
            errors.append(f"Missing field: {field}")
        elif isinstance(narrative[field], str) and not narrative[field].strip():
            errors.append(f"Empty field: {field}")

    # Evidence traceability
    rule_ids = {b["rule_id"] for b in evidence_blocks}
    supporting = set(narrative.get("supporting_evidence", []))
    missing = rule_ids - supporting
    if missing:
        errors.append(f"Missing evidence references: {', '.join(sorted(missing))}")

    # Prohibited phrase scan
    joined = " ".join(
        [
            str(narrative.get(k, ""))
            for k in REQUIRED_FIELDS
        ]
    ).lower()
    for phrase in PROHIBITED_PHRASES:
        if re.search(r"\b" + re.escape(phrase) + r"\b", joined):
            warnings.append(f"Prohibited phrase found: {phrase}")

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
