import datetime as dt

RULE_VERSION = "v0.1"


def _days_between(start_ts, end_ts):
    return (end_ts - start_ts).total_seconds() / 86400.0


def evaluate_rules(decision_data):
    txns = decision_data.get("transactions", [])
    total_amount = decision_data.get("total_amount", 0.0)
    unique_counterparties = decision_data.get("unique_counterparties", 0)
    period_days = decision_data.get("period_days", 0.0)

    evidence_blocks = []

    # Rule AML-001: Structuring / sub-threshold aggregation
    small_txns = [t for t in txns if t.get("amount", 0) < 100000]
    if len(small_txns) >= 20 and period_days <= 10:
        evidence_blocks.append({
            "rule_id": "AML-001",
            "rule_name": "Structuring — Sub-Threshold Aggregation",
            "confidence_score": 0.82,
            "evidence": [
                f"{len(small_txns)} transactions in {round(period_days, 1)}-day window (threshold: 20)",
                f"Average amount: {round(total_amount / max(len(txns), 1), 2)}",
                f"{unique_counterparties} unique counterparties",
            ],
            "triggered_at": dt.datetime.utcnow().isoformat() + "Z",
            "rule_version": RULE_VERSION,
        })

    # Rule AML-017: Rapid movement after aggregation
    outbound = [t for t in txns if t.get("direction") == "out" and t.get("timestamp")]
    inbound = [t for t in txns if t.get("direction") == "in" and t.get("timestamp")]
    if inbound and outbound:
        last_in = max(inbound, key=lambda t: t.get("timestamp"))
        first_out = min(outbound, key=lambda t: t.get("timestamp"))
        if last_in.get("timestamp") and first_out.get("timestamp"):
            delta_hours = (first_out["timestamp"] - last_in["timestamp"]).total_seconds() / 3600.0
            if 0 <= delta_hours <= 6:
                evidence_blocks.append({
                    "rule_id": "AML-017",
                    "rule_name": "Rapid Fund Movement",
                    "confidence_score": 0.79,
                    "evidence": [
                        f"Immediate outbound transfer within {round(delta_hours, 2)} hours",
                        "No holding period observed",
                    ],
                    "triggered_at": dt.datetime.utcnow().isoformat() + "Z",
                    "rule_version": RULE_VERSION,
                })

    # Rule AML-021: High-risk corridor
    high_risk_countries = {"IR", "KP", "SY", "RU"}
    risky = [t for t in txns if t.get("country") in high_risk_countries]
    if risky:
        evidence_blocks.append({
            "rule_id": "AML-021",
            "rule_name": "High-Risk Corridor",
            "confidence_score": 0.7,
            "evidence": [
                f"{len(risky)} transactions linked to high-risk jurisdictions",
            ],
            "triggered_at": dt.datetime.utcnow().isoformat() + "Z",
            "rule_version": RULE_VERSION,
        })

    risk_score = sum(b["confidence_score"] for b in evidence_blocks)
    return evidence_blocks, risk_score
