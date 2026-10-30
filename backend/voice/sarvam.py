import os
import hashlib
import base64
import logging
from typing import Optional, Dict
import httpx
from dotenv import load_dotenv

# Explicitly load .env from backend folder and repo root
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(backend_dir)
load_dotenv(os.path.join(backend_dir, ".env"))
load_dotenv(os.path.join(root_dir, ".env"))

logger = logging.getLogger("pivaani.voice")

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "audio")

# Valid Sarvam AI speakers (priya / kavya / rahul / meera fallback)
DEFAULT_SPEAKER = "priya"

# Templates for Hindi, Tamil, and English
TEMPLATES: Dict[str, Dict[str, str]] = {
    "hi-IN": {
        "payment_pending": "रुपये {amount} बैंक में लंबित हैं। भरोसा सुरक्षा सक्रिय है, दोबारा भुगतान न करें।",
        "payment_success": "{merchant} को रुपये {amount} सफलतापूर्वक प्राप्त हुए।",
        "fraud_blocked": "चेतावनी! फ्रॉड रिंग का पता चला। यह लेन-देन तुरंत रोक दिया गया है।",
        "authority_blocked": "अस्वीकृत! अनधिकृत वॉइस रिफंड अनुरोध को अथॉरिटी गेट ने रोक दिया।",
        "amount_exceeded": "रुपये {amount} सुरक्षा सीमा से अधिक है। मर्चेंट पिन सत्यापन आवश्यक है।",
        "confidence_failed": "कम विश्वास स्कोर। सुरक्षा के लिए लेन-देन रोक दिया गया।",
        "idempotency_blocked": "डुप्लीकेट रिटैप अवरुद्ध। केवल एक बार शुल्क लिया जाएगा।",
        "spoof_blocked": "वॉइस बायोमेट्रिक बेमेल। पहचान गेट द्वारा अनुरोध खारिज कर दिया गया।"
    },
    "ta-IN": {
        "payment_pending": "ரூபாய் {amount} வங்கியில் நிலுவையில் உள்ளது. பரோசா பாதுகாப்பு இயங்குகிறது, மீண்டும் பணம் செலுத்த வேண்டாம்.",
        "payment_success": "{merchant} அவர்களுக்கு ரூபாய் {amount} வெற்றிகரமாக பெறப்பட்டது.",
        "fraud_blocked": "எச்சரிக்கை! மோசடி வளையம் கண்டறியப்பட்டது. இந்த பரிவர்த்தனை உடனடியாக தடுக்கப்பட்டது.",
        "authority_blocked": "நிராகரிக்கப்பட்டது! அங்கீகரிக்கப்படாத குரல் கட்டளை அத்தாரிட்டி கேட் மூலம் தடுக்கப்பட்டது.",
        "amount_exceeded": "தொகை ரூபாய் {amount} வரம்பை மீறியது. வணிகரின் பின் ஒப்புதல் தேவை.",
        "confidence_failed": "குறைந்த நெட்வொர்க் நம்பிக்கை மதிப்பு. பரிவர்த்தனை நிறுத்தி வைக்கப்பட்டுள்ளது.",
        "idempotency_blocked": "நகல் பரிவர்த்தனை தடுக்கப்பட்டது. ஒரு முறை மட்டுமே பிடித்தம் செய்யப்படும்.",
        "spoof_blocked": "குரல் சரிபார்ப்பு தோல்வி. அடையாளம் கேட் மூலம் தடுக்கப்பட்டது."
    },
    "en-IN": {
        "payment_pending": "Rupees {amount} pending with bank. Protected by Bharosa layer. Do not retap.",
        "payment_success": "Received Rupees {amount} successfully at {merchant}.",
        "fraud_blocked": "Warning: Fraud ring detected. Transaction blocked by Identity Gate.",
        "authority_blocked": "Declined: Unauthorized refund command blocked by Authority Gate.",
        "amount_exceeded": "Rupees {amount} exceeds automated safety threshold. Merchant PIN required.",
        "confidence_failed": "Low banking switch confidence score. Blocked by Confidence Gate.",
        "idempotency_blocked": "Duplicate retap detected. Blocked by Idempotency Gate.",
        "spoof_blocked": "Voice biometric mismatch. Blocked by Identity Gate."
    }
}

def get_template_text(template_key: str, lang: str = "hi-IN", **kwargs) -> str:
    """Returns formatted template text in the requested language"""
    lang_dict = TEMPLATES.get(lang, TEMPLATES["en-IN"])
    template = lang_dict.get(template_key, TEMPLATES["en-IN"].get(template_key, ""))
    return template.format(**kwargs)

async def generate_tts(text: str, lang: str = "hi-IN") -> Optional[str]:
    """
    Generates TTS audio using Sarvam AI API.
    - Reads SARVAM_API_KEY from environment.
    - If DEMO_SCRIPTED=1 or no key is found, returns None.
    - Calls Sarvam AI TTS with valid speaker.
    - Saves returned base64 audio to backend/static/audio/<hash>.mp3.
    - Returns URL path string e.g. "/static/audio/<hash>.mp3".
    """
    demo_scripted = os.getenv("DEMO_SCRIPTED", "0").strip()
    api_key = os.getenv("SARVAM_API_KEY", "").strip()

    if demo_scripted == "1" or not api_key:
        logger.info(f"TTS skipped (DEMO_SCRIPTED={demo_scripted}, has_key={bool(api_key)})")
        return None

    target_lang = lang if "-" in lang else f"{lang}-IN"

    try:
        os.makedirs(AUDIO_DIR, exist_ok=True)
        filename = hashlib.md5(f"{target_lang}:{text}".encode("utf-8")).hexdigest() + ".mp3"
        filepath = os.path.join(AUDIO_DIR, filename)
        url_path = f"/static/audio/{filename}"

        if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
            logger.info(f"Using cached TTS audio: {url_path}")
            return url_path

        headers = {
            "api-subscription-key": api_key,
            "Content-Type": "application/json"
        }
        # Speaker 'priya' is supported by Sarvam bulbul
        payload = {
            "inputs": [text],
            "target_language_code": target_lang,
            "speaker": DEFAULT_SPEAKER
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(SARVAM_TTS_URL, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                audios = data.get("audios", [])
                if audios and audios[0]:
                    audio_bytes = base64.b64decode(audios[0])
                    with open(filepath, "wb") as f:
                        f.write(audio_bytes)
                    logger.info(f"Generated Sarvam TTS audio: {url_path}")
                    return url_path
            else:
                logger.warning(f"Sarvam API error ({response.status_code}): {response.text}")
                return None
    except Exception as e:
        logger.error(f"Error calling Sarvam TTS API: {e}")
        return None
