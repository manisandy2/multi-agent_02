import asyncio
import logging
from typing import Optional
from google import genai
from app.core.config import Settings


settings = Settings()
logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.GEMINI_API_KEY)

REPLY_PROMPT = """
You are a customer support assistant.

Write a professional reply to a customer review.

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
- Positive (rating >= 4) → thank the customer
- Neutral (rating == 3) → acknowledge the feedback
- Negative (rating <= 2) → apologize and assure resolution
{complaint_instruction}
"""


def _get_complaint_instruction(complaint_link: Optional[str]) -> str:
    if complaint_link:
        return f"- Include this support link: {complaint_link}"
    return ""


def _fallback_reply(rating: int, store: str) -> str:
    if rating >= 4:
        return (
            f"Thank you for your feedback! We're glad you had a great experience at {store}. "
            f"We look forward to serving you again."
        )
    if rating <= 2:
        return (
            f"We sincerely apologize for your experience at {store}. We understand your concern "
            f"and will work towards resolving it. Please contact our support team for assistance."
        )
    return (
        f"Thank you for your feedback. We appreciate your input and will continue "
        
    )

def _validate_reply(reply: str) -> str:
    #  enforce single paragraph
    reply = reply.replace("\n", " ").strip()

    #  enforce length (soft trim)
    words = reply.split()
    if len(words) > 90:
        reply = " ".join(words[:80])

    return reply

async def _generate_with_retry(prompt: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                ),
                timeout=30,  # timeout protection
            )

            text = response.text.strip() if response.text else ""

            if not text:
                raise ValueError("Empty response")

            return text

        except Exception as e:
            logger.warning(f"Gemini attempt {attempt+1} failed: {e}")

            if attempt == retries:
                raise

            await asyncio.sleep(1)  # small backoff

async def reply_agent(
    review: str,
    rating: int,
    reviewer: str,
    store: str,
    complaint_link: Optional[str] = None,
    ticket_id: Optional[str] = None,
) -> str:
    prompt = REPLY_PROMPT.format(
        reviewer=reviewer,
        store=store,
        rating=rating,
        review=review,
        complaint_instruction=_get_complaint_instruction(complaint_link),
    )

    try:
        raw_reply = await _generate_with_retry(prompt)

        reply = _validate_reply(raw_reply)

    except Exception as e:
        logger.error(f"Reply agent failed: {e}")
        reply = _fallback_reply(rating, store)

    return reply