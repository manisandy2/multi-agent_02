import asyncio
import json
import logging
from typing import Dict

from google import genai
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.supervisor import SupervisorResponse

settings = Settings()
logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.GEMINI_API_KEY)

NEGATIVE_KEYWORDS = [
    "bad", "worst", "poor", "issue", "problem",
    "delay", "late", "damaged", "broken",
    "not working", "refund", "fraud", "cheated",
]

STRONG_NEGATIVE_KEYWORDS = [
    "fraud", "cheated", "scam", "worst experience",
    "never again", "very bad", "pathetic",
]

SUPERVISOR_PROMPT = """
You are a Review Supervisor AI.

STRICT RULES:
- Return ONLY valid JSON
- Do NOT include explanation or markdown
- Output must start with {{ and end with }}

DECISION RULES:
- Serious complaint → create_ticket = true
- Minor issue or positive → create_ticket = false

FORMAT:
{{
    "sentiment": "positive|neutral|negative",
    "severity": "low|medium|high",
    "action": "reply|complaint",
    "create_ticket": true or false,
    "reason": "string"
}}

Review: "{review}"
Rating: {rating}
"""


def _parse_json(text: str) -> Dict | None:
    if not text:
        return None

    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _fallback_decision(review: str, rating: int) -> Dict:
    review_lower = review.lower()

    is_strong_negative = any(kw in review_lower for kw in STRONG_NEGATIVE_KEYWORDS)
    is_negative = any(kw in review_lower for kw in NEGATIVE_KEYWORDS)

    if rating <= 2 or is_strong_negative:
        sentiment, severity = "negative", "high"
    elif rating == 3 or is_negative:
        sentiment, severity = "neutral", "medium"
    else:
        sentiment, severity = "positive", "low"

    create_ticket = severity == "high"

    return {
        "sentiment": sentiment,
        "severity": severity,
        "action": "complaint" if create_ticket else "reply",
        "create_ticket": create_ticket,
        "reason": "Fallback rule (rating + keyword analysis)",
    }


async def supervisor_ai(review: str, rating: int) -> Dict:
    print("process start supervisor ai")
    if rating <= 2:
        return _fallback_decision(review, rating)

    try:
        prompt = SUPERVISOR_PROMPT.format(review=review, rating=rating)

        response = await asyncio.wait_for(
            asyncio.to_thread(
                client.models.generate_content,
                model=settings.GEMINI_MODEL,
                contents=prompt,
            ),
            timeout=8,
        )

        raw_text = response.text.strip() if response.text else ""
        logger.debug(f"Supervisor raw response: {raw_text}")

        parsed = _parse_json(raw_text)
        if not parsed:
            raise ValueError("Could not parse JSON from Gemini response")

        validated = SupervisorResponse(**parsed)
        print(validated.model_dump())
        print("end supervisier ai")
        return validated.model_dump()

    except (ValidationError, ValueError) as e:
        logger.warning(f"Supervisor validation error: {e}")
    except Exception as e:
        logger.error(f"Supervisor AI error: {e}")

    return _fallback_decision(review, rating)