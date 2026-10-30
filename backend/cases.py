import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from config import settings
from db import SessionLocal
from models import Payment, Case, Merchant, Policy, Action
from firewall import evaluate_seven_gates
from recommender import recommend
from audit import record_audit_event
from events import broadcast
from fraud_graph import fraud_detector
from voice.sarvam import generate_tts, get_template_text

logger = logging.getLogger("pivaani.cases")

# Global handle for background task
_monitor_task: Optional[asyncio.Task] = None
_is_running: bool = False
# Strong refs so in-flight announcement tasks are not garbage-collected
_announce_tasks: set = set()

# Case lifecycle: OPEN (bank pending) -> AWAITING_APPROVAL -> RESOLVED | BLOCKED
ACTIVE_CASE_STATUSES = ("OPEN", "EVALUATING", "AWAITING_APPROVAL")

def generate_next_case_id(db: Session) -> str:
    """
    Generates the next sequential Case ID in the format 'PV-1001', 'PV-1002', etc.
    """
    existing_ids = db.query(Case.id).filter(Case.id.like("PV-%")).all()
    highest_num = 1000

    for (cid,) in existing_ids:
        try:
            parts = cid.split("-")
            if len(parts) == 2:
                num = int(parts[1])
                if num > highest_num:
                    highest_num = num
        except (ValueError, IndexError):
            continue

    return f"PV-{highest_num + 1}"

def current_policy(db: Session, merchant: Optional[Merchant]) -> Optional[Policy]:
    if not merchant:
        return None
    return db.query(Policy).filter(
        Policy.merchant_id == merchant.id,
        Policy.dial_level == merchant.trust_dial
    ).first()

async def publish_gates(label: str, decision: str, gates: Dict[str, Any], gate: str, case_id: Optional[str] = None):
    """Sends a 7-gate result to the merchant panel"""
    await broadcast("GATES_EVALUATED", {
        "attack_kind": label,
        "case_id": case_id,
        "decision": decision,
        "passed": decision == "ALLOW",
        "blocked_by": gate if decision == "BLOCK" else "",
        "held_by": gate if decision in ("HOLD", "NEEDS_APPROVAL") else "",
        "gates": gates
    })

