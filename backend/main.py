import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from config import settings
from db import Base, engine, get_db, SessionLocal
from models import Merchant, Policy, Payment, Case, Action, AuditEvent
from audit import record_audit_event, verify_chain, install_append_only_guards
from events import manager, broadcast, start_event_dispatcher, stop_event_dispatcher
from cases import start_case_monitor, stop_case_monitor, ACTIVE_CASE_STATUSES
from security import hash_pin, is_pin_hashed, nonce_store, pin_limiter
from fraud_graph import fraud_detector
from locks import lock_manager
from routers.sandbox_api import router as sandbox_router
from routers.attack_api import router as attack_router
from routers.voice_api import router as voice_router
from fastapi.staticfiles import StaticFiles
import os
import schemas

# Setup structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("pivaani.main")

def seed_database(db: Session):
    """Seeds the initial Merchant 'Ravi' and default policies if not already present"""
    merchant = db.query(Merchant).filter(Merchant.name == settings.DEFAULT_MERCHANT_NAME).first()
    if not merchant:
        logger.info("Seeding initial Merchant: Ravi with trust_dial='balanced' and demo PIN '4321'")
        merchant = Merchant(
            id=1,
            name=settings.DEFAULT_MERCHANT_NAME,
            business_name=settings.DEFAULT_MERCHANT_BUSINESS,
            vpa=settings.DEFAULT_MERCHANT_VPA,
            phone=settings.DEFAULT_MERCHANT_PHONE,
            trust_dial=settings.DEFAULT_TRUST_DIAL,
            pin=hash_pin(settings.DEFAULT_MERCHANT_PIN),
            created_at=datetime.utcnow()
        )
        db.add(merchant)
        db.commit()
        db.refresh(merchant)

        # Seed the 3 standard policy rules for the merchant
        for dial, cfg in settings.POLICY_CONFIGS.items():
            policy = Policy(
                merchant_id=merchant.id,
                dial_level=dial,
                auto_refund_max=cfg["auto_refund_max"],
                min_confidence=cfg["min_confidence"],
                require_voice_approval=cfg["require_voice_approval"],
                require_pin=cfg["require_pin"],
                is_active=(dial == settings.DEFAULT_TRUST_DIAL)
            )
            db.add(policy)
        db.commit()

        # Seed Genesis Audit Event
        record_audit_event(
            db=db,
            event_type="SYSTEM_INIT",
            actor="system",
            payload={
                "message": "Pi Vaani Bharosa Layer initialized",
                "merchant": merchant.name,
                "vpa": merchant.vpa,
                "default_trust_dial": merchant.trust_dial
            }
        )
        logger.info("Seed completed successfully.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan handler for startup database initialization, seeding, and background monitor"""
    logger.info("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    install_append_only_guards(engine)
    db = SessionLocal()
    try:
        seed_database(db)
        # Older databases stored the PIN in plain text: hash it in place
        for merchant in db.query(Merchant).all():
            if not is_pin_hashed(merchant.pin):
                merchant.pin = hash_pin(merchant.pin)
        db.commit()
    finally:
        db.close()

    start_event_dispatcher()
    # Start the Case State Machine background monitor (checks every 1s)
    start_case_monitor()
    logger.info("Case State Machine background monitor initialized.")

    yield

    stop_case_monitor()
    stop_event_dispatcher()
    logger.info("Application shutting down.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Deterministic Bharosa Layer & Virtual Soundbox Gateway for UPI",
    lifespan=lifespan
)

# Enable CORS for the Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Sandbox Scenarios & Attacks Routers
app.include_router(sandbox_router)
app.include_router(attack_router)
app.include_router(voice_router)

# Mount static audio files
static_audio_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_audio_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_audio_dir), name="static")

