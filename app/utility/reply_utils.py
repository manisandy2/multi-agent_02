import re
import json
import random
from typing import Optional, Dict

from app.core.review_constants import (
    POSITIVE_OPENINGS,
    NEGATIVE_OPENINGS,
    NEUTRAL_OPENINGS,
)


# -----------------------
# BUILD REPLY TEMPLATE
# -----------------------
def build_reply_template(
    customer_name: Optional[str],
    store: str,
    stars: int,
    tone: str = "neutral",
    complaint_link: Optional[str] = None,
) -> str:

    if tone == "positive":
        opening = random.choice(POSITIVE_OPENINGS)

        body = (
            f"{opening} We are delighted that your {stars}-star experience at {store} "
            f"met your expectations. Your feedback motivates our team to continue delivering "
            f"excellent service. We truly appreciate your support and look forward to welcoming you again soon!"
        )

    elif tone == "negative":
        opening = random.choice(NEGATIVE_OPENINGS)

        link_text = (
            f"You can track your complaint here: {complaint_link}. "
            if complaint_link
            else ""
        )

        body = (
            f"{opening} We regret that your experience at {store} did not meet expectations. "
            f"Our team is committed to improving and ensuring a better experience moving forward. "
            f"{link_text}"
            f"We truly value your feedback and appreciate your patience."
        )

    else:
        opening = random.choice(NEUTRAL_OPENINGS)

        body = (
            
            f"We are continuously working to improve and provide better service. "
            f"Thank you for sharing your thoughts, and we hope to serve you even better next time."
        )

    return body.strip()


# -----------------------
# ENFORCE CUSTOMER NAME
# -----------------------
def enforce_customer_name_in_reply(
    reply: str,
    name: Optional[str],
    store: str,
    stars: int,
) -> str:

    if not reply:
        tone = "positive" if stars >= 4 else ("negative" if stars <= 2 else "neutral")
        reply = build_reply_template(name, store, stars, tone)

    name_use = name or "Customer"

    # Replace placeholders
    reply = (
        reply.replace("<Name>", name_use)
        .replace("{customer_name}", name_use)
    )

    # ❌ DO NOT force "Dear" (keep natural tone)
    # Only fix if badly formatted
    if reply.lower().startswith("dear customer"):
        reply = re.sub(
            r"^Dear\s+Customer",
            f"Dear {name_use}",
            reply,
            flags=re.IGNORECASE,
        )

    # Remove formal endings
    reply = re.sub(
        r"\n?(Regards|Best wishes|Warm regards|Sincerely|Thank you),?.*$",
        "",
        reply,
        flags=re.IGNORECASE | re.DOTALL,
    )

    return reply.strip()


# -----------------------
# SAFE JSON PARSER
# -----------------------
def safe_parse_json(raw: str) -> Optional[Dict]:
    if not raw:
        return None

    # First attempt
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # Extract JSON from text (Gemini often adds text)
    start = raw.find("{")
    if start == -1:
        return None

    for end in range(len(raw) - 1, start, -1):
        if raw[end] == "}":
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                continue

    return None