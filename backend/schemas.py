from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

# ----------------- Merchant & Policy ----------------- #
class PolicyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dial_level: str
    auto_refund_max: float
    min_confidence: float
    require_voice_approval: bool
    require_pin: bool
    is_active: bool

class MerchantBase(BaseModel):
    name: str
    business_name: str
    vpa: str
    phone: Optional[str] = None
    trust_dial: str
    pin: str

class MerchantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    business_name: str
    vpa: str
    phone: Optional[str] = None
    trust_dial: str
    pin: str
    created_at: datetime
    policies: List[PolicyOut] = []

class MerchantUpdateDial(BaseModel):
    trust_dial: str

# ----------------- Payments ----------------- #
class PaymentBase(BaseModel):
    id: str
    payer_vpa: str
    payer_name: str
    amount: float
    currency: str = "INR"
    status: str
    rrn: Optional[str] = None

class PaymentCreate(BaseModel):
    amount: float
    payer_vpa: Optional[str] = "customer@upi"
    payer_name: Optional[str] = "Customer"
    rrn: Optional[str] = None

class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    merchant_id: int
    payer_vpa: str
    payer_name: str
    amount: float
    currency: str
    status: str
    rrn: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# ----------------- Cases & Actions ----------------- #
class ActionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    action_type: str
    status: str
    gate_results: Optional[str] = None
    blocked_by_gate: Optional[str] = None
    executed_at: Optional[datetime] = None
    created_at: datetime

class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    merchant_id: int
    payment_id: Optional[str] = None
    status: str
    trigger_reason: str
    recommended_action: Optional[str] = None
    resolution: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    actions: List[ActionOut] = []

# ----------------- Audit Events ----------------- #
class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    prev_hash: str
    event_hash: str
    event_type: str
    actor: str
    payload: str
    timestamp: datetime
    created_at: datetime

class ChainVerificationOut(BaseModel):
    valid: bool
    total_events: int
    genesis_hash: Optional[str] = None
    latest_hash: Optional[str] = None
    broken_at_id: Optional[int] = None
    reason: Optional[str] = None
    message: Optional[str] = None

# ----------------- Responses ----------------- #
class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: str
    version: str

class ResetResponse(BaseModel):
    message: str
    timestamp: str
    merchant: MerchantOut

class StateResponse(BaseModel):
    merchant: Optional[MerchantOut] = None
    payments: List[PaymentOut] = []
    active_cases: List[CaseOut] = []
    latest_audit: Optional[AuditEventOut] = None
    active_dial: str
    server_time: str

