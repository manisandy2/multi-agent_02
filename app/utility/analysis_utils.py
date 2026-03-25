from typing import Dict

EMOTION_KEYWORDS = {
    "joy": ["happy", "excellent", "great", "good", "love", "delighted", "pleased"],
    "sadness": ["sad", "disappointed", "unhappy"],
    "anger": ["angry", "hate", "furious", "terrible"],
}

ATTRIBUTE_KEYWORDS = {
    "product": ["product", "phone", "device", "mobile"],
    "service": ["service", "support", "repair"],
    "delivery": ["delivery", "shipping"],
    "pricing": ["price", "cost", "expensive"],
    "staff": ["staff", "employee", "manager"],
    "store experience": ["store", "showroom", "waiting"],
}


def detect_attributes_and_emotion(text: str) -> Dict:
    text_l = (text or "").lower()

    detected_attrs = [
        attr for attr, kws in ATTRIBUTE_KEYWORDS.items()
        if any(kw in text_l for kw in kws)
    ]

    emotion_scores = {
        emo: sum(text_l.count(kw) for kw in kws)
        for emo, kws in EMOTION_KEYWORDS.items()
    }

    emotion = max(emotion_scores, key=emotion_scores.get) if emotion_scores else "other"

    return {
        "attributes": detected_attrs or ["other"],
        "emotion": emotion or "other"
    }