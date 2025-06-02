from aegis.tools.tool_metadata import load_tool_metadata
from aegis.registry import ToolEntry
from pydantic import BaseModel
from typing import Any


class DummyModel(BaseModel):
    value: str


def dummy_tool(input_data: BaseModel) -> Any:
    return f"Result: {input_data.text}"


def test_safe_mode_metadata_check():
    tool = ToolEntry(
        name="secure_dummy",
        run=dummy_tool,
        input_model=DummyModel,
        tags=["safe", "test"],
        description="Secure test tool",
        safe_mode=True,
    )
    metadata = load_tool_metadata(tool)
    assert metadata["safe_mode"] is True
