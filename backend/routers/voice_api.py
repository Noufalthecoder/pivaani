import logging
import os
import httpx
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

logger = logging.getLogger("pivaani.voice_api")

router = APIRouter(prefix="/api/voice", tags=["Voice"])

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saarika:v2.5")
MAX_AUDIO_BYTES = 5 * 1024 * 1024

def _api_key() -> str:
    return os.getenv("SARVAM_API_KEY", "").strip()

@router.get("/status")
def voice_status():
    """Lets the soundbox pick Sarvam STT, or fall back to the browser's recognizer"""
    return {"stt": bool(_api_key()) and os.getenv("DEMO_SCRIPTED", "0").strip() != "1", "model": SARVAM_STT_MODEL}

@router.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    lang: str = Query("unknown", description="hi-IN, ta-IN, en-IN, or 'unknown' to auto-detect")
):
    """Merchant push-to-talk: audio (WAV/MP3) in, Sarvam transcript out"""
    api_key = _api_key()
    if not api_key:
        raise HTTPException(status_code=503, detail="Sarvam STT not configured (SARVAM_API_KEY missing)")

    audio = await file.read()
    if not audio:
        raise HTTPException(status_code=400, detail="Empty audio")
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio too long")

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                SARVAM_STT_URL,
                headers={"api-subscription-key": api_key},
                files={"file": (file.filename or "speech.wav", audio, file.content_type or "audio/wav")},
                data={"model": SARVAM_STT_MODEL, "language_code": lang},
            )
    except httpx.HTTPError as e:
        logger.error(f"Sarvam STT unreachable: {e}")
        raise HTTPException(status_code=502, detail="Sarvam STT unreachable")

    if response.status_code != 200:
        logger.warning(f"Sarvam STT error ({response.status_code}): {response.text[:300]}")
        raise HTTPException(status_code=502, detail=f"Sarvam STT error {response.status_code}")

    data = response.json()
    return {"transcript": data.get("transcript", ""), "language_code": data.get("language_code")}
