from typing import Dict, Any, Optional, Tuple
from fraud_graph import fraud_detector
from models import Payment, Merchant, Policy

# Absolute ceiling for any refund, whatever the dial or approval says
HARD_REFUND_CEILING = 5000.0

# Channels allowed to issue or approve money actions
MERCHANT_CHANNELS = {"merchant_voice", "merchant_app"}
TRUSTED_ACTORS = {"system"} | MERCHANT_CHANNELS

# A refund is only safe once the bank has said the money will not reach the merchant
REFUNDABLE_STATUSES = {"DEBITED_NOT_CREDITED", "FAILED"}

# Gate statuses that hold an action (need a human or the bank) rather than block it
HOLD_STATUSES = {"REVIEW", "WAIT", "PENDING_APPROVAL"}

GATE_ORDER = ["Authority", "Amount", "Confidence", "Identity", "Idempotency", "Reversibility", "Approval"]

def evaluate_seven_gates(
    payment: Payment,
    merchant: Optional[Merchant],
    policy: Policy,
    recommendation: Dict[str, Any],
    actor: str = "system",
    approval: Optional[Dict[str, Any]] = None,
    retap_collision: bool = False
) -> Tuple[str, Dict[str, Any], str]:
    """
    Runs a proposed money action through 7 deterministic gates.

    recommendation: untrusted proposal {"action", "refund_amount", "confidence", ...}
    actor:          channel that issued the action ("system", "merchant_voice", "customer_note", ...)
    approval:       a merchant approval attempt {"actor", "pin_ok", "nonce_status", "command"}, if any

    Returns (decision, gates, gate) where decision is one of
      ALLOW          - execute now
      NEEDS_APPROVAL - wait for merchant voice approval + PIN (gate = what triggered it)
      HOLD           - wait for the bank (the payment may still settle)
      BLOCK          - never execute (gate = first failed gate)
    """
    gates: Dict[str, Dict[str, str]] = {}
    refund_amount = float(recommendation.get("refund_amount", payment.amount) or 0)

    # 1. Authority: who is asking, and who is approving
    if not merchant or not merchant.vpa:
        gates["Authority"] = {"status": "FAILED", "reason": "Unverified merchant origin"}
    elif actor not in TRUSTED_ACTORS:
        gates["Authority"] = {"status": "FAILED", "reason": f"'{actor}' is not allowed to issue money actions"}
    elif approval and approval.get("actor") not in MERCHANT_CHANNELS:
        gates["Authority"] = {"status": "FAILED", "reason": f"Only the merchant can approve refunds (got {approval.get('actor')})"}
    elif approval and not approval.get("pin_ok"):
        gates["Authority"] = {"status": "FAILED", "reason": "Merchant PIN incorrect"}
    else:
        gates["Authority"] = {"status": "PASSED", "reason": f"Verified channel: {approval['actor'] if approval else actor}"}

    # 2. Amount: never more than was paid, never above the hard ceiling, auto only within the dial
    if refund_amount > float(payment.amount):
        gates["Amount"] = {"status": "FAILED", "reason": f"Refund ₹{refund_amount:g} exceeds original payment ₹{payment.amount:g}"}
    elif refund_amount > HARD_REFUND_CEILING:
        gates["Amount"] = {"status": "FAILED", "reason": f"₹{refund_amount:g} exceeds hard ceiling ₹{HARD_REFUND_CEILING:g}"}
    elif refund_amount > policy.auto_refund_max:
        gates["Amount"] = {"status": "REVIEW", "reason": f"₹{refund_amount:g} above auto-refund limit ₹{policy.auto_refund_max:g}"}
    else:
        gates["Amount"] = {"status": "PASSED", "reason": f"₹{refund_amount:g} within auto-refund limit ₹{policy.auto_refund_max:g}"}

    # 3. Confidence: the recommender must be sure enough for this dial
    confidence = float(recommendation.get("confidence", 0))
    if confidence >= policy.min_confidence:
        gates["Confidence"] = {"status": "PASSED", "reason": f"Recommender '{recommendation.get('action')}' at {confidence:.2f} ≥ {policy.min_confidence:.2f}"}
    else:
        gates["Confidence"] = {"status": "FAILED", "reason": f"Recommender confidence {confidence:.2f} < {policy.min_confidence:.2f}"}

    # 4. Identity: fraud-ring links route to manual review instead of punishing the customer
    if fraud_detector.is_flagged(payment.payer_vpa):
        gates["Identity"] = {"status": "REVIEW", "reason": f"{payment.payer_vpa} linked to a fraud-ring pattern: manual review"}
    else:
        gates["Identity"] = {"status": "PASSED", "reason": f"Payer identity verified: {payment.payer_vpa}"}

    # 5. Idempotency: no duplicate payments, no replayed approvals
    if retap_collision:
        gates["Idempotency"] = {"status": "FAILED", "reason": "Duplicate payment for the same payer, merchant and amount"}
    elif approval and approval.get("nonce_status") != "fresh":
        gates["Idempotency"] = {"status": "FAILED", "reason": f"Approval nonce {approval.get('nonce_status')}: replay rejected"}
    else:
        gates["Idempotency"] = {"status": "PASSED", "reason": "Single-use action, no duplicates in flight"}

    # 6. Reversibility: only refund money the bank has confirmed will not settle
    status = (payment.status or "").upper()
    if status in REFUNDABLE_STATUSES:
        gates["Reversibility"] = {"status": "PASSED", "reason": f"Bank status {status}: safe to refund"}
    elif status == "PENDING":
        gates["Reversibility"] = {"status": "WAIT", "reason": "Bank may still settle: refund on hold"}
    elif status == "SUCCESS":
        gates["Reversibility"] = {"status": "FAILED", "reason": "Merchant already credited: no refund due"}
    elif status == "REFUNDED":
        gates["Reversibility"] = {"status": "FAILED", "reason": "Already refunded"}
    else:
        gates["Reversibility"] = {"status": "FAILED", "reason": f"Unknown bank status {status}"}

    # 7. Approval: merchant voice + PIN when the dial or another gate asks for it
    needs_human = any(g["status"] == "REVIEW" for g in gates.values()) or policy.auto_refund_max <= 0
    if approval:
        approval_ok = gates["Authority"]["status"] == "PASSED" and gates["Idempotency"]["status"] == "PASSED"
        gates["Approval"] = (
            {"status": "PASSED", "reason": f"Merchant approved with PIN: \"{approval.get('command') or 'approve'}\""}
            if approval_ok else
            {"status": "FAILED", "reason": "Approval rejected"}
        )
    elif needs_human:
        gates["Approval"] = {"status": "PENDING_APPROVAL", "reason": "Needs merchant voice approval + PIN"}
    else:
        gates["Approval"] = {"status": "AUTO_APPROVED", "reason": f"Auto-approved within the {policy.dial_level} dial"}

    # Decision: any failure blocks; otherwise wait for the bank, then for the merchant
    for name in GATE_ORDER:
        if gates[name]["status"] == "FAILED":
            return "BLOCK", gates, name
    if gates["Reversibility"]["status"] == "WAIT":
        return "HOLD", gates, "Reversibility"
    if gates["Approval"]["status"] == "PENDING_APPROVAL":
        trigger = next((n for n in GATE_ORDER if gates[n]["status"] == "REVIEW"), "Approval")
        return "NEEDS_APPROVAL", gates, trigger
    return "ALLOW", gates, ""
