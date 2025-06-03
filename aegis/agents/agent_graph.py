from langgraph.graph import StateGraph

from aegis.agents.node_registry import AGENT_NODE_REGISTRY
from aegis.utils.logger import setup_logger
from aegis.agents.task_state import TaskState

logger = setup_logger(__name__)


class AgentGraph:
    """
    Represents the AgentGraph class.

    Use this class to define and manage the execution graph for agent workflows.
    """

    def __init__(self, config):
        """
        Initializes the AgentGraph with a given configuration.

        :param config: Configuration object containing entrypoint, nodes, edges, and routing logic.
        :type config: Any
        """
        self.config = config

    def build_graph(self):
        """
        Builds and compiles the StateGraph based on the provided configuration.

        :return: Compiled StateGraph
        :rtype: Any
        """
        logger.debug(
            f"Initializing StateGraph with state_type: {self.config.state_type}"
        )
        builder = StateGraph(self.config.state_type)

        all_nodes = (
            {self.config.entrypoint}
            | {src for src, _ in self.config.edges}
            | {dst for _, dst in self.config.edges}
            | set(self.config.condition_map.values())
        )
        for name in all_nodes:
            builder.add_node(name, AGENT_NODE_REGISTRY[name])

        logger.debug(f"Setting entry point to: {self.config.entrypoint}")
        builder.set_entry_point(self.config.entrypoint)

        for edge in self.config.edges:
            logger.debug(f"Adding edge: {edge[0]} -> {edge[1]}")
            builder.add_edge(edge[0], edge[1])

        if self.config.condition_node and self.config.condition_map:
            logger.debug(f"Resolving condition_map: {self.config.condition_map}")

            def resolved_map(state: TaskState) -> str:
                logger.debug(f"Resolving next step from state: {state}")
                key = getattr(state, "next_step", None)
                if not key:
                    raise ValueError(
                        "Missing 'next_step' in TaskState for conditional routing."
                    )
                if key not in self.config.condition_map:
                    raise ValueError(f"Unknown routing key: {key}")
                resolved = self.config.condition_map[key]
                logger.debug(f"Resolved conditional step '{key}' → '{resolved}'")
                return resolved

            builder.add_conditional_edges(self.config.condition_node, resolved_map)

        logger.debug("Setting finish point to summarize")
        builder.set_finish_point("summarize")
        compiled = builder.compile()
        logger.debug("Graph compilation complete")
        return compiled

    async def run(self, input_data):
        """
        Executes the graph using the provided input data.

        :param input_data: Dictionary or TaskState instance
        :type input_data: Any
        :return: Final TaskState after graph execution
        :rtype: TaskState
        """
        logger.debug(f"Running graph with input data: {input_data}")
        graph = self.build_graph()

        if not isinstance(input_data, TaskState):
            state = TaskState(**input_data)
        else:
            state = input_data

        result = await graph.ainvoke(state)
        logger.debug(f"Graph execution complete, result: {result}")
        return result
