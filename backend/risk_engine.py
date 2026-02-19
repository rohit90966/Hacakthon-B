"""Risk scoring engine for SAR cases.

Provides deterministic risk assessments based on transaction and behavioral factors
for auditability and consistency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RiskAssessment:
    risk_score: float
    risk_level: str
    contributing_factors: Dict[str, float]
    rationale: List[str]


RISK_LEVEL_THRESHOLDS = {
    "LOW": 0,
    "MEDIUM": 30,
    "HIGH": 60,
    "CRITICAL": 85,
}


def _normalize_score(score: float) -> float:
    return max(0.0, min(100.0, score))


def _derive_level(score: float) -> str:
    if score >= RISK_LEVEL_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    if score >= RISK_LEVEL_THRESHOLDS["HIGH"]:
        return "HIGH"
    if score >= RISK_LEVEL_THRESHOLDS["MEDIUM"]:
        return "MEDIUM"
    return "LOW"


def assess_risk(decision_data: dict, evidence_blocks: list) -> RiskAssessment:
    """Compute a deterministic risk score using weighted factors."""
    txns = decision_data.get("transactions", [])
    total_amount = decision_data.get("total_amount", 0.0)
    period_days = max(decision_data.get("period_days", 1.0), 1.0)
    counterparties = decision_data.get("unique_counterparties", 0)
    risk_rating = (decision_data.get("risk_rating") or "medium").lower()

    # Factor weights (sum ~100)
    weights = {
        "transaction_velocity": 22,
        "structuring_pattern": 20,
        "jurisdiction_risk": 18,
        "pep_involvement": 20,
        "historical_deviation": 20,
    }

    # Transaction velocity: volume per day
    velocity = len(txns) / period_days
    velocity_score = min(40.0, velocity * 4.0)  # cap to avoid runaway

    # Structuring: smaller frequent txns vs total
    structuring_score = 0.0
    if txns:
        small = [t for t in txns if t.get("amount", 0) < 10000]
        structuring_score = min(30.0, (len(small) / len(txns)) * 30.0)

    # Jurisdiction risk: count high-risk corridors flagged by rules
    high_risk_rules = {b["rule_id"] for b in evidence_blocks if "AML-021" in b.get("rule_id", "")}
    jurisdiction_score = 25.0 if high_risk_rules else 5.0

    # PEP involvement heuristic
    pep_tags = decision_data.get("customer", {}).get("pep_flags", [])
    pep_score = 30.0 if pep_tags else 5.0

    # Historical deviation: proxy using counterparties + total amount
    historical_score = 10.0 + min(30.0, (counterparties * 2.0) + (total_amount / 1_000_000))

    weighted_sum = (
        velocity_score * weights["transaction_velocity"]
        + structuring_score * weights["structuring_pattern"]
        + jurisdiction_score * weights["jurisdiction_risk"]
        + pep_score * weights["pep_involvement"]
        + historical_score * weights["historical_deviation"]
    ) / 100.0

    score = _normalize_score(weighted_sum)
    level = _derive_level(score)

    rationale = [
        f"Velocity factor: {velocity_score:.1f} based on {len(txns)} txns over {period_days:.1f} days",
        f"Structuring factor: {structuring_score:.1f} from sub-threshold patterns",
        f"Jurisdiction factor: {jurisdiction_score:.1f} (high-risk rule triggered: {bool(high_risk_rules)})",
        f"PEP factor: {pep_score:.1f} (PEP flags present: {bool(pep_tags)})",
        f"Historical deviation: {historical_score:.1f} (counterparties={counterparties}, total_amount={total_amount})",
    ]

    contributing = {
        "transaction_velocity": round(velocity_score, 2),
        "structuring_pattern": round(structuring_score, 2),
        "jurisdiction_risk": round(jurisdiction_score, 2),
        "pep_involvement": round(pep_score, 2),
        "historical_deviation": round(historical_score, 2),
    }

    return RiskAssessment(
        risk_score=score,
        risk_level=level,
        contributing_factors=contributing,
        rationale=rationale,
    )
