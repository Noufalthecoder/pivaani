import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from models import Payment, Case, Merchant, Policy, Action
from sandbox import create_mock_payment, update_payment_status
from audit import record_audit_event
from events import broadcast
from locks import lock_manager
from fraud_graph import fraud_detector
from firewall import evaluate_seven_gates
import schemas

router = APIRouter(tags=["Sandbox Scenarios & Fraud Protection"])

# Request models
class SandboxPayRequest(BaseModel):
    amount: float = Field(default=40.0, description="Amount in INR")
    scenario: str = Field(default="pending", description="Scenario type: pending, success, timeout, duplicate")
    payer_vpa: Optional[str] = "customer@upi"
    payer_name: Optional[str] = "Customer"
    merchant_vpa: Optional[str] = None

class PaymentStateUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: SUCCESS, PENDING, DEBITED_NOT_CREDITED, FAILED, REFUNDED")

class RetapRequest(BaseModel):
    payment_id: Optional[str] = None
    customer_vpa: Optional[str] = "customer@upi"

class ApprovalRequest(BaseModel):
    case_id: str = Field(..., description="Incident Case ID e.g. PV-1001")
    pin: Optional[str] = Field(default="4321", description="Merchant 4-digit PIN")
    voice_command: Optional[str] = Field(default="Approve refund", description="Voice command transcript")
    action_type: Optional[str] = Field(default="REFUND", description="Target action type")

