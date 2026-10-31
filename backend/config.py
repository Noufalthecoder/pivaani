import os
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent

class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "Pi Vaani Backend")
    VERSION: str = "0.1.0"
    
    # SQLite Database location
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/pivaani.db")
    
    # Demo Merchant: Ravi
    DEFAULT_MERCHANT_NAME: str = "Ravi"
    DEFAULT_MERCHANT_BUSINESS: str = "Ravi's Chai Stall"
    DEFAULT_MERCHANT_VPA: str = "ravi.chai@upi"
    DEFAULT_MERCHANT_PHONE: str = "+919876543210"
    DEFAULT_TRUST_DIAL: str = "balanced"
    DEFAULT_MERCHANT_PIN: str = "4321"

    # Stuck payment detection threshold in seconds
    DETECT_AFTER_SECONDS: int = int(os.getenv("DETECT_AFTER_SECONDS", "2"))

    # Every soundbox line is spoken once per language, in this order (English first, then Hindi)
    VOICE_LANGS: List[str] = [l.strip() for l in os.getenv("VOICE_LANGS", "en-IN,hi-IN").split(",") if l.strip()]

    # Bharosa receipt languages
    CUSTOMER_VOICE_LANG: str = os.getenv("CUSTOMER_VOICE_LANG", "hi-IN")
    MERCHANT_VOICE_LANG: str = os.getenv("MERCHANT_VOICE_LANG", "en-IN")

    # Dial Policy Configurations for the 7-Gate Safety Firewall
    POLICY_CONFIGS: Dict[str, Dict[str, Any]] = {
        "careful": {
            "auto_refund_max": 0.0,
            "min_confidence": 0.90,
            "require_voice_approval": True,
            "require_pin": True,
        },
        "balanced": {
            "auto_refund_max": 200.0,
            "min_confidence": 0.80,
            "require_voice_approval": True,
            "require_pin": False,
        },
        "fast": {
            "auto_refund_max": 500.0,
            "min_confidence": 0.70,
            "require_voice_approval": False,
            "require_pin": False,
        },
    }

settings = Settings()

