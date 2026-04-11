import asyncio
import logging
from typing import Optional
from app.agents.reply_agent import reply_agent
from app.tools.crm_tool import complaint_agent
from app.agents.supervisor_agent import decision_agent,compliance_agent
from app.utility.helper import build_complaint_link
from app.core.state import ReviewState

logger = logging.getLogger(__name__)

# =========================
# Main ORCHESTRATOR
# =========================

async def process_review_task(data:dict) -> dict:
    state = ReviewState(data)

    job_id = state.job_id
    state.log("Processing started")

    print(f"\n🚀 START PROCESSING | Job ID: {job_id}")
    print("=" * 80)


    try:
        # =========================
        # 🔍 STEP 0: SENSITIVE CHECK
        # =========================
        print("🔍 Checking for sensitive content...")
        if _is_sensitive(state.review):
            print("⛔ Sensitive content detected. Blocking response.")
            return _blocked_response(job_id, {})
        
        # =========================
        # 🧠 STEP 1: DECISION (LLM)
        # =========================
        print("🧠 Generating decision...")

        decision = await decision_agent(
            review=state.review,
            rating=state.rating,
            reviewer=state.reviewer,
            store=state.location_name
        )


        print("✅ Decision Output:", decision)

        state.add_history("decision", "completed", decision)
        state.set_metric("decision", "success", True)

        state.issue_type = decision.get("classification", {}).get("issue_type", "other")

        # =========================
        # 📌 STEP 2: COMPLAINT (OPTIONAL)
        # =========================
        print("\n📌 STEP 2: Complaint Check")
        

        complaint_task = (
            _safe_create_complaint(state)
            if decision.get("create_ticket")
            else asyncio.sleep(0, result=None)
        )
        print("\n✍️ STEP 3: Generating Reply")

        # -------------------------
        # ✍️ STEP 3: REPLY GENERATION
        # -------------------------

        complaint_link, reply = await asyncio.gather(
            complaint_task,
            _generate_reply(state))

        if not reply:
            print("⚠️ Reply generation failed, using fallback")
            reply = "Thank you for your feedback. We will look into this."

        print("📝 Draft Reply:",reply)
        
        print("🔗 Complaint Link:",complaint_link)
        
        # =========================
        # 🔗 STEP 4: ADD LINK (FIXED)
        # =========================
        print("\n🔗 STEP 4: Attach Complaint Link")
        
        if complaint_link:
            state.draft_response = f"{reply} Kindly share more details here: {complaint_link}"
        else:
            state.draft_response = reply

        print("📄 Draft with Link:",state.draft_response)

        # =========================
        # 🧹 STEP 5: CLEAN REPLY
        # =========================
        print("\n🧹 STEP 5: Cleaning Reply")

        state.draft_response = clean_reply(state.draft_response)

        print("✨ Cleaned Reply:",state.draft_response)

        # =========================
        # 👮 STEP 6:  VALIDATION
        # =========================
        print("👮 Validating reply...")

        final_reply = await _validate_reply(state)

        state.final_response = final_reply

        print("🎯 FINAL RESPONSE:", state.final_response)

        state.set_metric("validation", "completed", True)

        print("=" * 80)
        print(f"✅ DONE | Job ID: {job_id}\n")

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
# REPLY CLEANING
# =========================
def clean_reply(text: str) -> str:
    sentences = text.split(". ")
    seen = set()
    result = []

    for s in sentences:
        s = s.strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)

    return ". ".join(result)


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


async def _generate_reply(state: ReviewState) -> str:
    print("✍️ Generating reply...")
    state.log("Reply generation started")

    max_retries = 2

    for attempt in range(max_retries):
        try:
            state.increment_retry("reply")
            state.log(f"Reply attempt {attempt+1}")
            issue_type = getattr(state, "issue_type", "other")

            reply = await reply_agent(
                review=state.review,
                rating=state.rating,
                reviewer=state.reviewer,
                store=state.location_name,
                issue_type=issue_type

            )

            if reply and isinstance(reply, str):
                reply = reply.strip()

                if not _is_bad_reply(reply, state.rating):
                    state.log("Reply generated successfully")
                    state.set_metric("reply", "success", True)
                    #state.add_history("reply", "generated", reply)

                    return reply

                state.log("Bad reply detected, retrying...")

        except Exception as e:
            state.log(f"Reply attempt {attempt+1} failed: {str(e)}")

            if attempt == max_retries - 1:
                state.set_metric("reply", "error", str(e))

    # -------- FALLBACK --------
    state.log("Using fallback reply")

    fallback_reply = (
        "We're sorry for your experience. Please share more details so we can assist you."
        if state.rating and state.rating <= 2
        else "Thank you for your feedback. We will look into this."
    )

    state.add_history("reply", "fallback", fallback_reply)
    state.set_metric("reply", "fallback_used", True)

    return fallback_reply


