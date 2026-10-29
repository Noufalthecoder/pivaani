from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db import get_db
from models import Payment
from sandbox import create_mock_payment, update_payment_status
from audit import record_audit_event
from events import broadcast
import schemas

router = APIRouter(prefix="/api/sandbox", tags=["Sandbox Scenarios"])

# Request models
class SandboxPayRequest(BaseModel):
    amount: float = Field(default=40.0, description="Amount in INR")
    scenario: str = Field(default="pending", description="Scenario type: pending, success, timeout, duplicate")
    payer_vpa: Optional[str] = "customer@upi"
    payer_name: Optional[str] = "Customer"

class PaymentStateUpdateRequest(BaseModel):
    status: str = Field(..., description="Target status: SUCCESS, PENDING, DEBITED_NOT_CREDITED, FAILED, REFUNDED")

class RetapRequest(BaseModel):
    payment_id: Optional[str] = None
    customer_vpa: Optional[str] = "customer@upi"

@router.post("/pay", response_model=schemas.PaymentOut, status_code=status.HTTP_201_CREATED)
async def sandbox_pay(payload: SandboxPayRequest, db: Session = Depends(get_db)):
    """
    Simulates a customer initiating a UPI payment at Ravi's Chai Stall.
    Creates a Payment record, writes to the audit chain, and broadcasts 'PAYMENT_CREATED'.
    """
    # Determine initial status based on scenario
    scenario_lower = payload.scenario.lower()
    initial_status = "SUCCESS" if scenario_lower == "success" else "PENDING"

    payment = create_mock_payment(
        db=db,
        amount=payload.amount,
        status=initial_status,
        payer_vpa=payload.payer_vpa or "customer@upi",
        payer_name=payload.payer_name or "Customer"
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

    # 1. Record cryptographic audit event
    record_audit_event(
        db=db,
        event_type="PAYMENT_CREATED",
        actor="customer",
        payload=payment_payload
    )

    # 2. Broadcast WebSocket event to Soundbox and Customer Phone
    await broadcast("PAYMENT_CREATED", payment_payload)

    return payment

@router.post("/payments/{payment_id}/state")
async def update_sandbox_payment_state(
    payment_id: str,
    payload: PaymentStateUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Updates a payment's status (e.g. to SUCCESS or DEBITED_NOT_CREDITED).
    If changed to SUCCESS, automatically resolves any active Case attached to it.
    Broadcasts 'PAYMENT_UPDATED'.
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

    # 1. Record audit event
    record_audit_event(
        db=db,
        event_type="PAYMENT_UPDATED",
        actor="system",
        payload=audit_payload
    )

    # 2. Broadcast WebSocket event
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

@router.post("/retap")
async def sandbox_retap(payload: Optional[RetapRequest] = None, db: Session = Depends(get_db)):
    """
    Simulates the customer re-tapping their phone or clicking 'Pay' again,
    exercising the Idempotency Gate. Broadcasts 'RETAP_DETECTED'.
    """
    customer_vpa = payload.customer_vpa if payload else "customer@upi"
    payment_id = payload.payment_id if payload else None

    event_payload = {
        "message": "Customer attempted re-tap / second payment attempt",
        "customer_vpa": customer_vpa,
        "payment_id": payment_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    # 1. Record audit event
    record_audit_event(
        db=db,
        event_type="RETAP_DETECTED",
        actor="customer",
        payload=event_payload
    )

    # 2. Broadcast WebSocket event
    await broadcast("RETAP_DETECTED", event_payload)

    return {
        "status": "success",
        "message": "Retap simulated successfully",
        "details": event_payload
    }

