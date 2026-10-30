from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from models import Payment, Case, Merchant
from sandbox import create_mock_payment
from audit import record_audit_event
from events import broadcast
from locks import lock_manager
from fraud_graph import fraud_detector
from firewall import evaluate_seven_gates
from recommender import recommend
from security import nonce_store, pin_limiter, verify_pin, MAX_PIN_ATTEMPTS
from cases import (
    schedule_announcement, current_policy, publish_gates, resolve_bank_failure,
    execute_refund, block_case, confirm_payment, reconcile_late_bank_update, active_case_for
)
import schemas

router = APIRouter(tags=["Sandbox Scenarios & Fraud Protection"])

# A payment in one of these states is still in flight: paying the same amount
# to the same merchant again is a retap, not a new purchase.
UNRESOLVED_PAYMENT_STATUSES = ("PENDING", "DEBITED_NOT_CREDITED")

# Request models
class SandboxPayRequest(BaseModel):
    amount: float = Field(default=40.0, description="Amount in INR")
    scenario: str = Field(default="pending", description="Scenario type: pending, success")
    payer_vpa: Optional[str] = "customer@upi"
    payer_name: Optional[str] = "Customer"
    merchant_vpa: Optional[str] = None
    confirm_new: bool = Field(default=False, description="Customer explicitly confirms a second, separate purchase")

class PaymentStateUpdateRequest(BaseModel):
    status: str = Field(..., description="Bank status: SUCCESS, DEBITED_NOT_CREDITED, FAILED, REVERSED")

class RetapRequest(BaseModel):
    payment_id: Optional[str] = None
    customer_vpa: Optional[str] = "customer@upi"

class ChallengeRequest(BaseModel):
    case_id: str

class ApprovalRequest(BaseModel):
    case_id: str = Field(..., description="Incident Case ID e.g. PV-1001")
    nonce: Optional[str] = Field(default=None, description="Single-use nonce from /api/approval/challenge")
    pin: Optional[str] = Field(default=None, description="Merchant PIN")
    actor: str = Field(default="merchant_voice", description="Channel: merchant_voice, merchant_app, customer_voice")
    voice_command: Optional[str] = Field(default="Approve refund", description="Voice command transcript")
    action_type: str = Field(default="REFUND", description="Target action type")

# -------------------------------------------------------------
# 1. PAY (idempotent per payer + merchant + amount)
# -------------------------------------------------------------
async def _block_duplicate(db: Session, payment: Payment):
    """Phase 3: a second tap while the first payment is in flight is blocked, not charged"""
    merchant = db.query(Merchant).filter(Merchant.id == payment.merchant_id).first()
    event_payload = {
        "message": "Second payment attempt blocked: original still in flight",
        "customer_vpa": payment.payer_vpa,
        "payment_id": payment.id,
        "amount": payment.amount,
        "timestamp": datetime.utcnow().isoformat()
    }
    record_audit_event(db=db, event_type="RETAP_BLOCKED", actor="customer", payload=event_payload)
    await broadcast("RETAP_DETECTED", event_payload)

    policy = current_policy(db, merchant)
    if policy:
        decision, gates, gate = evaluate_seven_gates(
            payment=payment, merchant=merchant, policy=policy,
            recommendation=recommend(payment), retap_collision=True
        )
        case = active_case_for(db, payment)
        await publish_gates("retap", decision, gates, gate, case.id if case else None)
    schedule_announcement([("customer", "customer_retap_blocked")], amount=payment.amount,
                          merchant_name=merchant.business_name if merchant else "Merchant",
                          blocked=True, reason="Duplicate payment blocked")

