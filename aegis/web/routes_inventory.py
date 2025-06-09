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
    to see the capabilities of the agent at a glance.

    :return: A list of dictionaries, where each dictionary represents a tool.
    :rtype: list[dict]
    """
    logger.info("Inventory requested. Returning list of all registered tools.")

    if not TOOL_REGISTRY:
        return []

    inventory_list = []
    for tool in sorted(TOOL_REGISTRY.values(), key=lambda t: t.name):
        inventory_list.append(
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.category or "uncategorized",
                "tags": tool.tags,
                "safe_mode": tool.safe_mode,
                "input_schema": tool.input_model.model_json_schema(),
            }
        )

    return inventory_list
