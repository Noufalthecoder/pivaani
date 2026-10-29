import random
import uuid
from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from models import Payment, Case, Merchant
from config import settings

def generate_rrn() -> str:
    """Generates a standard 12-digit Indian UPI Retrieval Reference Number (RRN)"""
    return f"43{random.randint(1000000000, 9999999999)}"

def create_mock_payment(
    db: Session,
    amount: float = 40.0,
    status: str = "PENDING",
    payer_vpa: str = "customer@upi",
    payer_name: str = "Customer",
    merchant_id: Optional[int] = None
) -> Payment:
    """
    Creates a new mock UPI payment in the database.
    Supported statuses: 'PENDING', 'SUCCESS', 'DEBITED_NOT_CREDITED'
    """
    if merchant_id is None:
        merchant = db.query(Merchant).filter(Merchant.name == settings.DEFAULT_MERCHANT_NAME).first()
        merchant_id = merchant.id if merchant else 1

    payment_id = f"PAY_{uuid.uuid4().hex[:10].upper()}"
    rrn = generate_rrn()

    payment = Payment(
        id=payment_id,
        merchant_id=merchant_id,
        payer_vpa=payer_vpa,
        payer_name=payer_name,
        amount=amount,
        currency="INR",
        status=status.upper(),
        rrn=rrn,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

def update_payment_status(
    db: Session,
    payment_id: str,
    new_status: str
) -> Tuple[Optional[Payment], List[Case]]:
    """
    Updates the payment status (e.g. to SUCCESS or DEBITED_NOT_CREDITED).
    If changed to SUCCESS, automatically resolves any active Case attached to it.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        return None, []

    payment.status = new_status.upper()
    payment.updated_at = datetime.utcnow()

    closed_cases: List[Case] = []
    if payment.status == "SUCCESS":
        # Find any active cases attached to this payment
        active_cases = db.query(Case).filter(
            Case.payment_id == payment.id,
            Case.status.in_(["OPEN", "EVALUATING"])
        ).all()

        for case in active_cases:
            case.status = "RESOLVED"
            case.resolution = "Payment successfully confirmed by bank webhook"
            case.updated_at = datetime.utcnow()
            closed_cases.append(case)

    db.commit()
    db.refresh(payment)
    for c in closed_cases:
        db.refresh(c)

    return payment, closed_cases

