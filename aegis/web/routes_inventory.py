# aegis/web/routes_inventory.py
"""
API route to expose the inventory of currently registered tools.
"""

from fastapi import APIRouter

from aegis.registry import TOOL_REGISTRY
from aegis.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)


@router.get("/inventory", tags=["Inventory"])
async def get_inventory() -> list[dict]:
    """Retrieves and returns the metadata for all registered tools.

    This endpoint powers the 'Tools' tab in the web UI, allowing users
    to see the capabilities of the agent at a glance. It iterates through the
    `TOOL_REGISTRY`, formats the metadata for each tool, and generates the
    JSON schema for its Pydantic input model. It gracefully handles
    errors in individual tool schema generation to prevent the entire
    endpoint from failing.

    :return: A list of dictionaries, where each dictionary represents a tool.
    :rtype: list[dict]
    """
    logger.info("Inventory requested. Returning list of all registered tools.")

    if not TOOL_REGISTRY:
        logger.warning("Tool inventory requested, but registry is empty.")
        return []

    inventory_list = []
    for tool in sorted(TOOL_REGISTRY.values(), key=lambda t: t.name):
        try:
            input_schema = tool.input_model.model_json_schema()
        except Exception as e:
            logger.error(f"Could not generate JSON schema for tool '{tool.name}': {e}")
            input_schema = {"error": f"Could not generate schema: {e}"}

        inventory_list.append({
            "name": tool.name,
            "description": tool.description,
            "category": tool.category or "uncategorized",
            "tags": tool.tags,
            "safe_mode": tool.safe_mode,
            "input_schema": input_schema,
        })

    logger.info(f"Successfully built inventory with {len(inventory_list)} tools.")
    return inventory_list
