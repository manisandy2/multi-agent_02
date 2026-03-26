from agents.supervisor import supervisor_ai
from graph.state import ReviewState


async def supervisor_node(state: ReviewState):
    decision = await supervisor_ai(
        state["review"], state["rating"]
    )
    return {"decision": decision}