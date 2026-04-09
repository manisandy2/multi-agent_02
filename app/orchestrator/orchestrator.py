import asyncio
import logging

from app.agents.reply_agent import reply_agent
from app.tools.crm_tool import complaint_agent
from app.agents.supervisor_agent import supervisor_agent
from app.utility.helper import build_complaint_link


logger = logging.getLogger(__name__)

# =========================
# Main ORCHESTRATOR
# =========================

async def process_review_task(data:dict) -> dict:
    job_id = data.get("job_id", "unknown")
    logger.info(f"[{job_id}] Processing started")

    try:
        # -------------------------
        # INPUT
        # -------------------------
        review = data.get("review", "")
        rating = data.get("rating", 0)
        reviewer = data.get("reviewer", "anonymous")
        store = data.get("location_name", "our store")

        # -------------------------
        # SUPERVISOR (DECISION)
        # -------------------------
        decision = await supervisor_agent(
            review=review,
            rating=rating,
            reviewer=reviewer,
            store=store,
        ) or {}
        decision = _enforce_rules(decision, rating)
        
        # -------------------------
        # COMPLAINT (OPTIONAL)
        # -------------------------
        # complaint_link = None

        # if decision.get("create_ticket"):
        #     complaint_link = await _safe_create_complaint(data, job_id)
        # else:
        #     complaint_task = asyncio.sleep(0, result=None)
        # -------------------------
        # SENSITIVE CHECK
        # -------------------------

        if _is_sensitive(review):
            link = await _safe_create_complaint(data, job_id)
            reply_text = "We request you to please raise a ticket using the link below so our team can assist you further."
            if link:
                reply_text += f" Link: {link}"
            return {
                "job_id": job_id,
                "status": "success",
                "type": "blocked",
                "reply": reply_text,
                "complaint_link": link,
                "decision": decision,
            }
        
        # -------------------------
        # PARALLEL TASKS
        # -------------------------

        complaint_task = (
            _safe_create_complaint(data, job_id)
            if decision.get("create_ticket")
            else asyncio.sleep(0, result=None)
        )

        # -------------------------
        # REPLY (ALWAYS)
        # -------------------------
        reply_task =  _generate_reply(
            review, rating, reviewer, store
        )

        complaint_link, reply = await asyncio.gather(
            complaint_task,
            reply_task 
        )

        # -------------------------
        # ADD LINK (NO RE-GENERATION)
        # -------------------------
        if complaint_link:
            reply = f"{reply} Kindly share more details here: {complaint_link}"



        # -------------------------
        # SUPERVISOR (VALIDATE + FIX)
        # -------------------------
        reply = await _validate_reply(
            review, rating, reviewer, store, reply
        )

        if decision.get("create_ticket") and not complaint_link:
            decision["action"] = "reply"
            decision["create_ticket"] = False
        
        return {
            "job_id": job_id,
            "status": "success",
            "type": "complaint_and_reply" if complaint_link else "reply",
            "complaint_link": complaint_link,
            "reply": reply,
            "decision": decision,
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Processing failed")

        return _error_response(
            job_id=job_id,
            message="Processing failed",
            details=str(e),
        )
    
# =========================
# Rule Enforcement
# =========================
def _enforce_rules(decision: dict, rating: int) -> dict:
    logger.debug(f"Enforcing rules for rating: {rating}")
    if rating <= 2:
        decision.update({
        "create_ticket" : True,
        "action" : "complaint_and_reply",
        "severity" : "high",
        })
    else:
        decision.update({
        "create_ticket" : False,
        "action" : "reply",
        })
    return decision

# =========================
# SENSITIVE CHECK
# =========================
def _is_sensitive(review: str) -> bool:
    if not review:
        return False
    keywords = ["fraud", "scam", "police", "legal", "court", "cheating"]
    return any(k in review.lower() for k in keywords)


# =========================
# SAFE COMPLAINT
# =========================
async def _safe_create_complaint(data: dict, job_id: str) -> str | None:
    try:
        ticket = await complaint_agent(data)

        if ticket.get("status") == "created":
            ticket_id = ticket.get("ticket_id")
            if ticket_id:
                return build_complaint_link(ticket_id)

        logger.warning(f"[{job_id}] Complaint not created")
        return None

    except Exception as e:
        logger.error(f"[{job_id}] Complaint failed: {e}")
        return None

# =========================
# REPLY GENERATION
# =========================
async def _generate_reply(
    review: str,
    rating: int,
    reviewer: str,
    store: str,
    complaint_link: str = None,
) -> str:

    for _ in range(2):  # retry max 2 times
        try:
            reply = await reply_agent(
                review,
                rating,
                reviewer,
                store,
                complaint_link=complaint_link,
            )

            if reply and isinstance(reply, str):
                reply = reply.strip()

                if not _is_bad_reply(reply, rating):
                    return reply

        except Exception as e:
            logger.warning(f"Reply generation failed: {e}")

    # fallback
    if complaint_link:
        return f"Thank you for your feedback. Please contact us here: {complaint_link}"

    return "Thank you for your feedback. We will look into this."

# =========================
# VALIDATION + CORRECTION
# =========================
async def _validate_reply(review, rating, reviewer, store, reply):

    try:
        final = await supervisor_agent(
            review=review,
            rating=rating,
            reviewer=reviewer,
            store=store,
            reply=reply,
            mode="validate",
        ) or {}

        if final.get("approved", True):
            return reply

        return final.get(
            "corrected_reply",
            "Thank you for your feedback. We will look into this."
        )

    except Exception as e:
        logger.warning(f"Validation failed: {e}")
        return reply  # fail-safe
    
# =========================
# REPLY QUALITY CHECK
# =========================
def _is_bad_reply(reply: str, rating: int) -> bool:
    if not reply:
        return True

    words = reply.split()

    if len(words) < 10:
        return True

    if rating <= 2 and not any(w in reply.lower() for w in ["sorry", "apologize", "apologies", "regret"]):
        return True

    return False


# =========================
# Error Response
# =========================
def _error_response(job_id: str, message: str, details: str = None):
    return {
        "job_id": job_id,
        "status": "failed",
        "error": {
            "message": message,
            "details": details,
        },
    }