@router.post("/api/sandbox/pay", response_model=schemas.PaymentOut, status_code=status.HTTP_201_CREATED)
async def sandbox_pay(payload: SandboxPayRequest, response: Response, db: Session = Depends(get_db)):
    """
    Simulates customer payment initiation. If the same payer already has a
    payment of the same amount to the same merchant in flight, no new payment
    is created: the original is returned (HTTP 200, Idempotent-Replay: true).
    """
    merchant = None
    if payload.merchant_vpa:
        merchant = db.query(Merchant).filter(Merchant.vpa == payload.merchant_vpa).first()
        if not merchant:
            # Create transient mock merchant for fraud ring simulation
            merchant = Merchant(
                name=payload.merchant_vpa.split("@")[0].capitalize(),
                business_name=f"{payload.merchant_vpa.split('@')[0].capitalize()} Store",
                vpa=payload.merchant_vpa,
                trust_dial="balanced",
                pin="!"
            )
            db.add(merchant)
            db.commit()
            db.refresh(merchant)
    if not merchant:
        merchant = db.query(Merchant).order_by(Merchant.id.asc()).first()

    payer_vpa = payload.payer_vpa or "customer@upi"
    idem_key = lock_manager.generate_key(f"{payer_vpa}:{merchant.id}:{payload.amount:.2f}", "pay")

    # Serialize same-key requests so two simultaneous taps cannot both create a payment
    async with lock_manager.lock_for(idem_key):
        if not payload.confirm_new:
            existing = db.query(Payment).filter(
                Payment.payer_vpa == payer_vpa,
                Payment.merchant_id == merchant.id,
                Payment.amount == payload.amount,
                Payment.status.in_(UNRESOLVED_PAYMENT_STATUSES)
            ).order_by(Payment.created_at.desc()).first()
            if existing:
                await _block_duplicate(db, existing)
                response.status_code = status.HTTP_200_OK
                response.headers["Idempotent-Replay"] = "true"
                return existing

        payment = create_mock_payment(
            db=db,
            amount=payload.amount,
            status="SUCCESS" if payload.scenario.lower() == "success" else "PENDING",
            payer_vpa=payer_vpa,
            payer_name=payload.payer_name or "Customer",
            merchant_id=merchant.id
        )

    payment_payload = {
        "payment_id": payment.id,
        "amount": payment.amount,
        "status": payment.status,
        "payer_vpa": payment.payer_vpa,
        "payer_name": payment.payer_name,
        "rrn": payment.rrn,
        "scenario": payload.scenario,
        "created_at": payment.created_at.isoformat()
    }
    record_audit_event(db=db, event_type="PAYMENT_CREATED", actor="customer", payload=payment_payload)
    await broadcast("PAYMENT_CREATED", payment_payload)
    return payment

@router.post("/api/sandbox/retap")
async def sandbox_retap(payload: Optional[RetapRequest] = None, db: Session = Depends(get_db)):
    """Customer taps Pay again for the payment that is still in flight"""
    query = db.query(Payment).filter(Payment.status.in_(UNRESOLVED_PAYMENT_STATUSES))
    if payload and payload.payment_id:
        query = query.filter(Payment.id == payload.payment_id)
    payment = query.order_by(Payment.created_at.desc()).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No payment in flight to retap.")

    idem_key = lock_manager.generate_key(f"{payment.payer_vpa}:{payment.merchant_id}:{payment.amount:.2f}", "pay")
    async with lock_manager.lock_for(idem_key):
        await _block_duplicate(db, payment)
    return {"status": "blocked", "payment_id": payment.id, "message": "Duplicate payment blocked by Idempotency Gate"}