async def _validate_reply(state: ReviewState) -> str:
    print("👮 Validating reply...")
    state.log("Validation started")

    try:
        issue_type = getattr(state, "issue_type", "other")

        final = await compliance_agent(
            # review=state.review,
            # rating=state.rating,
            draft_reply=state.draft_response,   # or reply=... based on your function
            # issue_type=issue_type,
            # reviewer=state.reviewer,
            # store=state.location_name
        )

        print("🔍 RAW COMPLIANCE OUTPUT:", final)

        # 🚨 HARD CHECK
        if not final or not isinstance(final, dict):
            raise ValueError("Invalid compliance response format")

        status = final.get("status")
        final_reply = final.get("final_reply")
        reason = final.get("reason", "No reason provided")
        
        # ✅ STRICT STATUS CHECK
        valid_status = {"approved", "modified", "blocked"}
        if status not in valid_status:
            raise ValueError(f"Invalid status from compliance_agent: {status}")
        
        # ✅ APPROVED
        if status == "approved":
            state.log("Reply approved")
            state.add_history("validation", "approved", {
                "reply": state.draft_response,
                "reason": reason
            })
            return state.draft_response

        # ✅ MODIFIED
        if status == "modified" and final_reply:
            # 🔒 Guardrail: prevent regeneration
            if not _is_safe_modification(state.draft_response, final_reply):
                state.log("Regeneration detected → forcing approved")
                state.add_history("validation", "forced_approved", {
                    "reason": "agent2_regeneration_detected"
                })
                return state.draft_response

            state.log("Reply modified")
            state.add_history("validation", "modified", {
                "original": state.draft_response,
                "modified": final_reply,
                "reason": reason
            })
            return final_reply
        
         # ❌ BLOCKED
        if status == "blocked":
            state.log("Reply blocked")
            state.add_history("validation", "blocked", {
                "reason": reason
            })
            return "We request you to raise a ticket so our team can assist you further."

        # ⚠️ Fallback
        state.log("Unknown status → using draft")
        return state.draft_response

    except Exception as e:
        # 🚨 CLEAR ERROR LOGGING
        print("❌ VALIDATION ERROR:", str(e))
        state.log(f"Validation failed: {str(e)}")

        state.add_history("validation", "error", {
            "error": str(e),
            "raw_response": str(final) if 'final' in locals() else "No response"
        })

        # ✅ SAFE FALLBACK (keep original reply)
        return state.draft_response

def _is_safe_modification(original: str, modified: str) -> bool:
    if not original or not modified:
        return False

    # Length control (max 30% change)
    if len(modified) > len(original) * 1.3:
        return False

    # Word overlap check
    orig_words = set(original.lower().split())
    mod_words = set(modified.lower().split())

    common = orig_words & mod_words

    if len(common) < len(orig_words) * 0.5:
        return False

    return True
    
# =========================
# REPLY QUALITY CHECK
# =========================
def _is_bad_reply(reply: str, rating: int) -> bool:
    if not reply:
        return True

    reply = reply.strip()
    words = reply.split()

    # Too short
    if len(words) < 10:
        return True

    # Must have at least one sentence
    if "." not in reply:
        return True

    # Negative reviews must have empathy
    if rating <= 2:
        if not any(word in reply.lower() for word in ["sorry", "apolog", "regret"]):
            return True

    # Duplicate sentence check
    sentences = [s.strip() for s in reply.split(".") if s.strip()]
    if len(sentences) != len(set(sentences)):
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