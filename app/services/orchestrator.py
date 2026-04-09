import asyncio
import logging
from typing import Optional
from app.agents.reply_agent import reply_agent
from app.tools.crm_tool import complaint_agent
from app.agents.supervisor_agent import supervisor_agent
from app.utility.helper import build_complaint_link
from app.core.state import ReviewState

logger = logging.getLogger(__name__)

# =========================
# Main ORCHESTRATOR
# =========================

async def process_review_task(data:dict) -> dict:
    state = ReviewState(data)

    print("Initial State:###############################################")

    job_id = state.job_id
    state.log("Processing started")

    try:
        
        # -------------------------
        # SUPERVISOR (DECISION)
        # -------------------------
        decision = await _get_decision(state)

        state.add_history("decision", "done", decision)
        print("After Decision: ##############################################")
        print(state.data)
        print(state.review)
        print(state.rating)

        print("#"*100)
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

        if _is_sensitive(state.review):
            state.set_error("Sensitive content")
            return _blocked_response(job_id, decision)
        
        # -------------------------
        # PARALLEL TASKS
        # -------------------------

        complaint_task = (
            _safe_create_complaint(state)
            if decision.get("create_ticket")
            else asyncio.sleep(0, result=None)
        )

        # -------------------------
        # REPLY (ALWAYS)
        # -------------------------
        print("Generating reply 01 ##############################################")
        reply_task =  _generate_reply(state)

        complaint_link, reply = await asyncio.gather(
            complaint_task,
            reply_task)

        # -------------------------
        # ADD LINK (NO RE-GENERATION)
        # -------------------------
        state.draft_response = reply
        print("Generating reply 02 ##############################################")
        if complaint_link and reply:
            state.draft_response += f"{reply} Kindly share more details here: {complaint_link}"



        # -------------------------
        # SUPERVISOR (VALIDATE + FIX)
        # -------------------------
        state.final_response = await _validate_reply(
            state
        )
        state.complete()
        
        return {
            "job_id": job_id,
            "status": "success",
            "type": "complaint_and_reply" if complaint_link else "reply",
            "complaint_link": complaint_link,
            "reply": state.final_response,
            "decision": decision,
            "logs": state.logs,
            "history": state.history,
        }

    except Exception as e:
        logger.exception(f"[{job_id}] Processing failed")
        state.set_error(str(e))
        
        return _error_response(
            job_id=job_id,
            message="Processing failed",
            details=str(e),
        )
    
# =========================
# SUPERVISOR DECISION
# =========================
async def _get_decision(state: ReviewState) -> dict:

    decision = await supervisor_agent(
        review=state.review,
        rating=state.rating,
        reviewer=state.reviewer,
        store=state.location_name,
        mode="analyze"
    ) or {}

    decision = _enforce_rules(decision, state.rating)

    state.add_history("decision", "On process", decision)
    state.add_history("review", "start", state.review)
    state.add_history("decision", "completed", decision)
    state.log("Decision generated")

    return decision


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

def _blocked_response(job_id, decision):
    return {
        "job_id": job_id,
        "status": "success",
        "type": "blocked",
        "reply": "We request you to raise a ticket so our team can assist you further.",
        "decision": decision,
    }

# =========================
# SAFE COMPLAINT
# =========================
# async def _safe_create_complaint(data: dict, job_id: str) -> str | None:
#     try:
#         ticket = await complaint_agent(data)

#         if ticket.get("status") == "created":
#             ticket_id = ticket.get("ticket_id")
#             if ticket_id:
#                 return build_complaint_link(ticket_id)

#         logger.warning(f"[{job_id}] Complaint not created")
#         return None

#     except Exception as e:
#         logger.error(f"[{job_id}] Complaint failed: {e}")
#         return None
async def _safe_create_complaint(state: ReviewState) -> Optional[str]:
    print("Creating complaint ##############################################")
    state.log("Complaint creation started")

    max_retries = 2

    for attempt in range(max_retries):

        try:
            state.increment_retry("complaint")

            ticket = await complaint_agent(state.data)
            print(f"Complaint API response: {ticket} ##############################################")
            if ticket.get("status") == "created":
                ticket_id = ticket.get("ticket_id")

                if ticket_id:
                    link = build_complaint_link(ticket_id)
                    print("#"*100)
                    print("Link: ", link)
                    state.log(f"Complaint created: {ticket_id}")
                    state.add_history("complaint", "created", {
                        "ticket_id": ticket_id,
                        "link": link
                    })

                    state.set_metric("complaint", "success", True)

                    return link

            # If API responded but not successful
            state.log("Complaint API responded but not created")

        except Exception as e:
            state.log(f"Complaint attempt {attempt+1} failed: {str(e)}")

            if attempt == max_retries - 1:
                state.set_metric("complaint", "error", str(e))

    # Final fallback
    state.log("Complaint creation failed after retries")
    state.add_history("complaint", "failed")

    return None