# ----------------- Phase 1: detection ----------------- #
async def open_case(db: Session, payment: Payment, trigger_reason: str) -> Case:
    """Opens a Case for a payment, runs the gate pre-check, and has the soundbox speak"""
    now = datetime.utcnow()
    case = Case(
        id=generate_next_case_id(db),
        merchant_id=payment.merchant_id,
        payment_id=payment.id,
        status="OPEN",
        trigger_reason=trigger_reason,
        created_at=now,
        updated_at=now
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    logger.info(f"🚨 Opened Case {case.id} for Payment {payment.id} (₹{payment.amount}): {trigger_reason}")

    case_payload = {
        "case_id": case.id,
        "payment_id": payment.id,
        "status": case.status,
        "trigger_reason": case.trigger_reason,
        "amount": payment.amount,
        "payer_vpa": payment.payer_vpa,
        "payer_name": payment.payer_name,
        "created_at": case.created_at.isoformat()
    }
    record_audit_event(db=db, event_type="CASE_OPENED", actor="firewall", payload=case_payload)

    # Customer <-> merchant incident edge for the fraud-ring graph
    merchant = db.query(Merchant).filter(Merchant.id == payment.merchant_id).first()
    is_new_fraud, fraud_data = fraud_detector.add_stuck_payment_incident(
        customer_vpa=payment.payer_vpa,
        merchant_vpa=merchant.vpa if merchant else settings.DEFAULT_MERCHANT_VPA,
        case_id=case.id,
        timestamp=case.created_at
    )
    if is_new_fraud and fraud_data:
        logger.warning(f"🚨 FRAUD RING PATTERN for {payment.payer_vpa}: refunds routed to manual review")
        record_audit_event(db=db, event_type="FRAUD_RING_DETECTED", actor="system", payload=fraud_data)
        await broadcast("FRAUD_RING_DETECTED", fraud_data)

    await broadcast("CASE_OPENED", case_payload)

    # Pre-check: what would happen to a refund right now (normally HOLD: bank may still settle)
    policy = current_policy(db, merchant)
    if policy:
        decision, gates, gate = evaluate_seven_gates(
            payment=payment, merchant=merchant, policy=policy, recommendation=recommend(payment)
        )
        await publish_gates(f"{case.id} pre-check", decision, gates, gate, case.id)

    schedule_announcement(
        [("customer", "customer_reassure"), ("merchant", "merchant_case_opened")],
        amount=payment.amount, merchant_name=_merchant_name(merchant), case_id=case.id, reason="Case opened"
    )
    return case

async def check_and_create_stuck_cases(db: Session) -> List[Case]:
    """
    Inspects database for any PENDING payments older than DETECT_AFTER_SECONDS (2s)
    that do not yet have an incident Case opened.
    """
    cutoff_time = datetime.utcnow() - timedelta(seconds=settings.DETECT_AFTER_SECONDS)
    stuck_payments = db.query(Payment).filter(
        Payment.status == "PENDING",
        Payment.created_at <= cutoff_time
    ).all()

    opened: List[Case] = []
    for payment in stuck_payments:
        if db.query(Case).filter(Case.payment_id == payment.id).first():
            continue
        opened.append(await open_case(db, payment, f"Payment stuck > {settings.DETECT_AFTER_SECONDS}s"))
    return opened

# ----------------- Phase 4: resolution ladder ----------------- #
def _merchant_name(merchant: Optional[Merchant]) -> str:
    return merchant.business_name if merchant else settings.DEFAULT_MERCHANT_BUSINESS

def active_case_for(db: Session, payment: Payment) -> Optional[Case]:
    return db.query(Case).filter(
        Case.payment_id == payment.id,
        Case.status.in_(ACTIVE_CASE_STATUSES)
    ).order_by(Case.created_at.desc()).first()

async def resolve_bank_failure(db: Session, payment: Payment) -> Case:
    """
    The bank says the debit will not reach the merchant (DEBITED_NOT_CREDITED / FAILED).
    The recommender proposes a refund; the firewall decides whether it auto-executes,
    waits for the merchant's voice + PIN, or is blocked.
    """
    case = active_case_for(db, payment) or await open_case(db, payment, f"Bank reported {payment.status}")
    merchant = db.query(Merchant).filter(Merchant.id == payment.merchant_id).first()
    policy = current_policy(db, merchant)
    if not policy:
        await block_case(db, case, payment, "Authority", {"Authority": {"reason": "No merchant policy on file"}})
        return case
    recommendation = recommend(payment)

    decision, gates, gate = evaluate_seven_gates(
        payment=payment, merchant=merchant, policy=policy, recommendation=recommendation
    )
    record_audit_event(db=db, event_type="FIREWALL_EVALUATED", actor="firewall", payload={
        "case_id": case.id, "recommendation": recommendation, "decision": decision, "gate": gate, "gates": gates
    })
    await publish_gates(f"{case.id} refund", decision, gates, gate, case.id)

    if decision == "ALLOW":
        await execute_refund(db, case, payment, gates, approved_by=f"auto ({merchant.trust_dial} dial)")
    elif decision == "NEEDS_APPROVAL":
        case.status = "AWAITING_APPROVAL"
        case.recommended_action = "REFUND"
        case.updated_at = datetime.utcnow()
        db.commit()
        reason = gates[gate]["reason"] if gate in gates else "Merchant approval required"
        record_audit_event(db=db, event_type="APPROVAL_REQUIRED", actor="firewall", payload={
            "case_id": case.id, "amount": payment.amount, "held_by": gate, "reason": reason
        })
        await broadcast("APPROVAL_REQUIRED", {
            "case_id": case.id, "status": case.status, "amount": payment.amount, "held_by": gate, "reason": reason
        })
        schedule_announcement([("merchant", "merchant_approval_needed")], amount=payment.amount,
                              merchant_name=_merchant_name(merchant), case_id=case.id, reason="Approval required")
    else:
        await block_case(db, case, payment, gate, gates)
    return case

async def block_case(db: Session, case: Case, payment: Payment, gate: str, gates: Dict[str, Any]):
    reason = gates.get(gate, {}).get("reason", "Safety checks failed")
    case.status = "BLOCKED"
    case.resolution = f"Blocked by {gate}: {reason}"
    case.updated_at = datetime.utcnow()
    db.commit()
    record_audit_event(db=db, event_type="CASE_BLOCKED", actor="firewall", payload={
        "case_id": case.id, "blocked_by": gate, "reason": reason
    })
    await broadcast("CASE_RESOLVED", {
        "case_id": case.id, "resolution": "BLOCKED", "amount": payment.amount, "blocked_by": gate, "reason": reason
    })
    schedule_announcement([("merchant", "refund_blocked")], amount=payment.amount,
                          merchant_name=settings.DEFAULT_MERCHANT_BUSINESS, case_id=case.id,
                          blocked=True, reason=f"Refund blocked by {gate}")

async def execute_refund(db: Session, case: Case, payment: Payment, gates: Dict[str, Any], approved_by: str):
    """The only place money moves: plain Python, reached only after an ALLOW decision"""
    now = datetime.utcnow()
    payment.status = "REFUNDED"
    payment.updated_at = now
    db.add(Action(
        id=f"ACT_{case.id}_REFUND_{uuid.uuid4().hex[:6]}",
        case_id=case.id,
        action_type="REFUND",
        status="EXECUTED",
        gate_results=str(gates),
        blocked_by_gate=None,
        executed_at=now,
        created_at=now
    ))
    case.status = "RESOLVED"
    case.resolution = f"Refunded ₹{payment.amount:g} ({approved_by})"
    case.updated_at = now
    db.commit()

    record_audit_event(db=db, event_type="REFUND_EXECUTED", actor="firewall", payload={
        "case_id": case.id, "payment_id": payment.id, "amount": payment.amount, "approved_by": approved_by
    })
    await broadcast("CASE_RESOLVED", {
        "case_id": case.id, "resolution": "REFUNDED", "amount": payment.amount, "approved_by": approved_by
    })
    await issue_receipts(db, case, payment, "refunded")
    merchant = db.query(Merchant).filter(Merchant.id == payment.merchant_id).first()
    schedule_announcement([("customer", "customer_refunded"), ("merchant", "merchant_refund_done")],
                          amount=payment.amount, merchant_name=_merchant_name(merchant), case_id=case.id,
                          reason="Refund executed")

# ----------------- Phase 6: resolution ----------------- #
async def confirm_payment(db: Session, payment: Payment):
    """Bank confirmed the credit: close the case and issue receipts"""
    payment.status = "SUCCESS"
    payment.updated_at = datetime.utcnow()
    cases = db.query(Case).filter(Case.payment_id == payment.id, Case.status.in_(ACTIVE_CASE_STATUSES)).all()
    for case in cases:
        case.status = "RESOLVED"
        case.resolution = "Payment confirmed by bank"
        case.updated_at = datetime.utcnow()
    db.commit()

    merchant = db.query(Merchant).filter(Merchant.id == payment.merchant_id).first()
    for case in cases:
        record_audit_event(db=db, event_type="CASE_RESOLVED", actor="system", payload={
            "case_id": case.id, "payment_id": payment.id, "resolution": "CONFIRMED"
        })
        await broadcast("CASE_RESOLVED", {"case_id": case.id, "resolution": "CONFIRMED", "amount": payment.amount})
        await issue_receipts(db, case, payment, "confirmed")
    schedule_announcement([("merchant", "payment_success")], amount=payment.amount,
                          merchant_name=_merchant_name(merchant), case_id=cases[0].id if cases else None,
                          reason="Payment confirmed")

async def reconcile_late_bank_update(db: Session, payment: Payment, bank_status: str):
    """
    The bank reported on a payment we already refunded (a late credit or an
    automatic reversal). Money may now have moved twice, so flag it for
    recovery instead of silently overwriting the refund.
    """
    message = (
        f"Late bank update {bank_status} after refund of ₹{payment.amount:g}: "
        + ("merchant credited after refund, recover from customer" if bank_status == "SUCCESS"
           else "bank auto-reversed the debit after our refund, recover the duplicate refund")
    )
    record_audit_event(db=db, event_type="RECONCILIATION_REQUIRED", actor="system", payload={
        "payment_id": payment.id, "bank_status": bank_status, "message": message
    })
    await broadcast("RECONCILIATION", {"payment_id": payment.id, "bank_status": bank_status, "message": message})

async def issue_receipts(db: Session, case: Case, payment: Payment, outcome: str):
    """Bharosa Receipt for customer and merchant, each in their own language"""
    key = "receipt_refunded" if outcome == "refunded" else "receipt_confirmed"
    receipt = {
        "case_id": case.id,
        "payment_id": payment.id,
        "amount": payment.amount,
        "outcome": outcome,
        "customer": {"lang": settings.CUSTOMER_VOICE_LANG,
                     "text": get_template_text(key, lang=settings.CUSTOMER_VOICE_LANG, amount=payment.amount, case_id=case.id)},
        "merchant": {"lang": settings.MERCHANT_VOICE_LANG,
                     "text": get_template_text(key, lang=settings.MERCHANT_VOICE_LANG, amount=payment.amount, case_id=case.id)},
        "issued_at": datetime.utcnow().isoformat()
    }
    entry = record_audit_event(db=db, event_type="RECEIPT_ISSUED", actor="system", payload=receipt)
    await broadcast("RECEIPT", {**receipt, "audit_hash": entry.event_hash})

# ----------------- Voice ----------------- #
def _audience_lang(audience: str) -> str:
    return settings.CUSTOMER_VOICE_LANG if audience == "customer" else settings.MERCHANT_VOICE_LANG

async def announce(
    items: List[Tuple[str, str]],
    amount: float,
    merchant_name: str,
    case_id: Optional[str] = None,
    blocked: bool = False,
    reason: str = ""
):
    """
    Broadcasts one SPEAK event per (audience, template_key), in order. Customer
    lines use CUSTOMER_VOICE_LANG and merchant lines MERCHANT_VOICE_LANG; the
    soundbox client queues them so they play back-to-back.
    """
    try:
        langs = [_audience_lang(audience) for audience, _ in items]
        texts = [
            get_template_text(key, lang=lang, amount=amount, merchant=merchant_name, case_id=case_id)
            for (_, key), lang in zip(items, langs)
        ]
        # Synthesize all clips concurrently; None means the client falls back to browser speech
        audio_urls = await asyncio.gather(*(generate_tts(text, lang=lang) for text, lang in zip(texts, langs)))
        for (audience, _), lang, text, audio_url in zip(items, langs, texts, audio_urls):
            await broadcast("SPEAK", {
                "text": text,
                "audio_url": audio_url,
                "lang": lang,
                "audience": audience,
                "case_id": case_id,
                "blocked": blocked,
                "reason": reason
            })
    except Exception as e:
        logger.error(f"Failed to announce {reason} ({case_id}): {e}")

def schedule_announcement(items: List[Tuple[str, str]], **kwargs):
    """Fire-and-forget announce(): TTS latency never delays the caller"""
    task = asyncio.create_task(announce(items, **kwargs))
    _announce_tasks.add(task)
    task.add_done_callback(_announce_tasks.discard)

async def prewarm_case_announcements(amount: float = 40.0, case_id: str = "PV-1001"):
    """
    Synthesizes the demo's first-case (₹40, PV-1001) lines at startup so they
    speak instantly instead of waiting on a cold Sarvam call.
    """
    clips = [
        ("customer", "customer_reassure"), ("merchant", "merchant_case_opened"),
        ("customer", "customer_retap_blocked"), ("merchant", "merchant_approval_needed"),
        ("customer", "customer_refunded"), ("merchant", "merchant_refund_done"),
        ("merchant", "payment_success"), ("merchant", "approval_rejected"),
    ]
    try:
        await asyncio.gather(*(
            generate_tts(
                get_template_text(key, lang=_audience_lang(audience), amount=amount,
                                  merchant=settings.DEFAULT_MERCHANT_BUSINESS, case_id=case_id),
                lang=_audience_lang(audience)
            )
            for audience, key in clips
        ))
    except Exception as e:
        logger.warning(f"Could not prewarm case announcements: {e}")

# ----------------- Background monitor ----------------- #
async def stuck_payment_monitor():
    """
    Background worker loop: checks the database every 1 second for stuck payments.
    """
    global _is_running
    logger.info("Case State Machine background monitor started (polling interval: 1s)")

    while _is_running:
        try:
            db = SessionLocal()
            try:
                await check_and_create_stuck_cases(db)
            finally:
                db.close()
        except asyncio.CancelledError:
            logger.info("Case monitor task cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in stuck payment background monitor: {e}")

        try:
            await asyncio.sleep(1)
        except asyncio.CancelledError:
            break

def start_case_monitor():
    """Starts the background asyncio monitor task"""
    global _monitor_task, _is_running
    if _monitor_task is None or _monitor_task.done():
        _is_running = True
        _monitor_task = asyncio.create_task(stuck_payment_monitor())
        task = asyncio.create_task(prewarm_case_announcements())
        _announce_tasks.add(task)
        task.add_done_callback(_announce_tasks.discard)

def stop_case_monitor():
    """Stops the background asyncio monitor task"""
    global _monitor_task, _is_running
    _is_running = False
    if _monitor_task and not _monitor_task.done():
        _monitor_task.cancel()
        _monitor_task = None
