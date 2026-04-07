import json
import logging
from typing import Dict
from pydantic import ValidationError
from app.services.gemini_service import _call_gemini
from app.schemas.supervisor import SupervisorResponse
from app.prompts.supervisor_prompt import SUPERVISOR_PROMPT
import re

logger = logging.getLogger(__name__)

# =========================
# JSON Parser
# =========================
def _parse_json(text: str) -> Dict | None:
    if not text:
        return None

    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON block
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None

# =========================
# Fallback
# =========================

def _fallback_decision(review: str, rating: int,reviewer: str, store: str) -> Dict:
    if rating <= 2:
        return {
            "classification": {"sentiment": "negative", "issue_type": "other", "rating": rating},
            "issues": ["Customer dissatisfaction"],
            "severity": "high",
            "action": "complaint",
            "create_ticket": True,
            "response": "We sincerely apologize. Your issue will be addressed.",
            "confidence": 0.5,
            "reason": "fallback"
        }

    return {
        "classification": {
            "sentiment": "positive" if rating >= 4 else "neutral" if rating == 3 else "negative",
            "issue_type": "other", 
            "rating": rating},
        "issues": [],
        "severity": "low" if rating >= 3 else "high",
        "action": "reply" if rating >= 3 else "complaint",
        "create_ticket": rating <= 2,
        "response": _fallback_response_text(review, rating, reviewer, store),
        "confidence": 0.5, 
        "reason": "fallback"
    }

def _fallback_response_text(review: str, rating: int, reviewer: str, store: str) -> str:

    name = reviewer or "Customer"
    store_name = store or "our store"

    # Positive
    if rating >= 4:
        return f"Hi {name}, thank you for your positive feedback about {store_name}. We’re glad you had a good experience and look forward to serving you again."

    # Neutral
    if rating == 3:
        return f"Hi {name}, thank you for your feedback about {store_name}. We appreciate your input and will use it to improve our service."

    # Negative
    return f"Hi {name}, we’re sorry to hear about your experience at {store_name}. Please share more details so we can look into this and assist you further."

# =========================
# Supervisor Agent
# =========================
    
async def supervisor_agent(
        review: str,
        rating: int,
        reviewer: str = "anonymous",
        store: str = "unknown",
        reply: str = None,
        mode: str = "decision"   # "full" for classification + response, "
        ) -> Dict:
    
    try:
        if mode not in ["analyze", "validate"]:
            logger.warning(f"Unknown mode: {mode}, defaulting to analyze")
            mode = "analyze"

        review = " ".join((review or "").strip().split())
        safe_review = review.replace("{", "{{").replace("}", "}}")

        # =========================
        # MODE: VALIDATION
        # =========================
        if mode == "validate":
            if not reply:
                return {"approved": False, 
                        "corrected_reply": "Thank you for your feedback. We will look into this."}

            text = reply.lower()
            words = text.split()

            issues = []

            # =========================
            # HARD SAFETY CHECK
            # =========================
            banned = [
                "refund processed",
                "legal action",
                "guarantee",
                "100%",
                "we will compensate",
                "you are right we made a mistake"
            ]

            if any(b in text for b in banned):
                logger.warning("Validation failed: unsafe claim detected")

                return {
                    "approved": False,
                    "corrected_reply": "Thank you for your feedback. Please contact our support team for further assistance.",
                    "issues": ["unsafe_claim"]
                }
    
            if len(words) < 10:
                logger.warning("Validation failed: too short")
                issues.append("too short")

            if rating >= 3:
                if not any(w in text for w in ["thank", "thanks", "appreciate", "grateful"]):
                    logger.warning("Validation failed: missing gratitude")
                    issues.append("missing gratitude")

            if rating <= 2 and not any(w in text for w in ["sorry", "apologize", "apologies", "regret"]):
                logger.warning("Validation failed: missing apology")
                issues.append("missing apology")
            
            if not issues:
                logger.info(f"Validation passed (rating={rating})")
                return {"approved": True}
            
            logger.warning(f"Validation issues: {issues}")

            # 🔥 AUTO FIX (THIS WAS MISSING)
            corrected = reply.strip()

            if "thank" not in text and rating >= 3:
                corrected = "Thank you for your feedback. " + corrected

            if rating <= 2 and not any(w in text for w in ["sorry", "apologize", "apologies", "regret"]):
                corrected = "We sincerely apologize for your experience. " + corrected

            if len(corrected.split()) < 10:
                corrected += " We truly value your feedback and will work on improving our service."

            logger.warning(f"Reply corrected: {issues}")

            return {
                "approved": False,
                "corrected_reply": corrected,
                "issues": issues
            }


        # =========================
        # MODE: DECISION (LLM)
        # =========================
        prompt = SUPERVISOR_PROMPT.format_map(
            {"review": safe_review,
            "rating": rating,
            "reviewer": reviewer,
            "store": store,}
        )
        
        llm_result =  await _call_gemini(prompt)

        if not llm_result or llm_result.get("status") != "success":
            raise ValueError("LLM failed")

        raw_text = llm_result.get("content", "")
        raw_text = raw_text.replace("```json", "").replace("```", "").strip()

        parsed = _parse_json(raw_text)
        if not parsed:
            raise ValueError("Invalid JSON from LLM")

        validated = SupervisorResponse(**parsed)
        data = validated.model_dump()

        data.setdefault("issues", [])
        data.setdefault("response", "")

        data["confidence"] = 0.9
        logger.info(
            f"Supervisor decision: action={data.get('action')} "
            f"ticket={data.get('create_ticket')} "
            f"confidence={data.get('confidence')}"
            )
        return data
    
    except (ValidationError, ValueError) as e:
        logger.warning(f"Supervisor validation error: {e}")

    except Exception as e:
        logger.exception(f"Supervisor AI error: {e}")

    if mode == "validate":
        return {
        "approved": False,
        "corrected_reply": "Thank you for your feedback. We will look into this."
    }
    
    return _fallback_decision(review or "", rating,reviewer, store)