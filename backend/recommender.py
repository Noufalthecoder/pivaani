from typing import Dict, Any
from models import Payment

def recommend(payment: Payment) -> Dict[str, Any]:
    """
    The recommender proposes; the 7-gate firewall decides. Its output is treated
    as untrusted input, so swapping in an LLM here cannot widen what executes.

    Returns {"action", "refund_amount", "confidence", "reason", "source"}.
    """
    status = (payment.status or "").upper()
    base = {"refund_amount": float(payment.amount), "source": "rules-v1"}

    if status == "DEBITED_NOT_CREDITED":
        return {**base, "action": "refund", "confidence": 0.92,
                "reason": "Bank confirmed debit without merchant credit"}
    if status == "FAILED":
        return {**base, "action": "refund", "confidence": 0.95,
                "reason": "Bank marked the payment failed after debit"}
    if status == "PENDING":
        return {**base, "action": "wait", "confidence": 0.90,
                "reason": "Bank has not answered yet; it may still settle"}
    return {**base, "action": "none", "refund_amount": 0.0, "confidence": 0.99,
            "reason": f"No action needed for status {status}"}