# -------------------------------------------------------------
# 1. WEBSOCKET ROUTE
# -------------------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket hub for real-time soundbox audio streaming, gate progression,
    and demo control drawer scenario injection.
    """
    await manager.connect(websocket)
    try:
        # Send initial handshake message
        await websocket.send_json({
            "type": "HANDSHAKE",
            "payload": {
                "status": "connected",
                "soundbox": "Pi Vaani Virtual Soundbox v1",
                "ready": True
            },
            "timestamp": datetime.utcnow().isoformat()
        })

        while True:
            data = await websocket.receive_text()
            # Handle incoming client telemetry or scenario ping
            logger.debug(f"Received from client: {data}")
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# -------------------------------------------------------------
# 2. REST API ENDPOINTS
# -------------------------------------------------------------
@app.get("/api/health", response_model=schemas.HealthResponse, tags=["System"])
def get_health(db: Session = Depends(get_db)):
    """Healthcheck endpoint confirming API and DB connectivity"""
    try:
        # Probe DB
        merchant_count = db.query(Merchant).count()
        db_status = f"connected ({merchant_count} merchants)"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return schemas.HealthResponse(
        status="healthy",
        database=db_status,
        timestamp=datetime.utcnow().isoformat(),
        version=settings.VERSION
    )

@app.post("/api/reset", response_model=schemas.ResetResponse, tags=["Sandbox"])
async def reset_state(db: Session = Depends(get_db)):
    """
    Resets the sandbox database state back to initial seed baseline:
    - Clears cases, actions and payments. The audit chain is append-only and is kept;
      the reset itself is recorded in it.
    - Resets Merchant 'Ravi' PIN to '4321' (the trust dial is kept).
    - Records state reset into audit hash chain.
    - Broadcasts reset to connected WebSockets.
    """
    try:
        # Clear transactional tables
        db.query(Action).delete()
        db.query(Case).delete()
        db.query(Payment).delete()
        db.commit()

        # Reset in-memory fraud graph, approval nonces and PIN lockouts
        fraud_detector.reset()
        lock_manager.reset()
        nonce_store.reset()
        pin_limiter.reset()

        # Reset or re-create Merchant Ravi
        merchant = db.query(Merchant).filter(Merchant.name == settings.DEFAULT_MERCHANT_NAME).first()
        if merchant:
            # The trust dial is the merchant's own setting: a sandbox reset keeps it
            merchant.pin = hash_pin(settings.DEFAULT_MERCHANT_PIN)
            db.commit()
            db.refresh(merchant)
        else:
            seed_database(db)
            merchant = db.query(Merchant).first()

        # Record fresh genesis audit event
        record_audit_event(
            db=db,
            event_type="STATE_RESET",
            actor="system",
            payload={"action": "reset_sandbox", "reset_by": "api_call"}
        )

        # Broadcast reset event to all frontend clients
        await broadcast("STATE_RESET", {
            "message": "Sandbox reset to baseline",
            "trust_dial": merchant.trust_dial
        })

        return schemas.ResetResponse(
            message="Sandbox state successfully reset to initial seed.",
            timestamp=datetime.utcnow().isoformat(),
            merchant=merchant
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error resetting state: {e}")
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@app.get("/api/state", response_model=schemas.StateResponse, tags=["Sandbox"])
def get_state(db: Session = Depends(get_db)):
    """
    Returns the comprehensive state of the merchant, payments, active case,
    and latest audit log for the /demo dashboard.
    """
    merchant = db.query(Merchant).filter(Merchant.name == settings.DEFAULT_MERCHANT_NAME).first()
    payments = db.query(Payment).order_by(Payment.created_at.desc()).limit(20).all()
    active_cases = db.query(Case).filter(Case.status.in_(ACTIVE_CASE_STATUSES)).all()
    latest_audit = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()

    active_dial = merchant.trust_dial if merchant else settings.DEFAULT_TRUST_DIAL

    return schemas.StateResponse(
        merchant=merchant,
        payments=payments,
        active_cases=active_cases,
        latest_audit=latest_audit,
        active_dial=active_dial,
        server_time=datetime.utcnow().isoformat()
    )

# -------------------------------------------------------------
# 3. AUDIT & TRUST DIAL HELPERS
# -------------------------------------------------------------
@app.get("/api/audit/verify", response_model=schemas.ChainVerificationOut, tags=["Audit"])
def verify_audit_chain(db: Session = Depends(get_db)):
    """Cryptographically verifies the SHA-256 hash chain of all audit events"""
    result = verify_chain(db)
    return schemas.ChainVerificationOut(**result)

@app.get("/api/audit", response_model=List[schemas.AuditEventOut], tags=["Audit"])
def get_audit_trail(db: Session = Depends(get_db), limit: int = 50):
    """Returns recent audit events for the demo audit log window"""
    return db.query(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit).all()

@app.patch("/api/merchant/dial", response_model=schemas.MerchantOut, tags=["Merchant"])
async def update_trust_dial(payload: schemas.MerchantUpdateDial, db: Session = Depends(get_db)):
    """Updates the merchant trust dial ('careful', 'balanced', 'fast')"""
    mode = payload.trust_dial.lower()
    if mode not in settings.POLICY_CONFIGS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid dial level '{mode}'. Must be one of: {list(settings.POLICY_CONFIGS.keys())}"
        )

    merchant = db.query(Merchant).filter(Merchant.name == settings.DEFAULT_MERCHANT_NAME).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    old_dial = merchant.trust_dial
    merchant.trust_dial = mode
    db.commit()
    db.refresh(merchant)

    # Log dial change to cryptographic audit chain
    record_audit_event(
        db=db,
        event_type="TRUST_DIAL_CHANGED",
        actor="merchant",
        payload={"from": old_dial, "to": mode, "merchant_id": merchant.id}
    )

    # Broadcast dial update to all UI clients
    await broadcast("TRUST_DIAL_CHANGED", {"trust_dial": mode})

    return merchant

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

