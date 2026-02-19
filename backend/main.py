import uuid
from typing import List

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .audit import get_audit_timeline, log_event
from .config import TOP_K
from .db import SessionLocal, init_db
from .evidence import build_decision_dataset, build_evidence_pack, serialize_for_json
from .explainability import build_explainability_trace
from .llm import generate_narrative
from .metrics import metrics, timed
from .models import Case
from .pdf_exporter import generate_pdf
from .rag import RAGRetriever
from .review_workflow import can_transition, record_history
from .risk_engine import assess_risk
from .rules import evaluate_rules
from .sar_formatter import format_sar_narrative, narrative_as_text
from .validation_v2 import validate_v2

app = FastAPI(title="SAR Narrative Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_retriever = RAGRetriever()


@app.on_event("startup")
def startup():
    init_db()
    rag_retriever.load_corpus()


def _confidence_from_evidence(evidence_blocks: List[dict]) -> float:
    if not evidence_blocks:
        return 0.5
    return sum(b.get("confidence_score", 0.0) for b in evidence_blocks) / len(evidence_blocks)


def _hallucination_guard(formatted_narrative, evidence_blocks):
    citations = set(formatted_narrative.get("evidence_citations", []))
    rule_ids = {b.get("rule_id") for b in evidence_blocks}
    if not citations or not citations.issubset(rule_ids):
        metrics.record_hallucination_rejection()
        raise HTTPException(status_code=400, detail="Narrative rejected: unsupported claims detected")


@timed
def run_pipeline(session, case_obj, alert):
    metrics.record_request()
    decision_data = build_decision_dataset(alert)
    decision_data_json = serialize_for_json(decision_data)
    log_event(session, case_obj.id, "ENRICHED", {"decision_data": decision_data_json})

    evidence_blocks, risk_score = evaluate_rules(decision_data)
    log_event(session, case_obj.id, "RULE_TRIGGERED", {"evidence_blocks": evidence_blocks})

    risk_assessment = assess_risk(decision_data, evidence_blocks)
    log_event(session, case_obj.id, "RISK_ASSESSED", risk_assessment.__dict__)

    narrative_dataset = build_evidence_pack(decision_data, evidence_blocks)
    log_event(session, case_obj.id, "EVIDENCE_BUILT", {"narrative_dataset": narrative_dataset})

    rag_context = rag_retriever.retrieve(
        query=str(narrative_dataset.get("summary")),
        top_k=TOP_K,
    )
    log_event(session, case_obj.id, "RETRIEVAL_COMPLETE", {"rag_context": rag_context})

    try:
        narrative, llm_meta = generate_narrative(narrative_dataset, rag_context)
    except Exception as e:
        log_event(session, case_obj.id, "ERROR", {"error": f"LLM failure: {str(e)}"})
        narrative, llm_meta = generate_narrative(narrative_dataset, rag_context, force_mock=True)

    log_event(session, case_obj.id, "DRAFT_GENERATED", {
        "llm_meta": llm_meta,
        "narrative": narrative,
    })

    evidence_citations = [b.get("rule_id") for b in evidence_blocks]
    confidence_level = _confidence_from_evidence(evidence_blocks)
    formatted = format_sar_narrative(
        llm_sections=narrative,
        risk_score=risk_assessment.risk_score,
        risk_level=risk_assessment.risk_level,
        confidence_level=confidence_level,
        evidence_citations=evidence_citations,
        contributing_factors=risk_assessment.contributing_factors,
    )

    explainability_trace = build_explainability_trace(formatted, evidence_blocks)
    validation = validate_v2(formatted, explainability_trace)
    metrics.record_validation(validation.get("passed"))
    log_event(session, case_obj.id, "VALIDATED", {"validation": validation})

    _hallucination_guard(formatted, evidence_blocks)

    sar_text = narrative_as_text(formatted)
    validation_status = "DRAFT" if validation.get("passed") else "VALIDATION_FAILED"

    case_obj.decision_data = decision_data_json
    case_obj.evidence_data = narrative_dataset
    case_obj.rag_context = rag_context
    case_obj.draft_narrative = formatted
    case_obj.validation_results = validation
    case_obj.validation_v2_results = validation
    case_obj.risk_score = risk_assessment.risk_score
    case_obj.risk_level = risk_assessment.risk_level
    case_obj.confidence_level = confidence_level
    case_obj.explainability_trace = explainability_trace
    case_obj.sar_document = sar_text
    case_obj.status = validation_status
    session.commit()


@app.post("/ingest-alert")
def ingest_alert(alert: dict):
    session = SessionLocal()
    case_id = str(uuid.uuid4())

    case_obj = Case(
        id=case_id,
        alert_json=alert,
        status="INGESTED",
    )
    session.add(case_obj)
    session.commit()

    log_event(session, case_id, "INGESTED", {"alert": alert})

    try:
        run_pipeline(session, case_obj, alert)
    except Exception as exc:
        log_event(session, case_id, "ERROR", {"error": str(exc)})
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Snapshot status before closing to avoid DetachedInstanceError
        status = case_obj.status
        session.close()

    return {"case_id": case_id, "status": status}


@app.post("/batch-ingest")
def batch_ingest(payload: dict):
    alerts = payload.get("alerts", [])
    session = SessionLocal()
    metrics.record_batch()
    results = []
    for alert in alerts:
        case_id = str(uuid.uuid4())
        case_obj = Case(id=case_id, alert_json=alert, status="INGESTED")
        session.add(case_obj)
        session.commit()
        log_event(session, case_id, "INGESTED", {"alert": alert})
        try:
            run_pipeline(session, case_obj, alert)
            status = case_obj.status
        except Exception as exc:
            log_event(session, case_id, "ERROR", {"error": str(exc)})
            status = "ERROR"
        results.append({"case_id": case_id, "status": status, "risk_score": case_obj.risk_score})
    session.close()
    # priority queue by risk descending
    results = sorted(results, key=lambda r: r.get("risk_score", 0), reverse=True)
    return {"results": results}


@app.get("/cases")
def list_cases():
    session = SessionLocal()
    cases = session.query(Case).order_by(Case.created_at.desc()).all()
    result = [
        {
            "id": c.id,
            "status": c.status,
            "created_at": c.created_at.isoformat() + "Z",
            "risk_score": c.risk_score,
            "risk_level": c.risk_level,
        }
        for c in cases
    ]
    session.close()
    return result


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    session = SessionLocal()
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")

    result = {
        "id": case_obj.id,
        "status": case_obj.status,
        "created_at": case_obj.created_at.isoformat() + "Z",
        "alert": case_obj.alert_json,
        "decision_data": case_obj.decision_data,
        "evidence_data": case_obj.evidence_data,
        "rag_context": case_obj.rag_context,
        "draft_narrative": case_obj.draft_narrative,
        "final_narrative": case_obj.final_narrative,
        "validation_results": case_obj.validation_results,
        "validation_v2_results": case_obj.validation_v2_results,
        "risk_score": case_obj.risk_score,
        "risk_level": case_obj.risk_level,
        "confidence_level": case_obj.confidence_level,
        "explainability_trace": case_obj.explainability_trace,
        "sar_document": case_obj.sar_document,
        "analyst_comment": case_obj.analyst_comment,
        "review_history": case_obj.review_history,
        "version": case_obj.version,
    }
    session.close()
    return result


@app.post("/cases/{case_id}/submit")
def submit_case(case_id: str, payload: dict = None):
    session = SessionLocal()
    payload = payload or {}
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")
    if not can_transition(case_obj.status, "REVIEW"):
        session.close()
        raise HTTPException(status_code=400, detail="Invalid transition")

    case_obj.status = "REVIEW"
    case_obj.review_history = record_history(case_obj.review_history, payload.get("user", "system"), "SUBMITTED", payload.get("comment"))
    case_obj.version = (case_obj.version or 1) + 1
    session.commit()
    log_event(session, case_id, "SUBMITTED", payload or {})
    status = case_obj.status
    session.close()
    return {"status": status}


@app.post("/cases/{case_id}/approve")
def approve_case(case_id: str, payload: dict):
    session = SessionLocal()
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")

    next_state = "APPROVED"
    if not can_transition(case_obj.status, next_state):
        session.close()
        raise HTTPException(status_code=400, detail="Invalid transition")

    case_obj.status = next_state
    case_obj.final_narrative = payload.get("narrative", case_obj.draft_narrative)
    case_obj.analyst_comment = payload.get("comment")
    case_obj.analyst_role = payload.get("role", "analyst")
    case_obj.review_history = record_history(case_obj.review_history, payload.get("role", "analyst"), "APPROVED", payload.get("comment"))
    session.commit()

    log_event(session, case_id, "APPROVED", payload)
    status = case_obj.status
    session.close()
    return {"status": status}


@app.post("/cases/{case_id}/reject")
def reject_case(case_id: str, payload: dict):
    session = SessionLocal()
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")

    next_state = "REJECTED"
    if not can_transition(case_obj.status, next_state):
        session.close()
        raise HTTPException(status_code=400, detail="Invalid transition")

    case_obj.status = next_state
    case_obj.analyst_comment = payload.get("comment")
    case_obj.analyst_role = payload.get("role", "analyst")
    case_obj.review_history = record_history(case_obj.review_history, payload.get("role", "analyst"), "REJECTED", payload.get("comment"))
    session.commit()

    log_event(session, case_id, "REJECTED", payload)
    session.close()
    return {"status": case_obj.status}


@app.post("/cases/{case_id}/finalize")
def finalize_case(case_id: str, payload: dict = None):
    session = SessionLocal()
    payload = payload or {}
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")
    if not can_transition(case_obj.status, "SUBMITTED"):
        session.close()
        raise HTTPException(status_code=400, detail="Invalid transition")

    case_obj.status = "SUBMITTED"
    case_obj.review_history = record_history(case_obj.review_history, payload.get("user", "system"), "SUBMITTED", payload.get("comment"))
    session.commit()
    log_event(session, case_id, "SUBMITTED", payload or {})
    status = case_obj.status
    session.close()
    return {"status": status}


@app.get("/cases/{case_id}/audit")
def case_audit(case_id: str):
    session = SessionLocal()
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")
    timeline = get_audit_timeline(session, case_id)
    session.close()
    return {"case_id": case_id, "timeline": timeline}


@app.get("/cases/{case_id}/export/pdf")
def export_pdf(case_id: str):
    session = SessionLocal()
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")
    pdf_bytes = generate_pdf(case_obj.final_narrative or case_obj.draft_narrative or {})
    session.close()
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={case_id}.pdf"})


@app.get("/cases/{case_id}/export/json")
def export_json(case_id: str):
    session = SessionLocal()
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")
    payload = {
        "case": case_obj.id,
        "narrative": case_obj.final_narrative or case_obj.draft_narrative,
        "risk": {"score": case_obj.risk_score, "level": case_obj.risk_level, "confidence": case_obj.confidence_level},
        "explainability_trace": case_obj.explainability_trace,
    }
    session.close()
    return payload


@app.get("/cases/{case_id}/export/audit")
def export_audit_bundle(case_id: str):
    session = SessionLocal()
    case_obj = session.query(Case).filter(Case.id == case_id).first()
    if not case_obj:
        session.close()
        raise HTTPException(status_code=404, detail="Case not found")
    timeline = get_audit_timeline(session, case_id)
    session.close()
    return {"case_id": case_id, "timeline": timeline, "narrative": case_obj.final_narrative or case_obj.draft_narrative}


@app.get("/metrics")
def get_metrics():
    return metrics.snapshot()
