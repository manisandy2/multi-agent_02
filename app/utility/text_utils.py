from functools import lru_cache
from typing import Optional, Union, Dict

from app.core.review_constants import (
    COMPILED_PATTERNS,
    ATTRIBUTE_KEYWORDS,
    EMOTION_KEYWORDS
)


# -----------------------
# NAME NORMALIZATION
# -----------------------
@lru_cache(maxsize=10000)
def normalize_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None

    n = name.strip()
    if not n:
        return None

    # Remove digits & special chars
    n = COMPILED_PATTERNS["digits"].sub("", n)
    n = COMPILED_PATTERNS["special"].sub("", n)

    # Normalize spaces
    n = COMPILED_PATTERNS["whitespace"].sub(" ", n).strip()
    if not n:
        return None

    # Remove duplicate words (case-insensitive)
    words = n.split()
    cleaned = []
    prev = None

    for word in words:
        w_lower = word.lower()
        if w_lower != prev:
            cleaned.append(word)
            prev = w_lower

    if not cleaned:
        return None

    normalized = " ".join(word.title() for word in cleaned)

    # Limit long names
    if len(normalized) > 50:
        normalized = " ".join(normalized.split()[:3])

    return normalized if len(normalized.replace(" ", "")) >= 2 else None


# -----------------------
# STORE TITLE CLEANING
# -----------------------
@lru_cache(maxsize=5000)
def _clean_store_title(raw: Optional[str]) -> str:
    if not raw:
        return ""

    s = raw.strip()

    # Remove domain-like suffix
    if "." in s:
        s = s.split(".")[0].strip()

    # Normalize whitespace
    s = COMPILED_PATTERNS["whitespace"].sub(
        " ", s.replace("\r", " ").replace("\n", " ")
    ).strip()

    # Remove promo words
    match = COMPILED_PATTERNS["promo"].search(s)
    if match:
        s = s[:match.start()].strip()

    # Remove trailing punctuation
    s = COMPILED_PATTERNS["trailing_punct"].sub("", s)

    return s.strip()


@lru_cache(maxsize=5000)
def normalize_store_title(store_location: Optional[str]) -> str:
    if not store_location:
        return "Poorvika"

    cleaned = _clean_store_title(store_location)

    if not cleaned:
        return "Poorvika"

    # Keep brand prefix if already correct
    if cleaned.lower().startswith("poorvika") and len(cleaned) < 80:
        return cleaned

    return cleaned or "Poorvika"


# -----------------------
# STAR RATING PARSER
# -----------------------
def parse_star_rating(
    raw: Union[str, int, float, None],
    default: int = 3
) -> int:
    if raw is None:
        return default

    try:
        rating = int(round(float(raw)))
        return max(1, min(5, rating))
    except (ValueError, TypeError):
        return default


# -----------------------
# ATTRIBUTE + EMOTION DETECTION
# -----------------------
def detect_attributes_and_emotion(text: str) -> Dict:
    text_l = (text or "").lower().strip()

    if not text_l:
        return {
            "attributes": ["other"],
            "emotion": "other"
        }

    # Detect attributes
    detected_attrs = {
        attr
        for attr, keywords in ATTRIBUTE_KEYWORDS.items()
        if any(kw in text_l for kw in keywords)
    }

    # Detect emotion (score-based)
    emotion_scores = {
        emo: sum(text_l.count(kw) for kw in kws)
        for emo, kws in EMOTION_KEYWORDS.items()
    }

    emotion = max(emotion_scores, key=emotion_scores.get)

    if emotion_scores[emotion] == 0:
        emotion = "other"

    return {
        "attributes": list(detected_attrs) if detected_attrs else ["other"],
        "emotion": emotion
    }