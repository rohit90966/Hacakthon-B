import json
from pathlib import Path
import requests

from .config import OLLAMA_MODEL, OLLAMA_URL, USE_MOCK_LLM

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "sar_prompt.txt"


def _load_prompt_template():
    return PROMPT_PATH.read_text(encoding="utf-8")


def _extract_json(text):
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in LLM response: {text[:200]}")
    json_str = text[start:end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in LLM response: {e}. Text: {json_str[:200]}")


def _generate_mock_narrative(narrative_dataset):
    """Deterministic mock narrative in sectioned format for offline dev."""
    summary = narrative_dataset.get("summary", {})
    evidence_blocks = narrative_dataset.get("evidence_blocks", [])
    rule_ids = [b.get("rule_id") for b in evidence_blocks]

    subject = narrative_dataset.get("customer_profile", {})
    subject_text = f"Customer exhibits activity inconsistent with declared profile during {summary.get('period_start', 'N/A')} to {summary.get('period_end', 'N/A')}"
    account_text = f"Account handled {summary.get('transaction_count', 0)} transactions totaling {summary.get('total_amount', 0)} across {summary.get('unique_counterparties', 0)} counterparties."

    return {
        "subject_information": subject_text,
        "account_details": account_text,
        "alert_summary": f"Alert triggered due to velocity and counterparty concentration over {summary.get('period_days', 'N/A')} days.",
        "transaction_pattern_analysis": "Patterns show compressed inbound followed by outbound movement consistent with structuring and layering.",
        "suspicious_behaviour_indicators": "; ".join([b.get("rule_name", "") for b in evidence_blocks]),
        "supporting_evidence": ", ".join(rule_ids),
        "regulatory_justification": "Activity meets reporting thresholds and typologies referenced in AML-001/AML-017 guidance.",
        "investigator_assessment": "Narrative compiled with masked PII and bounded evidence set.",
        "conclusion_recommendation": "File SAR and monitor for escalation; consider enhanced due diligence.",
        "confidence_level": 0.82,
    }


def generate_narrative(narrative_dataset, rag_context, force_mock=False):
    if USE_MOCK_LLM or force_mock:
        mock_narrative = _generate_mock_narrative(narrative_dataset)
        return mock_narrative, {
            "prompt": "[MOCK MODE]",
            "raw_response": json.dumps(mock_narrative),
            "model": "mock",
        }

    template = _load_prompt_template()
    prompt = template.format(
        narrative_dataset=json.dumps(narrative_dataset, ensure_ascii=False),
        rag_context=json.dumps(rag_context, ensure_ascii=False),
    )

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.25, "num_predict": 1400},
        "format": "json"
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()
        response_payload = data.get("response", "")

        if isinstance(response_payload, dict):
            narrative = response_payload
        else:
            narrative = _extract_json(str(response_payload))

        return narrative, {
            "prompt": prompt,
            "raw_response": response_payload,
            "model": OLLAMA_MODEL,
        }
    except (requests.RequestException, ValueError) as e:
        mock_narrative = _generate_mock_narrative(narrative_dataset)
        return mock_narrative, {
            "prompt": prompt,
            "raw_response": f"[LLM ERROR: {str(e)}] Fallback to mock",
            "model": f"{OLLAMA_MODEL}_fallback",
            "error": str(e),
        }
