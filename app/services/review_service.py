from app.graph.builder import build_graph

graph = build_graph()


async def process_review(data):
    result = await graph.ainvoke(data)
    return result