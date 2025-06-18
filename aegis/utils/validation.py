# aegis/utils/validation.py
"""
Utility functions for validating agent graph configurations.
"""
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


def validate_node_names(config: dict):
    """Validates that all referenced node names in a graph config exist in the node list.

        This function checks the entrypoint, all edges, and the condition map to
        ensure they only refer to nodes that are explicitly defined. This prevents
    is a core safety check to prevent the graph from being built with invalid
        transitions or references to non-existent nodes.

        :param config: The agent graph configuration dictionary loaded from a preset.
        :type config: dict
        :raises ValueError: If a referenced node is not defined in the `nodes` list.
    """
    logger.debug("Validating node names in graph configuration.")

    nodes = config.get("nodes", [])
    edges = config.get("edges", [])
    condition_map = config.get("condition_map", {})
    entrypoint = config.get("entrypoint", "")

    # Set of all node IDs that are defined in the 'nodes' list
    defined_nodes = {node["id"] for node in nodes}
    logger.debug(f"Defined nodes: {defined_nodes}")

    # Set of all node IDs that are referenced in the graph structure
    referenced_nodes = {entrypoint}
    for src, dst in edges:
        referenced_nodes.add(src)
        referenced_nodes.add(dst)
    for dst in condition_map.values():
        referenced_nodes.add(dst)
    # The condition_node itself must also be a defined node
    if config.get("condition_node"):
        referenced_nodes.add(config["condition_node"])

    logger.debug(f"Referenced nodes: {referenced_nodes}")

    # Check for any referenced node that is not defined
    for node_name in referenced_nodes:
        if node_name == "__end__":
            continue
        if node_name not in defined_nodes:
            logger.error(
                f"Graph validation failed: Node '{node_name}' is referenced but not defined."
            )
            raise ValueError(f"Unknown node name in config: '{node_name}'")

    logger.info("Graph node name validation successful.")
