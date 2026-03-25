import json
import logging
from typing import Optional
import asyncio
from app.services.gemini_service import generate_reply
from app.utility.json_utils import safe_parse_json
from app.utility.reply_utils import build_reply_template
from app.core.config import Settings
from google import genai


logger = logging.getLogger(__name__)
settings = Settings()

client = genai.Client(api_key=settings.GEMINI_API_KEY)

async def reply_agent(
    review: str,
    rating: int,
    reviewer: str,
    store: str,
    complaint_link: str = None,
    ticket_id: str = None
) -> str:
    """
    Clean reply generator (LLM + fallback)
    """

    # 🎯 Sentiment-based tone
    if rating >= 4:
        tone = "positive"
    elif rating <= 2:
        tone = "negative"
    else:
        tone = "neutral"

    prompt = f"""
        You are a customer support assistant.

        Write a professional reply.

        Rules:
        - Single paragraph
        - 60–80 words
        - No markdown
        - No "Dear"
        - No closing (no Regards)

        Customer: {reviewer}
        Store: {store}
        Rating: {rating}
        Review: "{review}"

        Instructions:
        - Positive → thank customer
        - Neutral → acknowledge feedback
        - Negative → apologize + assure resolution
        {f"- Include this support link: {complaint_link}" if complaint_link else ""}
"""

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=settings.GEMINI_MODEL,
            contents=prompt
        )

        reply = response.text.strip() if response.text else ""

        if not reply:
            raise ValueError("Empty reply")

    except Exception as e:
        logger.error(f"Reply agent failed: {e}")
        reply = fallback_reply(review, rating, store)

    # ✅ Add ticket reference if complaint exists
    if ticket_id:
        reply += f" Reference ID: {ticket_id}"

    return reply


# -----------------------
# FALLBACK
# -----------------------
def fallback_response(
    review: str,
    rating: int,
    name: str,
    location: str,
    complaint_link: Optional[str],
) -> dict:

    sentiment = (
        "positive" if rating >= 4
        else "negative" if rating <= 2
        else "neutral"
    )

    return {
        "sentiment": sentiment,
        "emotion": "other",
        "attributes": ["other"],
        "star_rating": rating,
        "reply": build_reply_template(
            name,
            location,
            rating,
            sentiment,
            complaint_link,
        ),
    }

def fallback_reply(review: str, rating: int, store: str) -> str:
    if rating >= 4:
        return f"Thank you for your feedback! We're glad you had a great experience at {store}. We look forward to serving you again."

    elif rating <= 2:
        return f"We sincerely apologize for your experience at {store}. We understand your concern and will work towards resolving it. Please contact our support team for assistance."

    return f"Thank you for your feedback. We appreciate your input and will continue improving your experience at {store}."