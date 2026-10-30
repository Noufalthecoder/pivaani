import hashlib
import hmac
import secrets
import time
from typing import Dict, Optional

# ----------------- Merchant PIN hashing ----------------- #
PIN_HASH_PREFIX = "pbkdf2$"
PIN_HASH_ITERATIONS = 100_000

def hash_pin(pin: str) -> str:
    """Salted PBKDF2-SHA256 hash; the plain PIN is never stored or returned by the API"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt), PIN_HASH_ITERATIONS).hex()
    return f"{PIN_HASH_PREFIX}{salt}${digest}"

def is_pin_hashed(stored: str) -> bool:
    return bool(stored) and stored.startswith(PIN_HASH_PREFIX)

def verify_pin(pin: Optional[str], stored: str) -> bool:
    """Constant-time check of a candidate PIN against the stored hash"""
    if not pin or not is_pin_hashed(stored):
        return False
    try:
        salt, digest = stored[len(PIN_HASH_PREFIX):].split("$", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), bytes.fromhex(salt), PIN_HASH_ITERATIONS).hex()
    return hmac.compare_digest(candidate, digest)

# ----------------- Single-use approval nonces ----------------- #
NONCE_TTL_SECONDS = 60

class ApprovalNonceStore:
    """
    Every refund approval must carry a nonce bound to (case, action, amount).
    A nonce is consumed on first use, so replaying an old approval fails the
    Idempotency gate. Consumed nonces are remembered until well past expiry.
    """

    def __init__(self):
        self._nonces: Dict[str, Dict] = {}

    def issue(self, case_id: str, action: str, amount: float) -> Dict:
        self._purge()
        nonce = secrets.token_urlsafe(16)
        expires_at = time.time() + NONCE_TTL_SECONDS
        self._nonces[nonce] = {
            "case_id": case_id,
            "action": action.upper(),
            "amount": float(amount),
            "expires_at": expires_at,
            "used": False,
        }
        return {"nonce": nonce, "expires_in": NONCE_TTL_SECONDS}

    def consume(self, nonce: Optional[str], case_id: str, action: str, amount: float) -> str:
        """Returns 'fresh' exactly once for a valid nonce; otherwise why it was rejected"""
        record = self._nonces.get(nonce or "")
        if not record:
            return "invalid"
        if record["used"]:
            return "replayed"
        if (record["case_id"], record["action"], record["amount"]) != (case_id, action.upper(), float(amount)):
            return "mismatched"
        record["used"] = True  # single-use even if the approval is then rejected
        if time.time() > record["expires_at"]:
            return "expired"
        return "fresh"

    def _purge(self):
        cutoff = time.time() - 10 * NONCE_TTL_SECONDS
        for key in [k for k, v in self._nonces.items() if v["expires_at"] < cutoff]:
            del self._nonces[key]

    def reset(self):
        self._nonces.clear()

nonce_store = ApprovalNonceStore()

# ----------------- Wrong-PIN lockout ----------------- #
MAX_PIN_ATTEMPTS = 3

class PinAttemptLimiter:
    """Locks refund approval for a case after MAX_PIN_ATTEMPTS wrong PINs"""

    def __init__(self):
        self._failures: Dict[str, int] = {}

    def record_failure(self, case_id: str) -> int:
        self._failures[case_id] = self._failures.get(case_id, 0) + 1
        return self._failures[case_id]

    def is_locked(self, case_id: str) -> bool:
        return self._failures.get(case_id, 0) >= MAX_PIN_ATTEMPTS

    def reset(self):
        self._failures.clear()

pin_limiter = PinAttemptLimiter()
