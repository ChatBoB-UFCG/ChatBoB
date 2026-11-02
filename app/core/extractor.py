from app.graph.builder import build_graph
from app.core.schema import Schema

class ExtractorAgent:
    def __init__(self):
        self.graph = build_graph()

    def feed_message(self, message: str, state: dict):
        state["last_user_message"] = message

        state["context_messages"].append({
            "role": "user",
            "content": state["last_user_message"]
        })
        return self.graph.invoke(state)
