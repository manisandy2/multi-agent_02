


from app.tools.crm_tool import complaint_agent

async def complaint_node(state):
    ticket = await complaint_agent(state)
    return {"ticket": ticket}