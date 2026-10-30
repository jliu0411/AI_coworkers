"""Use real LangGraph when installed; tiny sequential runner only for dependency-free smoke tests.

The offline runner is NOT a reimplementation of LangGraph features like checkpointing or branching.
SQLite in this project is the durable long-term store in either mode.
"""
try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    START, END = '__start__', '__end__'

    class StateGraph:
        def __init__(self, state_schema):
            self.nodes, self.edges = {}, {}
        def add_node(self, name, fn):
            self.nodes[name] = fn
        def add_edge(self, a, b):
            self.edges[a] = b
        def compile(self):
            nodes, edges = self.nodes, self.edges
            class Runner:
                def invoke(self, state):
                    state = dict(state)
                    node = edges[START]
                    while node != END:
                        state.update(nodes[node](state))
                        node = edges[node]
                    return state
            return Runner()
