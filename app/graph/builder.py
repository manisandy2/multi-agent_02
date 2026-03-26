from langgraph.graph import StateGraph, END

from app.graph.state import ReviewState
from app.graph.nodes.supervisor import supervisor_node
from app.graph.nodes.complaint import complaint_node
from app.graph.nodes.reply import reply_node
from app.graph.router import route_decision


def build_graph():
    builder = StateGraph(ReviewState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("complaint", complaint_node)
    builder.add_node("reply", reply_node)

    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor",
        route_decision,
        {
            "complaint": "complaint",
            "reply": "reply",
        },
    )

    builder.add_edge("complaint", "reply")
    builder.add_edge("reply", END)

    return builder.compile()