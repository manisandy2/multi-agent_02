import logging
from typing import Optional
from app.services.gemini_service import _call_gemini
from app.prompts.reply_prompt import REPLY_PROMPT

logger = logging.getLogger(__name__)

# =========================
# Prompt Builder
# =========================

def build_prompt(review, rating, reviewer, store, complaint_link):
    review = review or ""
    clean_review = " ".join(review.strip().split())
    safe_review = clean_review.replace("{", "{{").replace("}", "}}")

    instruction = f"- Include this support link: {complaint_link}" if complaint_link else ""

    return REPLY_PROMPT.format(
        reviewer=reviewer or "Customer",
        store=store or "our store",
        rating=rating,
        review=safe_review,
        complaint_instruction=instruction,
    )


# =========================
# Fallback Reply
# =========================

def fallback_reply(rating: int, store: str,complaint_link:Optional[str] = None) -> str:
    store = store or "our store"

    if rating >= 4:
        return (
            f"Thank you for your feedback! We're glad you had a great experience at {store}. "
            f"We look forward to serving you again."
        )
    if rating <= 2:
        base = (
            f"We’re sorry to hear about your experience at {store}. "
            f"We truly understand your concern and are working to make things right."
        )
        if complaint_link:
            base += f" You can reach us here: {complaint_link}"
        return base
    return (
        f"Thank you for your feedback. We appreciate your input and will continue "
        f"to improve our services at {store}."
    )

# =========================
# Validation
# =========================

def validate_reply(reply: str) -> str:
    #  enforce single paragraph
    reply = reply.replace("\n", " ").strip()
    words = reply.split()

    # enforce minimum length
    if len(words) < 10:
        return ""

    if len(words) > 90:
        reply = " ".join(words[:90])

    return reply


# =========================
# Reply Agent
# =========================
async def reply_agent(
    review: str,
    rating: int,
    reviewer: str,
    store: str,
    complaint_link: Optional[str] = None,
) -> str:
   
    prompt = build_prompt(review, rating, reviewer, store, complaint_link)

    try:
        llm_result = await _call_gemini(prompt)

        if llm_result.get("status") != "success":
            raise ValueError("LLM failed")
         
        reply = llm_result.get("content", "").strip()
        
        if not reply or len(reply) < 10:
            raise ValueError("Invalid reply")
        

    except Exception as e:
        logger.error(
            f"Reply agent failed | rating={rating}, store={store}, review={review[:50]}, error={e}"
        )
        return fallback_reply(rating, store, complaint_link)

    reply = validate_reply(reply)
    
    if not reply:
        return fallback_reply(rating, store, complaint_link)

    if complaint_link and complaint_link not in reply:
        reply = reply.rstrip(". ") + f". You can reach us here: {complaint_link}"

    return reply