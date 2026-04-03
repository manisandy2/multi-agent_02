import asyncio
import json
import logging
from typing import Dict

from google import genai
from pydantic import ValidationError
from app.utility.helper import _call_gemini
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
    if rating <= 2:
        return {
            "classification": {"sentiment": "negative", "issue_type": "other", "rating": rating},
            "issues": ["Customer dissatisfaction"],
            "severity": "high",
            "action": "complaint",
            "create_ticket": True,
            "response": "We sincerely apologize. Your issue will be addressed.",
            "reason": "fallback"
        }

    return {
        "classification": {"sentiment": "positive", "issue_type": "other", "rating": rating},
        "issues": [],
        "severity": "low",
        "action": "reply",
        "create_ticket": False,
        "response": "Thank you for your feedback!",
        "reason": "fallback"
    }

# async def _call_gemini(prompt: str, retries: int = 2):
#     for attempt in range(retries):
#         try:
#             return await asyncio.wait_for(
#                 asyncio.to_thread(
#                     client.models.generate_content,
#                     model=settings.GEMINI_MODEL,
#                     contents=prompt,
#                 ),
#                 timeout=8,
#             )
#         except Exception as e:
#             if attempt == retries - 1:
#                 raise
#             wait_time = 2 ** attempt  # exponential backoff
#             logger.warning(f"Retry {attempt+1} failed: {e}, retrying in {wait_time}s")
#             await asyncio.sleep(wait_time)

class SafeDict(dict):
    def __missing__(self, key):
        return f"{{{key}}}"
    
def extract_gemini_text(response) -> str:
    try:
        return response.candidates[0].content.parts[0].text.strip()
    except Exception:
        return ""
    
async def supervisor_ai(review: str, rating: int,
                        reviewer: str = "anonymous",
                        store: str = "unknown") -> Dict:
    print(f"Supervisor received review: '{review[:50]}...' with rating: {rating}")
    try:
        review = " ".join(review.strip().split())
        print(f"Cleaned review: '{review[:50]}...'")
        safe_review = review.replace("{", "{{").replace("}", "}}")

        context = {
            "review": safe_review,
            "rating": rating,
            "reviewer": reviewer,
            "store": store,
        }
        prompt = SUPERVISOR_PROMPT.format_map(context)
        print("TYPE OF PROMPT:", type(prompt))
        print("PROMPT SAMPLE:", prompt)
        print(f"Safe review for prompt: '{safe_review[:50]}...'")
        print("========== SUPERVISOR PROMPT START ==========")
        # prompt = SUPERVISOR_PROMPT.format(context)

        print("Context:",context)
        print("========== SUPERVISOR PROMPT END ==========")
        print("#### Calling Gemini with prompt ####")
        response = await asyncio.wait_for(_call_gemini(prompt), timeout=20)
        print("#### ending Gemini with prompt ####")
        print(f"Gemini response object: {response}")

        raw_text = extract_gemini_text(response)
        if not raw_text:
            raise ValueError("Empty Gemini response")
        
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        parsed = _parse_json(raw_text)
        if not parsed:
            raise ValueError("Could not parse JSON from Gemini response")

        validated = SupervisorResponse(**parsed)
        print(f"Validated supervisor output: {validated.model_dump()}")

        data = validated.model_dump()
        # print("supervisier:",data)
        if data["severity"] == "low" and data["create_ticket"]:
            logger.warning("Fixing inconsistent AI output")
            data["create_ticket"] = False
            data["action"] = "reply"

        return data
    except (ValidationError, ValueError) as e:
        logger.warning(f"Supervisor validation error: {e}")
    except Exception :
        logger.exception("Supervisor AI error")

    return _fallback_decision(review, rating)