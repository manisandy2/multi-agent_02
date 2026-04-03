import asyncio
import logging

from app.agents.reply_agent import reply_agent
from app.tools.crm_tool import complaint_agent
from app.agents.supervisor import supervisor_ai
from app.utility.helper import build_complaint_link

logger = logging.getLogger(__name__)

# =========================
# Main Entry
# =========================

async def process_review_task(data:dict) -> dict:
    job_id = data.get("job_id")
    print(f"[{job_id}] Starting review processing task")

    try:
        decision = await supervisor_ai(data["review"], data["rating"], data.get("reviewer", "anonymous"))
        decision = _enforce_rules(decision, data["rating"])
        
        logger.info(f"[{job_id}] Final decision: {decision}")

        if decision.get("create_ticket"):
            return await _handle_complaint(job_id, data, decision)

        return await _handle_reply(job_id, data, decision)

    except Exception as e:
        logger.exception(f"[{job_id}] Supervisor failed")

        return _error_response(
            job_id=job_id,
            message="Supervisor failed",
            details=str(e),
        )
    
# =========================
# Rule Enforcement
# =========================
def _enforce_rules(decision: dict, rating: int) -> dict:
    print(f"Enforcing rules for rating: {rating}")
    if rating <= 2:
        decision["create_ticket"] = True
        decision["action"] = "complaint_and_reply"
        decision["severity"] = "high"
    else:
        decision["create_ticket"] = False
        decision["action"] = "reply"

    return decision


# =========================
# Complaint Flow
# =========================
async def _handle_complaint(job_id: str, data: dict, decision: dict) -> dict:
    ticket = await complaint_agent(data)

    # ✅ Handle CRM failure
    if ticket.get("status") != "created":
        logger.error(f"[{job_id}] Complaint creation failed: {ticket}")

        # fallback → still reply without ticket
        reply = await reply_agent(
            data["review"],
            data["rating"],
            data["reviewer"],
            data["location_name"],
        )

        return {
            "job_id": job_id,
            "status": "success",
            "type": "reply_only",
            "complaint_link": complaint_link,
            "error": ticket,
            "reply": reply,
            "decision": decision,
        }

    ticket_id = ticket.get("ticket_id")
    complaint_link = build_complaint_link(ticket_id)

    reply = await reply_agent(
        data["review"],
        data["rating"],
        data["reviewer"],
        data["location_name"],
        complaint_link=complaint_link,
        # ticket_id=ticket_id,
    )

    logger.info(f"[{job_id}] Complaint + reply completed")

    return {
        "job_id": job_id,
        "status": "success",
        "type": "complaint_and_reply",
        # "ticket_id": ticket_id,
        "complaint_link": complaint_link,
        "reply": reply,
        "decision": decision,
    }


# =========================
# Reply Only Flow
# =========================
async def _handle_reply(job_id: str, data: dict, decision: dict) -> dict:
    print(f"[{job_id}] Handling reply flow with decision: {decision}")
    logger.info(f"[{job_id}] Handling reply flow")

    reply = await _safe_reply(data)

    return {
        "job_id": job_id,
        "status": "success",
        "type": "reply",
        "reply": reply,
        "decision": decision,
    }

# =========================
# Safe Reply (Retry + Fallback)
# =========================
async def _safe_reply(data: dict, complaint_link: str = None) -> str:
    print(f"Generating reply for review: '{data['review'][:50]}...' with rating: {data['rating']}")
    for attempt in range(2):
        try:
            reply = await reply_agent(
                data["review"],
                data["rating"],
                data.get("reviewer"),
                data.get("location_name"),
                complaint_link=complaint_link,
            )

            if reply and isinstance(reply, str):
                return reply.strip()

        except Exception as e:
            logger.warning(f"Reply retry {attempt + 1} failed: {e}")

    # ✅ Final fallback reply
    return (
        "We sincerely apologize for your experience. "
        "Your concern has been noted and will be addressed."
    )


# =========================
# Standard Error Response
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