# =========================
# REPLY GENERATION
# =========================
# async def _generate_reply(
#     # review: str,
#     # rating: int,
#     # reviewer: str,
#     # store: str,
#     # complaint_link: str = None,
#     state: ReviewState
# ) -> str:
#     print("start Generating reply ##############################################")
#     state.log("Reply generation started")
#     for _ in range(2):  # retry max 2 times
#         try:
#             reply = await reply_agent(
#                 state.review,
#                 state.rating,
#                 state.reviewer,
#                 state.store,
                
#             )

#             if reply and isinstance(reply, str):
#                 reply = reply.strip()

#                 if not _is_bad_reply(reply, state.rating):
#                     state.log("Reply generated successfully")
#                     state.set_metric("reply", "success", True)
#                     state.add_history("reply", "generated")
#                     return reply
#                 state.log("Bad reply detected, retrying...")

#         except Exception as e:
#             logger.warning(f"Reply generation failed: {e}")

#     # fallback
#     if complaint_link:
#         return f"Thank you for your feedback. Please contact us here: {complaint_link}"

#     return "Thank you for your feedback. We will look into this."

async def _generate_reply(state: ReviewState) -> str:
    print("start Generating reply ##############################################")
    state.log("Reply generation started")

    max_retries = 2

    for attempt in range(max_retries):
        try:
            state.increment_retry("reply")

            reply = await reply_agent(
                state
            )

            if reply and isinstance(reply, str):
                reply = reply.strip()

                if not _is_bad_reply(reply, state.rating):
                    state.log("Reply generated successfully")
                    state.set_metric("reply", "success", True)
                    state.add_history("reply", "generated")

                    return reply

                state.log("Bad reply detected, retrying...")

        except Exception as e:
            state.log(f"Reply attempt {attempt+1} failed: {str(e)}")

            if attempt == max_retries - 1:
                state.set_metric("reply", "error", str(e))

    # -------- FALLBACK --------
    state.log("Using fallback reply")
    state.add_history("reply", "fallback")

    if state.rating and state.rating <= 2:
        return "We're sorry for your experience. Please share more details so we can assist you."

    return "Thank you for your feedback. We will look into this."

# =========================
# VALIDATION + CORRECTION
# =========================
# async def _validate_reply(review, rating, reviewer, store, reply):

#     try:
#         final = await supervisor_agent(
#             review=review,
#             rating=rating,
#             reviewer=reviewer,
#             store=store,
#             reply=reply,
#             mode="validate",
#         ) or {}

#         if final.get("approved", True):
#             return reply

#         return final.get(
#             "corrected_reply",
#             "Thank you for your feedback. We will look into this."
#         )

#     except Exception as e:
#         logger.warning(f"Validation failed: {e}")
#         return reply  # fail-safe

async def _validate_reply(state: ReviewState) -> str:
    print("Validating reply ##############################################")
    state.log("Validation started")

    try:
        final = await supervisor_agent(
            review=state.review,
            rating=state.rating,
            reviewer=state.reviewer,
            store=state.location_name,
            reply=state.draft_response,
            mode="validate",
        ) or {}
        print(f"Validation result: {final} ##############################################")
        # -------- APPROVED --------
        if final.get("approved", True):
            state.log("Reply approved")
            state.set_metric("validation", "approved", True)
            state.add_history("validation", "approved")

            return state.draft_response

        # -------- CORRECTED --------
        corrected = final.get("corrected_reply")

        if corrected:
            state.log("Reply corrected by supervisor")
            state.set_metric("validation", "corrected", True)
            state.add_history("validation", "corrected")

            return corrected

        # -------- FALLBACK --------
        state.log("Validation fallback used")
        state.add_history("validation", "fallback")

        return "Thank you for your feedback. We will look into this."

    except Exception as e:
        state.log(f"Validation failed: {str(e)}")
        state.set_metric("validation", "error", str(e))

        return state.draft_response  # fail-safe
    
# =========================
# REPLY QUALITY CHECK
# =========================
def _is_bad_reply(reply: str, rating: int) -> bool:
    if not reply:
        return True

    words = reply.split()

    if len(words) < 15:
        return True

    if rating <= 2 and "sorry" not in reply.lower():
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