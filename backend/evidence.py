import copy
import datetime as dt

PII_FIELDS = {
    "name", "customer_name", "account_number", "customer_id", "address",
    "email", "phone", "dob",
}


def _mask_value(value):
    if not value:
        return value
    s = str(value)
    if len(s) <= 4:
        return "****"
    return s[:2] + "****" + s[-2:]


def mask_pii(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in PII_FIELDS:
                out[k] = _mask_value(v)
            else:
                out[k] = mask_pii(v)
        return out
    if isinstance(obj, list):
        return [mask_pii(i) for i in obj]
    return obj


def build_decision_dataset(alert):
    customer = alert.get("customer", {})
    txns = alert.get("transactions", [])

    for txn in txns:
        ts = txn.get("timestamp")
        if isinstance(ts, str):
            cleaned = ts.replace("Z", "+00:00")
            try:
                txn["timestamp"] = dt.datetime.fromisoformat(cleaned)
            except ValueError:
                txn["timestamp"] = None

    timestamps = [t.get("timestamp") for t in txns if t.get("timestamp")]
    if timestamps:
        start_ts = min(timestamps)
        end_ts = max(timestamps)
        period_days = (end_ts - start_ts).total_seconds() / 86400.0
    else:
        start_ts = end_ts = None
        period_days = 0.0

    total_amount = sum(t.get("amount", 0.0) for t in txns)
    unique_counterparties = len({t.get("counterparty") for t in txns})

    return {
        "customer": customer,
        "transactions": txns,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "period_days": period_days,
        "total_amount": total_amount,
        "unique_counterparties": unique_counterparties,
        "risk_rating": alert.get("risk_rating", "medium"),
    }


def build_evidence_pack(decision_data, evidence_blocks):
    masked_customer = mask_pii(decision_data.get("customer", {}))

    summary = {
        "risk_rating": decision_data.get("risk_rating"),
        "period_start": decision_data.get("start_ts").isoformat() if decision_data.get("start_ts") else None,
        "period_end": decision_data.get("end_ts").isoformat() if decision_data.get("end_ts") else None,
        "transaction_count": len(decision_data.get("transactions", [])),
        "total_amount": decision_data.get("total_amount"),
        "unique_counterparties": decision_data.get("unique_counterparties"),
    }

    narrative_dataset = {
        "summary": summary,
        "customer_profile": masked_customer,
        "evidence_blocks": copy.deepcopy(evidence_blocks),
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
    }

    return narrative_dataset


def serialize_for_json(obj):
    if isinstance(obj, dt.datetime):
        return obj.isoformat()
    if isinstance(obj, list):
        return [serialize_for_json(i) for i in obj]
    if isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    return obj
