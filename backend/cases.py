import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from config import settings
from db import SessionLocal
from models import Payment, Case
from audit import record_audit_event
from events import broadcast

logger = logging.getLogger("pivaani.cases")

# Global handle for background task
_monitor_task: Optional[asyncio.Task] = None
_is_running: bool = False

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

async def check_and_create_stuck_cases(db: Session) -> List[Case]:
    """
    Inspects database for any PENDING payments older than DETECT_AFTER_SECONDS (2s)
    that do not yet have an active incident Case opened.
    """
    now = datetime.utcnow()
    cutoff_time = now - timedelta(seconds=settings.DETECT_AFTER_SECONDS)

    # Find pending payments older than the threshold
    stuck_payments = db.query(Payment).filter(
        Payment.status == "PENDING",
        Payment.created_at <= cutoff_time
    ).all()

    newly_opened_cases: List[Case] = []

    for payment in stuck_payments:
        # Check if a case already exists for this payment
        existing_case = db.query(Case).filter(Case.payment_id == payment.id).first()
        if existing_case:
            continue

        case_id = generate_next_case_id(db)
        trigger_reason = f"Payment stuck > {settings.DETECT_AFTER_SECONDS}s"

        case = Case(
            id=case_id,
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

        logger.info(f"🚨 Auto-opened Incident Case {case.id} for stuck Payment {payment.id} (₹{payment.amount})")

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

        # 1. Record immutable cryptographic audit entry
        record_audit_event(
            db=db,
            event_type="CASE_OPENED",
            actor="firewall",
            payload=case_payload
        )

        # 2. Broadcast real-time WebSocket event to soundbox and merchant UI
        await broadcast("CASE_OPENED", case_payload)
        newly_opened_cases.append(case)

    return newly_opened_cases

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

def stop_case_monitor():
    """Stops the background asyncio monitor task"""
    global _monitor_task, _is_running
    _is_running = False
    if _monitor_task and not _monitor_task.done():
        _monitor_task.cancel()
        _monitor_task = None

