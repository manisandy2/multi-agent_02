import logging
from typing import Optional
from app.utility.helper import _call_gemini
from app.prompts.reply_prompt import REPLY_PROMPT

logger = logging.getLogger(__name__)


def build_prompt(review, rating, reviewer, store, complaint_link):
    clean_review = " ".join(review.strip().split())
    safe_review = clean_review.replace("{", "{{").replace("}", "}}")

    instruction = f"- Include this support link: {complaint_link}" if complaint_link else ""

    return REPLY_PROMPT.format(
        reviewer=reviewer or "Customer",
        store=store,
        rating=rating,
        review=safe_review,
        complaint_instruction=instruction,
    )



def fallback_reply(rating: int, store: str,complaint_link:Optional[str] = None) -> str:
    if rating >= 4:
        return (
            f"Thank you for your feedback! We're glad you had a great experience at {store}. "
            f"We look forward to serving you again."
        )
    if rating <= 2:
        base = (
            f"We sincerely apologize for your experience at {store}. "
            f"We understand your concern and will work towards resolving it."
        )
        if complaint_link:
            base += f" You can reach us here: {complaint_link}"
        return base
    return (
        f"Thank you for your feedback. We appreciate your input and will continue "
        f"to improve our services at {store}."
    )

def validate_reply(reply: str) -> str:
    #  enforce single paragraph
    reply = reply.replace("\n", " ").strip()
    words = reply.split()

    # enforce minimum length
    if len(words) < 20:
        return ""

    if len(words) > 90:
        reply = " ".join(words[:80])

    return reply


async def reply_agent(
    review: str,
    rating: int,
    reviewer: str,
    store: str,
    complaint_link: Optional[str] = None,
) -> str:
   
    prompt = build_prompt(review, rating, reviewer, store, complaint_link)

    try:
        response = await _call_gemini(prompt)

        reply = response.text.strip() if response.text else ""

        if not reply or len(reply) < 10:
            raise ValueError("Invalid reply from Gemini")

    except Exception as e:
        logger.error(
            "Reply agent failed",
            extra={"rating": rating, "store": store, "error": str(e)}
        )
        return fallback_reply(rating, store, complaint_link)

    reply = validate_reply(reply)
    # print("reply",reply)
    if not reply:
        return fallback_reply(rating, store, complaint_link)

    if complaint_link and complaint_link.lower() not in reply.lower():
        reply = reply.rstrip(".") + f". You can reach us here: {complaint_link}"

    return reply