import datetime as dt

from .evidence import mask_pii
from .models import AuditEvent


def log_event(session, case_id, event_type, payload):
    masked_payload = mask_pii(payload)
    event = AuditEvent(
        case_id=case_id,
        event_type=event_type,
        timestamp=dt.datetime.utcnow(),
        payload=masked_payload,
    )
    session.add(event)
    session.commit()
    return event


def get_audit_timeline(session, case_id):
    events = (
        session.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.timestamp.asc())
        .all()
    )
    return [
        {
            "timestamp": e.timestamp.isoformat() + "Z",
            "event_type": e.event_type,
            "payload": e.payload,
        }
        for e in events
    ]
