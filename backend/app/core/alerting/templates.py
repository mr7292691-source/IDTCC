"""Personalized, multilingual alert templates.

Static templates in English / Tamil / Hindi / Telugu / Kannada provide an
instant, offline-safe fallback. When a vLLM (Qwen3-14B) endpoint is available,
`render()` can be swapped for an LLM call for languages / tones beyond these —
but the static set guarantees the demo (and a real disaster) never depends on
the model being up.

Every template is built to fit a single 160-char SMS / IVR script so it works on
a basic phone with no internet — the primary channel during a disaster.
"""
from __future__ import annotations

from typing import Dict

SUPPORTED_LANGUAGES = ["en", "ta", "hi", "te", "kn"]

# alert_type -> language -> template. Placeholders are str.format keys.
TEMPLATES: Dict[str, Dict[str, str]] = {
    "cyclone_warning": {
        "en": ("{name}, Cyclone {hazard} expected in {eta_hours}h. Your area "
               "{ward} is HIGH RISK. Nearest shelter: {shelter}, {distance_km}km. "
               "Leave before {leave_by}. Help: {helpline}"),
        "ta": ("{name}, {eta_hours} மணி நேரத்தில் {hazard} புயல் வரும். உங்கள் "
               "பகுதி {ward} அதிக ஆபத்து. அருகில் தஞ்சம்: {shelter}, {distance_km}கி.மீ. "
               "{leave_by} முன் அகலுங்கள். உதவி: {helpline}"),
        "hi": ("{name}, {eta_hours}घं में चक्रवात {hazard}। {ward} अति जोखिम में। "
               "शरण: {shelter}, {distance_km}किमी. {leave_by} से पहले निकलें। "
               "मदद: {helpline}"),
        "te": ("{name}, {eta_hours} గంటల్లో తుఫాను {hazard} వస్తోంది. మీ ప్రాంతం "
               "{ward} అధిక ప్రమాదం. దగ్గరి ఆశ్రయం: {shelter}, {distance_km}కిమీ. "
               "{leave_by} లోపు బయలుదేరండి. సహాయం: {helpline}"),
        "kn": ("{name}, {eta_hours} ಗಂಟೆಯಲ್ಲಿ ಚಂಡಮಾರುತ {hazard} ಬರಲಿದೆ. ನಿಮ್ಮ "
               "ಪ್ರದೇಶ {ward} ಹೆಚ್ಚಿನ ಅಪಾಯ. ಹತ್ತಿರದ ಆಶ್ರಯ: {shelter}, {distance_km}ಕಿಮೀ. "
               "{leave_by} ಮೊದಲು ಹೊರಡಿ. ಸಹಾಯ: {helpline}"),
    },
    "flood_warning": {
        "en": ("{name}, river breach expected in {eta_hours}h. Move to higher "
               "ground NOW. Do NOT use {blocked_road} (flooded). Use {alt_route}. "
               "Shelter: {shelter}. Help: {helpline}"),
        "ta": ("{name}, {eta_hours} மணியில் ஆறு உடைக்கும். உடனே உயரமான இடத்திற்கு "
               "செல்லுங்கள். {blocked_road} பயன்படுத்த வேண்டாம் (வெள்ளம்). "
               "{alt_route} பயன்படுத்துங்கள். தஞ்சம்: {shelter}. உதவி: {helpline}"),
        "hi": ("{name}, {eta_hours} घंटे में नदी का तटबंध टूट सकता है। तुरंत ऊँची "
               "जगह जाएँ। {blocked_road} का उपयोग न करें (बाढ़)। {alt_route} लें। "
               "शरण: {shelter}. मदद: {helpline}"),
        "te": ("{name}, {eta_hours} గంటల్లో నది కట్ట తెగొచ్చు. వెంటనే ఎత్తైన "
               "ప్రాంతానికి వెళ్లండి. {blocked_road} వాడొద్దు (వరద). {alt_route} "
               "వాడండి. ఆశ్రయం: {shelter}. సహాయం: {helpline}"),
        "kn": ("{name}, {eta_hours} ಗಂಟೆಯಲ್ಲಿ ನದಿ ಒಡ್ಡು ಒಡೆಯಬಹುದು. ಕೂಡಲೇ ಎತ್ತರದ "
               "ಸ್ಥಳಕ್ಕೆ ಹೋಗಿ. {blocked_road} ಬಳಸಬೇಡಿ (ಪ್ರವಾಹ). {alt_route} ಬಳಸಿ. "
               "ಆಶ್ರಯ: {shelter}. ಸಹಾಯ: {helpline}"),
    },
    "rescue_confirmation": {
        "en": ("{name}, rescue team dispatched to your location. ETA "
               "{eta_minutes} min. Stay visible. Flash a light if possible. "
               "Help: {helpline}"),
        "ta": ("{name}, மீட்பு குழு உங்கள் இடத்திற்கு அனுப்பப்பட்டது. வருகை "
               "{eta_minutes} நிமிடம். தெரியும்படி இருங்கள். விளக்கு காட்டுங்கள். "
               "உதவி: {helpline}"),
        "hi": ("{name}, बचाव दल आपके स्थान पर भेजा गया है। पहुँचने का समय "
               "{eta_minutes} मिनट। दिखाई दें। रोशनी दिखाएँ। मदद: {helpline}"),
        "te": ("{name}, రక్షణ బృందం మీ వద్దకు పంపబడింది. చేరే సమయం {eta_minutes} "
               "నిమి. కనిపించేలా ఉండండి. లైట్ చూపండి. సహాయం: {helpline}"),
        "kn": ("{name}, ರಕ್ಷಣಾ ತಂಡ ನಿಮ್ಮ ಸ್ಥಳಕ್ಕೆ ಕಳುಹಿಸಲಾಗಿದೆ. ಆಗಮನ {eta_minutes} "
               "ನಿಮಿ. ಕಾಣಿಸಿಕೊಳ್ಳಿ. ಬೆಳಕು ತೋರಿಸಿ. ಸಹಾಯ: {helpline}"),
    },
}

_DEFAULTS = {
    "name": "Citizen", "hazard": "the storm", "eta_hours": "?", "ward": "your area",
    "district": "", "shelter": "the nearest shelter", "distance_km": "?",
    "leave_by": "immediately", "helpline": "108", "blocked_road": "the main road",
    "alt_route": "an inland route", "eta_minutes": "?",
}


def render(alert_type: str, language: str, **kwargs) -> str:
    """Render a personalized alert. Falls back to English, then a generic line."""
    lang_map = TEMPLATES.get(alert_type, {})
    template = lang_map.get(language) or lang_map.get("en")
    if template is None:
        return (f"{kwargs.get('name', 'Citizen')}: emergency in your area. "
                f"Move to {kwargs.get('shelter', 'the nearest shelter')} now.")
    fields = {**_DEFAULTS, **{k: v for k, v in kwargs.items() if v is not None}}
    try:
        return template.format(**fields)
    except (KeyError, IndexError):
        return template
