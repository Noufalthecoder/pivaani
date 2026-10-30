import hashlib
import hmac
import json
import os
import secrets
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from models import AuditEvent

GENESIS_HASH = "0" * 64

# Key that signs the chain head. Set AUDIT_SIGNING_KEY in production; for local
# runs a random key is generated once and kept next to the database.
_KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".audit_signing_key")

def _signing_key() -> bytes:
    env_key = os.getenv("AUDIT_SIGNING_KEY", "").strip()
    if env_key:
        return env_key.encode("utf-8")
    if not os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, "w") as f:
            f.write(secrets.token_hex(32))
    with open(_KEY_FILE) as f:
        return f.read().strip().encode("utf-8")

def sign_head(latest_hash: str, total_events: int) -> str:
    """HMAC over the chain head: rewriting history and recomputing hashes no longer verifies without the key"""
    return hmac.new(_signing_key(), f"{total_events}:{latest_hash}".encode("utf-8"), hashlib.sha256).hexdigest()

def install_append_only_guards(engine) -> None:
    """SQLite triggers that make audit_events append-only: UPDATE and DELETE abort"""
    with engine.begin() as conn:
        for op in ("UPDATE", "DELETE"):
            conn.execute(text(
                f"CREATE TRIGGER IF NOT EXISTS audit_events_no_{op.lower()} "
                f"BEFORE {op} ON audit_events "
                f"BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;"
            ))

def canonical_json(data: Any) -> str:
    """Produces deterministic, canonical JSON string for hashing"""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)

def compute_event_hash(prev_hash: str, timestamp_str: str, event_type: str, actor: str, payload_json: str) -> str:
    """
    Computes SHA-256 hash linking the previous block's hash with current event fields.
    Format: SHA256(prev_hash | timestamp | event_type | actor | canonical_payload)
    """
    raw_payload = f"{prev_hash}|{timestamp_str}|{event_type}|{actor}|{payload_json}"
    return hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

def record_audit_event(
    db: Session,
    event_type: str,
    actor: str,
    payload: Dict[str, Any],
    timestamp: datetime = None
) -> AuditEvent:
    """
    Appends a new immutable event to the cryptographic audit hash chain.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()

    # Retrieve the latest audit event to find the previous hash
    last_event = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
    prev_hash = last_event.event_hash if last_event else GENESIS_HASH

    timestamp_str = timestamp.isoformat()
    payload_str = canonical_json(payload)
    event_hash = compute_event_hash(prev_hash, timestamp_str, event_type, actor, payload_str)

    audit_entry = AuditEvent(
        event_id=f"EVT_{uuid.uuid4().hex[:12].upper()}",
        prev_hash=prev_hash,
        event_hash=event_hash,
        event_type=event_type,
        actor=actor,
        payload=payload_str,
        timestamp=timestamp,
        created_at=datetime.utcnow()
    )

    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry

def verify_chain(db: Session) -> Dict[str, Any]:
    """
    Verifies cryptographic integrity of the entire audit event hash chain.
    Returns validation status, total events checked, and error details if broken.
    """
    events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
    if not events:
        return {
            "valid": True,
            "total_events": 0,
            "message": "Empty audit chain (valid)"
        }

    expected_prev_hash = GENESIS_HASH

    for idx, event in enumerate(events):
        # 1. Verify previous hash pointer matches expected link
        if event.prev_hash != expected_prev_hash:
            return {
                "valid": False,
                "broken_at_id": event.id,
                "broken_at_event_id": event.event_id,
                "reason": f"Broken link at event #{event.id}: expected prev_hash '{expected_prev_hash}', got '{event.prev_hash}'",
                "total_events": len(events)
            }

        # 2. Recompute hash from source fields
        timestamp_str = event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp)
        # Parse and re-canonicalize payload to ensure exact formatting
        try:
            parsed_payload = json.loads(event.payload)
            canonical_payload_str = canonical_json(parsed_payload)
        except Exception:
            canonical_payload_str = event.payload

        calculated_hash = compute_event_hash(
            event.prev_hash,
            timestamp_str,
            event.event_type,
            event.actor,
            canonical_payload_str
        )

        if event.event_hash != calculated_hash:
            return {
                "valid": False,
                "broken_at_id": event.id,
                "broken_at_event_id": event.event_id,
                "reason": f"Hash mismatch at event #{event.id}: stored '{event.event_hash}', calculated '{calculated_hash}'",
                "total_events": len(events)
            }

        expected_prev_hash = event.event_hash

    return {
        "valid": True,
        "total_events": len(events),
        "genesis_hash": events[0].event_hash,
        "latest_hash": events[-1].event_hash,
        "head_signature": sign_head(events[-1].event_hash, len(events)),
        "message": f"All {len(events)} hash links verified successfully"
    }

