import asyncio
import logging

from app.agents.reply_agent import reply_agent
from app.tools.crm_tool import complaint_agent
from app.agents.supervisor import supervisor_ai
from app.utility.helper import build_complaint_link

logger = logging.getLogger(__name__)


async def process_review_task(data):
    job_id = data.get("job_id")

    try:
        decision = await supervisor_ai(
            data["review"], data["rating"]
        )

        if decision.get("create_ticket"):
            return await _handle_complaint(job_id, data, decision)

        return await _handle_reply(job_id, data, decision)

    except Exception as e:
        logger.exception(f"[{job_id}] Task failed")

        return _error_response(
            job_id=job_id,
            message="Supervisor failed",
            details=str(e),
        )


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
            "status": "partial_success",
            "type": "reply_only",
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
        ticket_id=ticket_id,
    )

    logger.info(f"[{job_id}] Complaint + reply completed")

    return {
        "job_id": job_id,
        "status": "success",
        "type": "complaint_and_reply",
        "ticket_id": ticket_id,
        "complaint_link": complaint_link,
        "reply": reply,
        "decision": decision,
    }


# =========================
# Reply Only Flow
# =========================
async def _handle_reply(job_id: str, data: dict, decision: dict) -> dict:
    try:
        reply = await reply_agent(
            data["review"],
            data["rating"],
            data["reviewer"],
            data["location_name"],
        )

        logger.info(f"[{job_id}] Reply generated")

        return {
            "job_id": job_id,
            "status": "success",
            "type": "reply",
            "reply": reply,
            "decision": decision,
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Reply generation failed")

        return _error_response(
            job_id=job_id,
            message="Reply agent failed",
            details=str(e),
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