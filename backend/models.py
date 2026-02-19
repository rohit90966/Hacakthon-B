import datetime as dt
from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.types import JSON

from .db import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    status = Column(String, default="INGESTED")
    analyst_role = Column(String, default="analyst")

    alert_json = Column(JSON)
    decision_data = Column(JSON)
    evidence_data = Column(JSON)
    rag_context = Column(JSON)
    validation_results = Column(JSON)
    validation_v2_results = Column(JSON)

    draft_narrative = Column(JSON)
    final_narrative = Column(JSON)
    sar_document = Column(Text)
    risk_level = Column(String, default="LOW")
    confidence_level = Column(Float, default=0.0)
    explainability_trace = Column(JSON)
    review_history = Column(JSON)
    version = Column(Integer, default=1)
    analyst_comment = Column(Text)
    risk_score = Column(Float, default=0.0)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, index=True)
    timestamp = Column(DateTime, default=dt.datetime.utcnow)
    event_type = Column(String, index=True)
    payload = Column(JSON)
