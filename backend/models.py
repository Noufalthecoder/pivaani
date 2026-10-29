from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    business_name = Column(String(200), nullable=False)
    vpa = Column(String(100), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    trust_dial = Column(String(20), default="balanced", nullable=False)  # careful, balanced, fast
    pin = Column(String(10), default="4321", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    payments = relationship("Payment", back_populates="merchant", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="merchant", cascade="all, delete-orphan")
    policies = relationship("Policy", back_populates="merchant", cascade="all, delete-orphan")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    dial_level = Column(String(20), nullable=False)  # careful, balanced, fast
    auto_refund_max = Column(Float, default=200.0, nullable=False)
    min_confidence = Column(Float, default=0.80, nullable=False)
    require_voice_approval = Column(Boolean, default=True, nullable=False)
    require_pin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    merchant = relationship("Merchant", back_populates="policies")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(64), primary_key=True, index=True)
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    payer_vpa = Column(String(100), nullable=False)
    payer_name = Column(String(100), default="Customer", nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    status = Column(String(30), default="PENDING", nullable=False)  # PENDING, SUCCESS, FAILED, DUPLICATE, REFUNDED
    rrn = Column(String(64), nullable=True)  # Bank Retrieval Reference Number
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    merchant = relationship("Merchant", back_populates="payments")
    cases = relationship("Case", back_populates="payment")


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(64), primary_key=True, index=True)  # e.g., PV-1001
    merchant_id = Column(Integer, ForeignKey("merchants.id"), nullable=False)
    payment_id = Column(String(64), ForeignKey("payments.id"), nullable=True)
    status = Column(String(30), default="OPEN", nullable=False)  # OPEN, EVALUATING, RESOLVED, ESCALATED, CLOSED
    trigger_reason = Column(String(255), nullable=False)  # e.g., "Payment stuck > 2s"
    recommended_action = Column(String(50), nullable=True)
    resolution = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    merchant = relationship("Merchant", back_populates="cases")
    payment = relationship("Payment", back_populates="cases")
    actions = relationship("Action", back_populates="case", cascade="all, delete-orphan")


class Action(Base):
    __tablename__ = "actions"

    id = Column(String(64), primary_key=True, index=True)
    case_id = Column(String(64), ForeignKey("cases.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # REFUND, BLOCK_DUPLICATE, HOLD, APPROVE
    status = Column(String(30), default="PENDING", nullable=False)  # PENDING, APPROVED, BLOCKED, EXECUTED, REJECTED
    gate_results = Column(Text, nullable=True)  # JSON-serialized evaluations for all 7 gates
    blocked_by_gate = Column(String(50), nullable=True)
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    case = relationship("Case", back_populates="actions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    prev_hash = Column(String(64), nullable=False)
    event_hash = Column(String(64), nullable=False)
    event_type = Column(String(50), nullable=False)  # SYSTEM_INIT, PAYMENT_CREATED, FIREWALL_EVALUATED, etc.
    actor = Column(String(50), nullable=False)  # system, merchant, customer, firewall
    payload = Column(Text, nullable=False)  # JSON-serialized payload
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

