from app.agents.reply_agent import reply_agent
from app.utility.helper import build_complaint_link

async def reply_node(state):
    ticket = state.get("ticket") or {}
    ticket_id = ticket.get("ticket_id")

    complaint_link = build_complaint_link(ticket_id) if ticket_id else None

    reply = await reply_agent(
        state["review"],
        state["rating"],
        state["reviewer"],
        state["location_name"],
        complaint_link=complaint_link,
        ticket_id=ticket_id,
    )

    return {"reply": reply}