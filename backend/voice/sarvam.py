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

# Templates for Hindi, Tamil, and English.
# Spoken lines use {case_ref} ("PV 1001", easier for TTS); receipts use {case_id}.
TEMPLATES: Dict[str, Dict[str, str]] = {
    "hi-IN": {
        "customer_reassure": "आपका पैसा सुरक्षित है। रुपये {amount} का भुगतान प्रोसेस हो रहा है। केस {case_ref}। कृपया दोबारा भुगतान न करें।",
        "merchant_case_opened": "रुपये {amount} का भुगतान लंबित है। केस {case_ref} खोला गया। ग्राहक को रुकने के लिए कहें।",
        "customer_retap_blocked": "आपका दूसरा भुगतान रोक दिया गया। आपसे दो बार पैसा नहीं लिया जाएगा।",
        "merchant_approval_needed": "रुपये {amount} के रिफंड के लिए आपकी मंज़ूरी चाहिए। केस {case_ref}। मंज़ूरी के साथ अपना पिन बोलें।",
        "approval_rejected": "मंज़ूरी अस्वीकार। पिन गलत है या यह अनुरोध मर्चेंट का नहीं है।",
        "customer_refunded": "आपके रुपये {amount} वापस भेज दिए गए हैं। केस {case_ref}। पैसा जल्द ही आपके खाते में आ जाएगा।",
        "merchant_refund_done": "रिफंड पूरा। रुपये {amount} ग्राहक को वापस भेज दिए गए। केस {case_ref}।",
        "refund_blocked": "रिफंड रोका गया। सुरक्षा जांच पूरी नहीं हुई।",
        "customer_refund_review": "आपका पैसा सुरक्षित है। रुपये {amount} का केस {case_ref} जांच के लिए भेजा गया है। कृपया दोबारा भुगतान न करें।",
        "payment_success": "{merchant} को रुपये {amount} सफलतापूर्वक प्राप्त हुए।",
        "fraud_blocked": "चेतावनी! फ्रॉड रिंग पैटर्न मिला। ऑटो रिफंड रोककर मैनुअल जांच के लिए भेजा गया।",
        "authority_blocked": "अस्वीकृत! ग्राहक के नोट से आया रिफंड आदेश अथॉरिटी गेट ने रोक दिया।",
        "amount_exceeded": "रुपये {amount} पाँच हज़ार की सख्त सीमा से ज़्यादा है। रिफंड रोका गया।",
        "confidence_failed": "कम विश्वास स्कोर। सुरक्षा के लिए रिफंड रोक दिया गया।",
        "idempotency_blocked": "पुरानी मंज़ूरी दोबारा इस्तेमाल की गई। आइडेम्पोटेंसी गेट ने रोक दिया।",
        "spoof_blocked": "केवल मर्चेंट ही रिफंड मंज़ूर कर सकता है। ग्राहक की आवाज़ अथॉरिटी गेट ने खारिज की।",
        "receipt_refunded": "भरोसा रसीद · केस {case_id} · रुपये {amount} · रिफंड हो गया",
        "receipt_confirmed": "भरोसा रसीद · केस {case_id} · रुपये {amount} · भुगतान सफल"
    },
    "ta-IN": {
        "customer_reassure": "உங்கள் பணம் பாதுகாப்பாக உள்ளது. ரூபாய் {amount} கட்டணம் செயலாக்கத்தில் உள்ளது. கேஸ் {case_ref}. மீண்டும் பணம் செலுத்த வேண்டாம்.",
        "merchant_case_opened": "ரூபாய் {amount} கட்டணம் நிலுவையில் உள்ளது. கேஸ் {case_ref} திறக்கப்பட்டது. வாடிக்கையாளரை காத்திருக்கச் சொல்லுங்கள்.",
        "customer_retap_blocked": "உங்கள் இரண்டாவது கட்டணம் தடுக்கப்பட்டது. இரண்டு முறை பணம் எடுக்கப்படாது.",
        "merchant_approval_needed": "ரூபாய் {amount} ரீஃபண்டுக்கு உங்கள் ஒப்புதல் தேவை. கேஸ் {case_ref}. ஒப்புதலுடன் உங்கள் பின் எண்ணைச் சொல்லுங்கள்.",
        "approval_rejected": "ஒப்புதல் நிராகரிக்கப்பட்டது. பின் தவறு அல்லது இது வணிகரின் கோரிக்கை அல்ல.",
        "customer_refunded": "உங்கள் ரூபாய் {amount} திருப்பி அனுப்பப்பட்டது. கேஸ் {case_ref}. விரைவில் உங்கள் கணக்கில் வரவு வைக்கப்படும்.",
        "merchant_refund_done": "ரீஃபண்ட் முடிந்தது. ரூபாய் {amount} வாடிக்கையாளருக்கு திருப்பி அனுப்பப்பட்டது. கேஸ் {case_ref}.",
        "refund_blocked": "ரீஃபண்ட் தடுக்கப்பட்டது. பாதுகாப்பு சோதனை தோல்வியடைந்தது.",
        "customer_refund_review": "உங்கள் பணம் பாதுகாப்பாக உள்ளது. ரூபாய் {amount} கேஸ் {case_ref} சரிபார்ப்புக்கு அனுப்பப்பட்டது. மீண்டும் பணம் செலுத்த வேண்டாம்.",
        "payment_success": "{merchant} அவர்களுக்கு ரூபாய் {amount} வெற்றிகரமாக பெறப்பட்டது.",
        "fraud_blocked": "எச்சரிக்கை! மோசடி வளைய முறை கண்டறியப்பட்டது. தானியங்கி ரீஃபண்ட் கைமுறை சரிபார்ப்புக்கு நிறுத்தப்பட்டது.",
        "authority_blocked": "நிராகரிக்கப்பட்டது! வாடிக்கையாளர் குறிப்பில் வந்த ரீஃபண்ட் கட்டளை அத்தாரிட்டி கேட் மூலம் தடுக்கப்பட்டது.",
        "amount_exceeded": "ரூபாய் {amount} ஐந்தாயிரம் உச்ச வரம்பை மீறுகிறது. ரீஃபண்ட் தடுக்கப்பட்டது.",
        "confidence_failed": "குறைந்த நம்பிக்கை மதிப்பு. பாதுகாப்புக்காக ரீஃபண்ட் நிறுத்தப்பட்டது.",
        "idempotency_blocked": "பழைய ஒப்புதல் மீண்டும் பயன்படுத்தப்பட்டது. ஐடெம்பொடென்சி கேட் தடுத்தது.",
        "spoof_blocked": "வணிகர் மட்டுமே ரீஃபண்டை அங்கீகரிக்க முடியும். வாடிக்கையாளர் குரல் அத்தாரிட்டி கேட் மூலம் நிராகரிக்கப்பட்டது.",
        "receipt_refunded": "பரோசா ரசீது · கேஸ் {case_id} · ரூபாய் {amount} · ரீஃபண்ட் முடிந்தது",
        "receipt_confirmed": "பரோசா ரசீது · கேஸ் {case_id} · ரூபாய் {amount} · கட்டணம் வெற்றி"
    },
    "en-IN": {
        "customer_reassure": "Your money is safe. Your Rupees {amount} payment is processing. Case {case_ref}. Please do not pay again.",
        "merchant_case_opened": "Rupees {amount} payment is pending. Case {case_ref} opened. Ask the customer to wait.",
        "customer_retap_blocked": "Your second payment was blocked. You will not be charged twice.",
        "merchant_approval_needed": "Refund of Rupees {amount} needs your approval. Case {case_ref}. Say approve with your PIN.",
        "approval_rejected": "Approval rejected. Wrong PIN, or the request did not come from the merchant.",
        "customer_refunded": "Your Rupees {amount} has been refunded. Case {case_ref}. It will reach your account shortly.",
        "merchant_refund_done": "Refund complete. Rupees {amount} sent back to the customer. Case {case_ref}.",
        "refund_blocked": "Refund blocked. Safety checks did not pass.",
        "customer_refund_review": "Your money is safe. Your Rupees {amount} case {case_ref} has been sent for review. Please do not pay again.",
        "payment_success": "Received Rupees {amount} successfully at {merchant}.",
        "fraud_blocked": "Warning: fraud ring pattern detected. Auto-refund held for manual review.",
        "authority_blocked": "Declined: a refund command from a customer note was blocked by the Authority Gate.",
        "amount_exceeded": "Rupees {amount} exceeds the five thousand rupee hard ceiling. Refund blocked.",
        "confidence_failed": "Low confidence score. Refund blocked by the Confidence Gate.",
        "idempotency_blocked": "Replayed approval detected. Blocked by the Idempotency Gate.",
        "spoof_blocked": "Only the merchant can approve refunds. Customer voice rejected by the Authority Gate.",
        "receipt_refunded": "Bharosa Receipt · Case {case_id} · Rs {amount} · Refunded",
        "receipt_confirmed": "Bharosa Receipt · Case {case_id} · Rs {amount} · Payment successful"
    }
}

class _BlankMissing(dict):
    def __missing__(self, key):
        return ""

def spoken_case_ref(case_id: Optional[str]) -> str:
    """'PV-1001' -> 'PV 1001' so TTS reads it as letters and a number"""
    return (case_id or "").replace("-", " ")

def get_template_text(template_key: str, lang: str = "hi-IN", **kwargs) -> str:
    """Returns formatted template text in the requested language"""
    lang_dict = TEMPLATES.get(lang, TEMPLATES["en-IN"])
    template = lang_dict.get(template_key, TEMPLATES["en-IN"].get(template_key, ""))
    # Speak "40", not "40.0"
    amount = kwargs.get("amount")
    if isinstance(amount, float) and amount.is_integer():
        kwargs["amount"] = int(amount)
    if "case_id" in kwargs and "case_ref" not in kwargs:
        kwargs["case_ref"] = spoken_case_ref(kwargs["case_id"])
    return template.format_map(_BlankMissing(kwargs))

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
