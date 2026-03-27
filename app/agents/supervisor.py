import asyncio
import json
import logging
from typing import Dict

from google import genai
from pydantic import ValidationError
from utility.helper import _call_gemini
from app.core.config import Settings
from app.schemas.supervisor import SupervisorResponse
from app.prompts.supervisor_prompt import SUPERVISOR_PROMPT
import re

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




def _parse_json(text: str) -> Dict | None:
    if not text:
        return None

    text = text.strip()

    # Extract first JSON object
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None

def supervisor_decision(review: str, rating: int) -> dict:
    review_lower = review.lower()

    if rating <= 2:
        return {
            "sentiment": "negative",
            "action": "complaint",
            "create_ticket": True
        }

    if rating == 3:
        return {
            "sentiment": "neutral",
            "action": "reply",
            "create_ticket": False
        }

    return {
        "sentiment": "positive",
        "action": "reply",
        "create_ticket": False
    }

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

async def _call_gemini(prompt: str, retries: int = 2):
    for attempt in range(retries):
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                ),
                timeout=8,
            )
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait_time = 2 ** attempt  # exponential backoff
            logger.warning(f"Retry {attempt+1} failed: {e}, retrying in {wait_time}s")
            await asyncio.sleep(wait_time)


async def supervisor_ai(review: str, rating: int) -> Dict:
    try:
        review = " ".join(review.strip().split())
        safe_review = review.replace("{", "{{").replace("}", "}}")

        prompt = SUPERVISOR_PROMPT.format(
            rating=rating,
            review=review )

        response = await _call_gemini(prompt)
        print(f"Gemini response object: {response}")
        raw_text = response.text.strip() if response.text else ""
        logger.debug(f"Supervisor raw response: {raw_text}")

        parsed = _parse_json(raw_text)
        if not parsed:
            raise ValueError("Could not parse JSON from Gemini response")

        validated = SupervisorResponse(**parsed)
        print(f"Validated supervisor output: {validated.model_dump()}")
        data = validated.model_dump()
        if data["severity"] == "low" and data["create_ticket"]:
            logger.warning("Fixing inconsistent AI output")
            data["create_ticket"] = False
            data["action"] = "reply"
        return data
    except (ValidationError, ValueError) as e:
        logger.warning(f"Supervisor validation error: {e}")
    except Exception as e:
        logger.error(
            "Supervisor AI error",
            extra={
                "review": review[:100],
                "rating": rating,
                "error": str(e),
            }
        )

    return _fallback_decision(review, rating)