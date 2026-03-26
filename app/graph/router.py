

def route_decision(state):
    decision = state.get("decision", {})

    if decision.get("create_ticket"):
        return "complaint"

    return "reply"