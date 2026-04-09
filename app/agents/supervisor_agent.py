import json
import logging
from typing import Dict
from pydantic import ValidationError
from app.services.gemini_service import call_gemini
from app.schemas.supervisor import SupervisorResponse
from app.prompts.supervisor_prompt import SUPERVISOR_PROMPT
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
    
async def supervisor_agent(
        review: str,
        rating: int,
        reviewer: str = "anonymous",
        store: str = "unknown",
        reply: str | None = None,
        mode: str = "analyze"   # "full" for classification + response, "
        ) -> Dict:
    print(f"Supervisor Agent called with review: {review}, rating: {rating}, reviewer: {reviewer}, store: {store}, mode: {mode}")   
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

            compliance_prompt = COMPLIANCE_PROMPT.format_map(
                {"review": safe_review,
                 "rating": rating,
                 "reply": reply}
            )

            validation_result = await call_gemini(compliance_prompt, agent_name="compliance_agent", expect_json=True)

            if not validation_result or validation_result.get("status") != "success":
                raise ValueError("LLM compliance validation failed")

            val_parsed = validation_result.get("content")

            if not val_parsed or not isinstance(val_parsed, dict):
                logger.warning("Compliance validation failed to parse JSON, falling back.")
                return {"approved": False, "corrected_reply": reply}

            return {
                "approved": val_parsed.get("approved", False),
                "corrected_reply": val_parsed.get("corrected_reply", reply),
                "issues": [val_parsed.get("suggestions")] if val_parsed.get("suggestions") else [],
                "manual_response_required": val_parsed.get("manual_response_required", False) 
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
        
        llm_result =  await call_gemini(prompt, agent_name="supervisor_agent", expect_json=True)

        if not llm_result or llm_result.get("status") != "success":
            raise ValueError("LLM failed")

        parsed = llm_result.get("content", {})
        if not parsed or not isinstance(parsed, dict):
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

# from app.core.state import ReviewState
# from app.agents.supervisor_agent import supervisor_agent


# class SupervisorAgent:

#     async def run(self, state: ReviewState) -> ReviewState:

#         state.current_agent = "supervisor"
#         state.log("Supervisor started")

#         # -------- DECISION --------
#         if state.next_agent == "decision":

#             result = await supervisor_agent(
#                 review=state.review,
#                 rating=state.rating,
#                 reviewer=state.reviewer,
#                 store=state.location_name,
#                 mode="analyze"
#             )

#             state.decision = result
#             state.add_history("supervisor", "decision", result)

#             # routing
#             if state.rating and state.rating <= 2:
#                 state.next_agent = "complaint"
#             else:
#                 state.next_agent = "reply"

#             return state

#         # -------- VALIDATION --------
#         if state.next_agent == "validation":

#             result = await supervisor_agent(
#                 review=state.review,
#                 rating=state.rating,
#                 reviewer=state.reviewer,
#                 store=state.location_name,
#                 reply=state.draft_response,
#                 mode="validate"
#             )

#             state.validation = result
#             state.add_history("supervisor", "validation", result)

#             if result.get("approved", True):
#                 state.final_response = state.draft_response
#             else:
#                 state.final_response = result.get(
#                     "corrected_reply",
#                     state.draft_response
#                 )

#             state.complete()
#             return state

#         return state