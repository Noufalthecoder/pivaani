import logging
import os
import httpx
from fastapi import APIRouter, File, HTTPException, Query, UploadFile

logger = logging.getLogger("pivaani.voice_api")

router = APIRouter(prefix="/api/voice", tags=["Voice"])

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saarika:v2.5")
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
SARVAM_TRANSLATE_MODEL = os.getenv("SARVAM_TRANSLATE_MODEL", "mayura:v1")
MAX_AUDIO_BYTES =5 * 1024 * 1024

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
    transcript = data.get("transcript", "")
    language_code = data.get("language_code")
    english = await _to_english(transcript, language_code)
    return {"transcript": transcript, "language_code": language_code, "english": english}

async def _to_english(text: str, source: str | None = None) -> str:
    """English rendering of a command in any Indian language, so intents match whatever was spoken.
    Returns the text unchanged if it is already English or Sarvam is unavailable."""
    text = (text or "").strip()
    api_key = _api_key()
    if not text or not api_key or (source or "").startswith("en") or text.isascii():
        return text
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                SARVAM_TRANSLATE_URL,
                headers={"api-subscription-key": api_key},
                json={
                    "input": text[:900],
                    "source_language_code": source if source and source != "unknown" else "auto",
                    "target_language_code": "en-IN",
                    "model": SARVAM_TRANSLATE_MODEL,
                },
            )
        if response.status_code == 200:
            return response.json().get("translated_text", "") or text
        logger.warning(f"Sarvam translate error ({response.status_code}): {response.text[:300]}")
    except httpx.HTTPError as e:
        logger.error(f"Sarvam translate unreachable: {e}")
    return text

@router.post("/translate")
async def translate_command(body: dict):
    """Typed or browser-recognised command in any language -> English, for intent matching"""
    text = str(body.get("text", ""))[:900]
    return {"english": await _to_english(text, body.get("lang"))}
