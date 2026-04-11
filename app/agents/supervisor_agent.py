import json
import logging
from typing import Dict
from pydantic import ValidationError
from app.services.gemini_service import call_gemini
from app.schemas.supervisor import SupervisorResponse
from app.prompts.decision_prompt import DECISION_AGENT_PROMPT
from app.prompts.compliance_prompt import COMPLIANCE_PROMPT
import re

logger = logging.getLogger(__name__)

# =========================
# JSON Parser
# =========================
def _parse_json(text: str) -> Dict | list | None:
    if not text:
        return None

    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: extract JSON block
    match = re.search(r"(\{.*?\}|\[.*?\])", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None

# =========================
# Fallback
# =========================

def _fallback_decision(review: str, rating: int, reviewer: str, store: str) -> Dict:
    if rating <= 2:
        return {
            "classification": {"sentiment": "negative", "issue_type": "other", "rating": rating},
            "issues": ["Customer dissatisfaction"],
            "severity": "high",
            "action": "complaint",
            "create_ticket": True,
            "response": _fallback_response_text(review, rating, reviewer, store),
            "confidence": 0.5,
            "reason": "fallback"
        }

    return {
        "classification": {
            "sentiment": "positive" if rating >= 4 else "neutral",
            "issue_type": "other",
            "rating": rating},
        "issues": [],
        "severity": "low",
        "action": "reply",
        "create_ticket": False,
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
    
async def decision_agent(
        review: str,
        rating: int,
        reviewer: str = "anonymous",
        store: str = "unknown",
        mode: str = "analyze"   # "full" for classification + response, "
        ) -> Dict:
    
    print(f"Decision Agent called with review: {review}, rating: {rating}")
   
    try:

        review = " ".join((review or "").strip().split())[:1000]  # Clean and truncate review
        safe_review = review.replace("{", "{{").replace("}", "}}")

    

        # =========================
        # MODE: DECISION (LLM)
        # =========================
        prompt = DECISION_AGENT_PROMPT.format_map(
            {"review": safe_review,
            "rating": rating,
            "reviewer": reviewer,
            "store": store,}
        )
        
        llm_result =  await call_gemini(
            prompt, agent_name="decision_agent", expect_json=True)

        if not llm_result or llm_result.get("status") != "success":
            raise ValueError("LLM failed")

        parsed = llm_result.get("content", {})
        if not parsed or not isinstance(parsed, dict):
            raise ValueError("Invalid JSON from LLM")

        validated = SupervisorResponse(**parsed)
        data = validated.model_dump()

        data.setdefault("issues", [])
        data.setdefault("draft_reply", "")
        data.setdefault("reason", "LLM decision")
        data.setdefault("confidence", 0.9)
        
        logger.info(
            f"Supervisor decision: action={data.get('action')} "
            f"ticket={data.get('create_ticket')} "
            f"confidence={data.get('confidence')}"
            )
        
        return data
    
    except (ValidationError, ValueError) as e:
        logger.warning(f"Decision Agent validation error: {e}")

    except Exception as e:
        logger.exception(f"Decision Agent error: {e}")

    
    return _fallback_decision(review or "", rating,reviewer, store)

async def compliance_agent(
    review: str,
    rating: int,
    draft_reply: str,
    issue_type: str,
    reviewer: str = "anonymous",
    store: str = "unknown",
) -> dict:

    try:
        if not draft_reply:
            return {
                "approved": False,
                "final_reply": "Thank you for your feedback. We will look into this.",
                "reason": "Empty reply",
                "action": "fallback",
                "confidence": 0.5
            }

        # 🔥 Rule-based overrides FIRST (important)

        # Fraud / harassment / hygiene → force escalation
        if issue_type in ["fraud", "harassment", "hygiene"]:
            return {
                "approved": False,
                "final_reply": "We take this matter seriously. Kindly share more details through the link provided so we can investigate further.",
                "reason": "Sensitive issue - escalation required",
                "action": "escalated",
                "confidence": 0.95
            }

        # Staff issue → safe wording (no admission)
        if issue_type == "staff":
            safe_reply = (
                f"Dear {reviewer or 'Customer'}, we’re sorry for your experience at {store}. "
                "We will look into this matter and appreciate your feedback."
            )

            return {
                "approved": False,
                "final_reply": safe_reply,
                "reason": "Staff issue - avoid public admission",
                "action": "corrected",
                "confidence": 0.9
            }

        # -----------------------------
        # LLM VALIDATION (Secondary)
        # -----------------------------
        prompt = COMPLIANCE_PROMPT.format_map({
            "review": review,
            "rating": rating,
            "reply": draft_reply,
            "issue_type": issue_type,
            "reviewer": reviewer,
            "store": store
        })

        result = await call_gemini(
            prompt,
            agent_name="compliance_agent",
            expect_json=True
        )

        if not result or result.get("status") != "success":
            raise ValueError("Compliance LLM failed")

        parsed = result.get("content")

        if not isinstance(parsed, dict):
            raise ValueError("Invalid JSON from compliance")

        corrected = parsed.get("corrected_reply")

        # ✅ If no change → approve
        if not corrected or corrected.strip() == draft_reply.strip():
            return {
                "approved": True,
                "final_reply": draft_reply,
                "reason": "Reply is compliant",
                "action": "approved",
                "confidence": 0.95
            }

        # ✅ If changed → corrected
        return {
            "approved": False,
            "final_reply": corrected,
            "reason": parsed.get("reason", "Improved clarity/compliance"),
            "action": "corrected",
            "confidence": parsed.get("confidence", 0.9)
        }

    except Exception as e:
        logger.exception(f"Compliance Agent error: {e}")

        return {
            "approved": False,
            "final_reply": draft_reply,
            "reason": "Adjusted response for compliance",
            "action": "fallback",
            "confidence": 0.5
        }