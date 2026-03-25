import asyncio
from app.agents.reply_agent import reply_agent
from app.agents.complaint_agent import complaint_agent
from app.agents.supervisor import supervisor_ai
import logging
from app.utility.helper import build_complaint_link


logger = logging.getLogger(__name__)

async def process_review_task(data):
    job_id = data.get("job_id")
    try:
        decision = await supervisor_ai(
            data["review"], data["rating"]
            )
        
        # reply = await reply_agent(
        #     data["review"],
        #     data["rating"],
        #     data["reviewer"],
        #     data["location_name"]
            
        # )

        # 🚨 Complaint path
        if decision.get("create_ticket"):
            ticket = await complaint_agent(data)
            
            ticket_id = ticket.get("ticket_id")
            link = build_complaint_link(ticket_id)
            
            reply = await reply_agent(
            data["review"],
            data["rating"],
            data["reviewer"],
            data["location_name"],
            complaint_link=link,
            ticket_id=ticket_id
        )
            result =  {
                "job_id": job_id,
                "status": "complaint",
                "type": "complaint_and_reply",
                "ticket_id": ticket.get("ticket_id"),
                "reply": reply,
                "decision": decision
                
            }
            logger.info(f"[{job_id}] Complaint + Reply done")
            return result
        
        reply = await reply_agent(
        data["review"],
        data["rating"],
        data["reviewer"],
        data["location_name"]
    )
        # ✍️ Reply only
        result = {
            "job_id": job_id,
            "status": "completed",
            "type": "reply",
            "reply": reply,
            "decision": decision
        }

        logger.info(f"[{job_id}] Reply generated")
        return result
    
    except Exception as e:
        logger.error(f"[{job_id}] Failed: {str(e)}")
        
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e)
        }

    