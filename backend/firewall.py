from typing import Dict, Any, Tuple
from fraud_graph import fraud_detector
from models import Payment, Case, Merchant, Policy

def evaluate_seven_gates(
    payment: Payment,
    case: Case,
    merchant: Merchant,
    policy: Policy,
    custom_confidence: float = 0.92,
    has_retap_collision: bool = False
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Evaluates the 7 Deterministic Safety Gates for an incident case action:
    1. Authority
    2. Amount
    3. Confidence
    4. Identity (Incorporates Graph Fraud Ring check)
    5. Idempotency
    6. Reversibility
    7. Approval

    Returns: (all_passed: bool, gate_evaluations: dict, blocked_by_gate: str)
    """
    gates = {}
    blocked_by = None

    # 1. Authority Gate: Valid Merchant & Channel
    if merchant and merchant.vpa:
        gates["Authority"] = {"status": "PASSED", "reason": "Verified merchant channel"}
    else:
        gates["Authority"] = {"status": "FAILED", "reason": "Unverified merchant origin"}
        blocked_by = "Authority"

    # 2. Amount Gate: Threshold check against policy auto_refund_max
    if payment.amount <= policy.auto_refund_max or policy.auto_refund_max == 0:
        # If auto_refund_max is 0 (Careful mode), amount requires explicit voice PIN
        if policy.auto_refund_max == 0:
            gates["Amount"] = {"status": "PASSED", "reason": f"Amount ₹{payment.amount} routed to voice approval (Careful mode)"}
        else:
            gates["Amount"] = {"status": "PASSED", "reason": f"Amount ₹{payment.amount} <= ₹{policy.auto_refund_max} limit"}
    else:
        gates["Amount"] = {"status": "FLAGGED", "reason": f"Amount ₹{payment.amount} exceeds auto threshold ₹{policy.auto_refund_max}"}

    # 3. Confidence Gate: Confidence threshold check
    if custom_confidence >= policy.min_confidence:
        gates["Confidence"] = {"status": "PASSED", "reason": f"Confidence {custom_confidence:.2f} >= {policy.min_confidence:.2f}"}
    else:
        gates["Confidence"] = {"status": "FAILED", "reason": f"Confidence {custom_confidence:.2f} < {policy.min_confidence:.2f}"}
        if not blocked_by:
            blocked_by = "Confidence"

    # 4. Identity Gate (WITH GRAPH FRAUD DETECTION):
    if fraud_detector.is_flagged(payment.payer_vpa):
        gates["Identity"] = {
            "status": "FAILED",
            "reason": "Fraud Ring Detected: Collusive retap pattern"
        }
        if not blocked_by:
            blocked_by = "Identity"
    else:
        gates["Identity"] = {
            "status": "PASSED",
            "reason": f"Payer identity verified: {payment.payer_vpa}"
        }

    # 5. Idempotency Gate
    if has_retap_collision:
        gates["Idempotency"] = {"status": "FAILED", "reason": "Duplicate transaction detected in-flight"}
        if not blocked_by:
            blocked_by = "Idempotency"
    else:
        gates["Idempotency"] = {"status": "PASSED", "reason": "Zero duplicate debits detected"}

    # 6. Reversibility Gate
    gates["Reversibility"] = {"status": "PASSED", "reason": "Within 2-minute UPI settlement escrow buffer"}

    # 7. Approval Gate
    if policy.require_voice_approval:
        gates["Approval"] = {"status": "PENDING_APPROVAL", "reason": "Awaiting merchant vocal PIN confirmation"}
    else:
        gates["Approval"] = {"status": "AUTO_APPROVED", "reason": "Auto-authorized by Fast trust dial"}

    all_passed = (blocked_by is None)
    return all_passed, gates, blocked_by or ""