# -------------------------------------------------------------
# 1. PAY ENDPOINT
# -------------------------------------------------------------
@router.post("/api/sandbox/pay", response_model=schemas.PaymentOut, status_code=status.HTTP_201_CREATED)
async def sandbox_pay(payload: SandboxPayRequest, db: Session = Depends(get_db)):
    """
    Simulates customer payment initiation.
    """
    scenario_lower = payload.scenario.lower()
    initial_status = "SUCCESS" if scenario_lower == "success" else "PENDING"

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
                pin="4321"
            )
            db.add(merchant)
            db.commit()
            db.refresh(merchant)

    payment = create_mock_payment(
        db=db,
        amount=payload.amount,
        status=initial_status,
        payer_vpa=payload.payer_vpa or "customer@upi",
        payer_name=payload.payer_name or "Customer",
        merchant_id=merchant.id if merchant else None
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

    record_audit_event(
        db=db,
        event_type="PAYMENT_CREATED",
        actor="customer",
        payload=payment_payload
    )

    await broadcast("PAYMENT_CREATED", payment_payload)
    return payment

# -------------------------------------------------------------
# 2. STATE UPDATE (Bank Webhook)
# -------------------------------------------------------------
@router.post("/api/sandbox/payments/{payment_id}/state")
async def update_sandbox_payment_state(
    payment_id: str,
    payload: PaymentStateUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates payment status (e.g. to SUCCESS). If SUCCESS, resolves active Case.
    """
    target_status = payload.status.upper()
    payment, closed_cases = update_payment_status(
        db=db,
        payment_id=payment_id,
        new_status=target_status
    )

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with id '{payment_id}' not found."
        )

    closed_case_ids = [c.id for c in closed_cases]

    audit_payload = {
        "payment_id": payment.id,
        "new_status": payment.status,
        "cases_closed": closed_case_ids,
        "updated_at": payment.updated_at.isoformat()
    }

    record_audit_event(
        db=db,
        event_type="PAYMENT_UPDATED",
        actor="system",
        payload=audit_payload
    )

    await broadcast("PAYMENT_UPDATED", {
        "payment_id": payment.id,
        "amount": payment.amount,
        "status": payment.status,
        "cases_closed": closed_case_ids,
        "case_closed": len(closed_case_ids) > 0,
        "updated_at": payment.updated_at.isoformat()
    })

    return {
        "message": f"Payment {payment.id} status updated to {payment.status}",
        "payment_id": payment.id,
        "status": payment.status,
        "cases_closed": closed_case_ids
    }

# -------------------------------------------------------------
# 3. RETAP WITH ASYNC DISTRIBUTED LOCK (Concurrency Protection)
# -------------------------------------------------------------
@router.post("/api/sandbox/retap")
async def sandbox_retap(payload: Optional[RetapRequest] = None, db: Session = Depends(get_db)):
    """
    Simulates customer retapping phone.
    Protected by Async Distributed Idempotency Lock:
    If a duplicate request arrives in-flight, immediately returns HTTP 429 Too Many Requests.
    """
    customer_vpa = payload.customer_vpa if payload else "customer@upi"
    payment_id = payload.payment_id if payload else "latest"
    lock_key = lock_manager.generate_key(f"{customer_vpa}:{payment_id}", "retap")

    # STEP 1: Attempt to acquire the in-flight distributed lock
    acquired = await lock_manager.acquire(lock_key)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Concurrency Block: Duplicate request detected in-flight."
        )

    try:
        # Simulate in-flight validation window (prevents sub-millisecond race conditions)
        await asyncio.sleep(0.2)

        event_payload = {
            "message": "Customer attempted re-tap / second payment attempt",
            "customer_vpa": customer_vpa,
            "payment_id": payment_id,
            "lock_key": lock_key[:12],
            "timestamp": datetime.utcnow().isoformat()
        }

        record_audit_event(
            db=db,
            event_type="RETAP_DETECTED",
            actor="customer",
            payload=event_payload
        )

        await broadcast("RETAP_DETECTED", event_payload)

        return {
            "status": "success",
            "message": "Retap simulated successfully",
            "details": event_payload
        }
    finally:
        # STEP 2: Release lock once operation is settled
        lock_manager.release(lock_key)

# -------------------------------------------------------------
# 4. APPROVAL WITH ASYNC DISTRIBUTED LOCK & 7-GATE FIREWALL
# -------------------------------------------------------------
@router.post("/api/approval")
@router.post("/api/sandbox/approval")
async def process_approval(payload: ApprovalRequest, db: Session = Depends(get_db)):
    """
    Processes merchant voice PIN approval for an active case.
    Protected by Async Distributed Idempotency Lock:
    If duplicate approval request arrives in-flight, immediately returns HTTP 429.
    Evaluates the 7-Gate Safety Firewall (including Graph Fraud Detector in Identity Gate).
    """
    lock_key = lock_manager.generate_key(payload.case_id, "approval")

    # STEP 1: Acquire distributed idempotency lock
    acquired = await lock_manager.acquire(lock_key)
    if not acquired:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Concurrency Block: Duplicate request detected in-flight."
        )

    try:
        # Simulate short processing window for lock contention testing
        await asyncio.sleep(0.2)

        case = db.query(Case).filter(Case.id == payload.case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail=f"Case '{payload.case_id}' not found.")

        payment = db.query(Payment).filter(Payment.id == case.payment_id).first()
        merchant = db.query(Merchant).filter(Merchant.id == case.merchant_id).first()
        policy = db.query(Policy).filter(
            Policy.merchant_id == merchant.id,
            Policy.dial_level == merchant.trust_dial
        ).first()

        if not policy:
            policy = Policy(
                merchant_id=merchant.id,
                dial_level="balanced",
                auto_refund_max=200.0,
                min_confidence=0.80,
                require_voice_approval=True,
                require_pin=False
            )

        # Evaluate 7 Deterministic Safety Gates (Identity gate checks Graph Fraud)
        passed, gate_results, blocked_by = evaluate_seven_gates(
            payment=payment,
            case=case,
            merchant=merchant,
            policy=policy
        )

        action_status = "EXECUTED" if passed else "BLOCKED"

        action = Action(
            id=f"ACT_{payload.case_id}_{payload.action_type}",
            case_id=case.id,
            action_type=payload.action_type,
            status=action_status,
            gate_results=str(gate_results),
            blocked_by_gate=blocked_by,
            executed_at=datetime.utcnow() if passed else None,
            created_at=datetime.utcnow()
        )
        db.add(action)

        if passed:
            case.status = "RESOLVED"
            case.resolution = f"Approved and executed: {payload.action_type}"
        else:
            case.status = "BLOCKED"
            case.resolution = f"Blocked by {blocked_by}: {gate_results.get(blocked_by, {}).get('reason')}"

        db.commit()

        approval_event = {
            "case_id": case.id,
            "action_id": action.id,
            "action_type": payload.action_type,
            "status": action.status,
            "blocked_by": blocked_by,
            "gate_results": gate_results,
            "timestamp": datetime.utcnow().isoformat()
        }

        record_audit_event(
            db=db,
            event_type="APPROVAL_PROCESSED",
            actor="merchant",
            payload=approval_event
        )

        await broadcast("APPROVAL_PROCESSED", approval_event)

        return {
            "case_id": case.id,
            "status": action.status,
            "blocked_by_gate": blocked_by,
            "gate_evaluations": gate_results,
            "message": f"Action {action_status}: {case.resolution}"
        }
    finally:
        # STEP 2: Release distributed lock
        lock_manager.release(lock_key)

# -------------------------------------------------------------
# 5. GRAPH FRAUD DETECTION ENDPOINT
# -------------------------------------------------------------
@router.get("/api/fraud/graph")
def get_fraud_graph():
    """
    Returns the NetworkX fraud graph topology (nodes, edges, and flagged fraud rings) as JSON.
    """
    return fraud_detector.to_dict()

# -------------------------------------------------------------
# 6. SIMULATE FRAUD RING (Helper to test multi-merchant collusion)
# -------------------------------------------------------------
@router.post("/api/sandbox/simulate-fraud-ring")
async def simulate_fraud_ring(
    customer_vpa: str = "attacker@upi",
    db: Session = Depends(get_db)
):
    """
    Simulates a collusive fraud ring:
    Creates stuck payments for a single Customer VPA across 4 distinct merchants within seconds.
    Triggers the Fraud Ring Detector (>3 merchants in 5m), logs FRAUD_RING_DETECTED audit event,
    and flags the customer in the Identity Gate.
    """
    merchants = [
        "ravi.chai@upi",
        "anand.sweets@upi",
        "priya.flowers@upi",
        "kumar.general@upi"
    ]

    opened_cases = []
    for idx, mVPA in enumerate(merchants):
        # Create payment
        payment = create_mock_payment(
            db=db,
            amount=50.0 + (idx * 10),
            status="PENDING",
            payer_vpa=customer_vpa,
            payer_name="Collusive Attacker"
        )
        # Directly open stuck case
        case = Case(
            id=f"PV-FRAUD-{idx + 1}",
            merchant_id=payment.merchant_id,
            payment_id=payment.id,
            status="OPEN",
            trigger_reason="Payment stuck > 2s (Collusion Simulation)",
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
            record_audit_event(
                db=db,
                event_type="FRAUD_RING_DETECTED",
                actor="system",
                payload=fraud_data
            )
            await broadcast("FRAUD_RING_DETECTED", fraud_data)

    return {
        "message": f"Simulated 4 stuck payment incidents across 4 distinct merchants for {customer_vpa}",
        "customer_vpa": customer_vpa,
        "is_flagged_as_fraud_ring": fraud_detector.is_flagged(customer_vpa),
        "incidents": opened_cases,
        "graph_summary": fraud_detector.to_dict()["summary"]
    }
