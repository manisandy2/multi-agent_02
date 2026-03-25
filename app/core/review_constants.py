import re

# 🎯 Reply tones
REPLY_TONES = [
    "friendly and warm",
    "professional and courteous",
    "empathetic and caring",
    "enthusiastic and grateful",
    "sincere and understanding",
]

# 🟢 Positive
POSITIVE_OPENINGS = [
    "Thank you so much for your wonderful feedback!",
    "We're delighted to hear about your positive experience!",
    "Your kind words truly made our day!",
]

# 🟡 Neutral
NEUTRAL_OPENINGS = [
    "Thank you for taking the time to share your feedback.",
    "We appreciate you sharing your experience with us.",
    "Your feedback is valuable to us.",
]

# 🔴 Negative
NEGATIVE_OPENINGS = [
    "We sincerely apologize for your experience.",
    "We're truly sorry to hear about the issues you faced.",
    "Your concerns are important to us, and we apologize.",
]

# 😊 Emotion detection
EMOTION_KEYWORDS = {
    "joy": ["happy", "excellent", "great", "good", "love", "delighted", "pleased", "awesome", "thanks", "thank"],
    "sadness": ["sad", "disappointed", "unhappy", "sorrow", "regret"],
    "anger": ["angry", "hate", "furious", "annoyed", "terrible", "worst"],
}

# 🧩 Attribute detection
ATTRIBUTE_KEYWORDS = {
    "product": ["product", "device", "phone", "model", "item", "iphone", "samsung", "mobile"],
    "service": ["service", "support", "warranty", "repair", "assistance"],
    "delivery": ["delivery", "shipping", "courier", "arrival"],
    "pricing": ["price", "pricing", "cost", "expensive", "cheap", "emi"],
    "staff": ["staff", "salesperson", "manager", "employee"],
    "store_experience": ["store", "showroom", "ambience", "queue", "waiting"],
}

# ⚙️ Precompiled regex (performance optimized)
COMPILED_PATTERNS = {
    "digits": re.compile(r"[0-9]"),
    "special": re.compile(r"[^\w\s\-\']"),
    "whitespace": re.compile(r"\s+"),
    "promo": re.compile(
        r"\b(Buy\s+Latest|Buy\s+Now|Buy|Latest|Premium|Offers?|Sale|Discount)\b",
        re.IGNORECASE,
    ),
    "trailing_punct": re.compile(r"[\.,;:\s]+$"),
}