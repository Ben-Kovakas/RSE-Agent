from langgraph.graph import StateGraph, START, END
from .state import ResearchState
from .nodes import coder_node, tester_node, reviewer_node, executor_node

# 1. Define the Graph
workflow = StateGraph(ResearchState)

# 2. Add Nodes
workflow.add_node("coder", coder_node)
workflow.add_node("tester", tester_node)
workflow.add_node("reviewer", reviewer_node)
workflow.add_node("executor", executor_node)

# 3. Define Edges
workflow.add_edge(START, "coder")
workflow.add_edge("coder", "tester")
workflow.add_edge("tester", "reviewer")
workflow.add_edge("reviewer", "executor")

# 4. Define Logic Loop (The most important part for RSE)
def route_after_execution(state: ResearchState):
    if state["passed"]:
        return END
    if state["iteration"] >= state["max_iterations"]:
        return END
    return "coder"  # Loop back to fix code if it failed

workflow.add_conditional_edges("executor", route_after_execution)

# 5. Compile the executable agent
app = workflow.compile()