# -------------------------------------------------------------
# 2. BANK STATUS WEBHOOK (resolution ladder)
# -------------------------------------------------------------
@router.post("/api/sandbox/payments/{payment_id}/state")
async def update_sandbox_payment_state(
    payment_id: str,
    payload: PaymentStateUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Simulated bank webhook.
    - SUCCESS: case resolved, receipts issued.
    - DEBITED_NOT_CREDITED / FAILED: refund proposed and run through the 7 gates.
    - Any update on an already-refunded payment raises a reconciliation alert.
    """
    target_status = payload.status.upper()
    if target_status not in ("SUCCESS", "DEBITED_NOT_CREDITED", "FAILED", "REVERSED", "PENDING"):
        raise HTTPException(status_code=400, detail=f"Unsupported bank status '{target_status}'")

    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Payment with id '{payment_id}' not found.")

    previous_status = payment.status
    record_audit_event(db=db, event_type="BANK_STATUS_RECEIVED", actor="bank", payload={
        "payment_id": payment.id, "from": previous_status, "to": target_status
    })

    if previous_status == "REFUNDED":
        await reconcile_late_bank_update(db, payment, target_status)
    elif previous_status == "SUCCESS":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment already settled.")
    elif target_status == "SUCCESS":
        await confirm_payment(db, payment)
    elif target_status in ("DEBITED_NOT_CREDITED", "FAILED"):
        payment.status = target_status
        payment.updated_at = datetime.utcnow()
        db.commit()
        await resolve_bank_failure(db, payment)

    await broadcast("PAYMENT_UPDATED", {
        "payment_id": payment.id,
        "amount": payment.amount,
        "status": payment.status,
        "bank_status": target_status,
        "updated_at": datetime.utcnow().isoformat()
    })
    return {
        "message": f"Bank status {target_status} processed for payment {payment.id}",
        "payment_id": payment.id,
        "status": payment.status
    }

# -------------------------------------------------------------
# 3. MERCHANT APPROVAL (nonce + PIN + merchant channel)
# -------------------------------------------------------------
def _approvable_case(db: Session, case_id: str):
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case '{case_id}' not found.")
    if case.status != "AWAITING_APPROVAL":
        detail = ("Bank has not answered yet; a refund now could pay out twice."
                  if case.status == "OPEN" else f"Case is {case.status}; nothing to approve.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
    merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
    return case, payment, merchant

@router.post("/api/approval/challenge")
def approval_challenge(payload: ChallengeRequest, db: Session = Depends(get_db)):
    """Issues a single-use, 60-second nonce bound to this case, action and amount"""
    case, payment, _ = _approvable_case(db, payload.case_id)
    if pin_limiter.is_locked(case.id):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Approval locked after too many wrong PINs.")
    issued = nonce_store.issue(case.id, "REFUND", payment.amount)
    return {**issued, "case_id": case.id, "action": "REFUND", "amount": payment.amount}

@router.post("/api/approval")
@router.post("/api/sandbox/approval")
async def process_approval(payload: ApprovalRequest, db: Session = Depends(get_db)):
    """
    Merchant approves a held refund. The request must carry a fresh nonce, the
    merchant PIN, and come from a merchant channel; the 7 gates then decide.
    """
    lock_key = lock_manager.generate_key(payload.case_id, "approval")
    if not await lock_manager.acquire(lock_key):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Concurrency Block: Duplicate request detected in-flight.")
    try:
        case, payment, merchant = _approvable_case(db, payload.case_id)
        if pin_limiter.is_locked(case.id):
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Approval locked after too many wrong PINs.")

        approval = {
            "actor": payload.actor,
            "pin_ok": verify_pin(payload.pin, merchant.pin),
            "nonce_status": nonce_store.consume(payload.nonce, case.id, payload.action_type, payment.amount),
            "command": payload.voice_command,
        }
        decision, gates, gate = evaluate_seven_gates(
            payment=payment, merchant=merchant, policy=current_policy(db, merchant),
            recommendation=recommend(payment), approval=approval
        )

        approval_event = {
            "case_id": case.id,
            "actor": payload.actor,
            "voice_command": payload.voice_command,
            "nonce_status": approval["nonce_status"],
            "pin_ok": approval["pin_ok"],
            "decision": decision,
            "blocked_by": gate if decision == "BLOCK" else "",
            "gate_results": gates,
        }
        record_audit_event(db=db, event_type="APPROVAL_PROCESSED", actor=payload.actor, payload=approval_event)
        await publish_gates(f"{case.id} approval", decision, gates, gate, case.id)

        if decision == "ALLOW":
            await broadcast("APPROVAL_PROCESSED", {**approval_event, "status": "EXECUTED"})
            await execute_refund(db, case, payment, gates, approved_by=f"{payload.actor} + PIN")
            return {"case_id": case.id, "status": "EXECUTED", "decision": decision, "gate_evaluations": gates}

        # Rejected: the case stays open for a correct approval, unless the PIN limit is hit
        if not approval["pin_ok"] and payload.actor in ("merchant_voice", "merchant_app"):
            if pin_limiter.record_failure(case.id) >= MAX_PIN_ATTEMPTS:
                await block_case(db, case, payment, "Authority",
                                 {"Authority": {"reason": f"{MAX_PIN_ATTEMPTS} wrong PINs: approval locked"}})
        await broadcast("APPROVAL_PROCESSED", {**approval_event, "status": "REJECTED"})
        schedule_announcement([("merchant", "approval_rejected")], amount=payment.amount,
                              merchant_name=merchant.business_name, case_id=case.id,
                              blocked=True, reason=f"Approval rejected by {gate}")
        return {"case_id": case.id, "status": "REJECTED", "decision": decision,
                "blocked_by_gate": gate, "gate_evaluations": gates}
    finally:
        lock_manager.release(lock_key)

# -------------------------------------------------------------
# 4. GRAPH FRAUD DETECTION ENDPOINT
# -------------------------------------------------------------
@router.get("/api/fraud/graph")
def get_fraud_graph():
    """
    Returns the NetworkX fraud graph topology (nodes, edges, and flagged fraud rings) as JSON.
    """
    return fraud_detector.to_dict()

# -------------------------------------------------------------
# 5. SIMULATE FRAUD RING (Helper to test multi-merchant collusion)
# -------------------------------------------------------------
@router.post("/api/sandbox/simulate-fraud-ring")
async def simulate_fraud_ring(
    customer_vpa: str = "attacker@upi",
    db: Session = Depends(get_db)
):
    """
    Simulates a collusive fraud ring: stuck payments for one customer VPA across
    4 merchants within seconds. The customer is flagged and their refunds are
    routed to manual review by the Identity gate.
    """
    merchants = [
        "ravi.chai@upi",
        "anand.sweets@upi",
        "priya.flowers@upi",
        "kumar.general@upi"
    ]

    opened_cases = []
    for idx, mVPA in enumerate(merchants):
        payment = create_mock_payment(
            db=db,
            amount=50.0 + (idx * 10),
            status="FAILED",
            payer_vpa=customer_vpa,
            payer_name="Collusive Attacker"
        )
        case = Case(
            id=f"PV-FRAUD-{idx + 1}-{payment.id[-4:]}",
            merchant_id=payment.merchant_id,
            payment_id=payment.id,
            status="BLOCKED",
            trigger_reason="Collusion simulation",
            created_at=datetime.utcnow()
        )
        db.add(case)
        db.commit()

        is_new_fraud, fraud_data = fraud_detector.add_stuck_payment_incident(
            customer_vpa=customer_vpa,
            merchant_vpa=mVPA,
            case_id=case.id,
            timestamp=datetime.utcnow()
        )
        opened_cases.append({"case_id": case.id, "merchant": mVPA, "flagged": is_new_fraud})

        if is_new_fraud and fraud_data:
            record_audit_event(db=db, event_type="FRAUD_RING_DETECTED", actor="system", payload=fraud_data)
            await broadcast("FRAUD_RING_DETECTED", fraud_data)

    return {
        "message": f"Simulated 4 stuck payment incidents across 4 distinct merchants for {customer_vpa}",
        "customer_vpa": customer_vpa,
        "is_flagged_as_fraud_ring": fraud_detector.is_flagged(customer_vpa),
        "incidents": opened_cases,
        "graph_summary": fraud_detector.to_dict()["summary"]
    }
