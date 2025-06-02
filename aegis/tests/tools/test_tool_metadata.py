from aegis.tools.tool_metadata import load_tool_metadata
from aegis.registry import ToolEntry
from pydantic import BaseModel
from typing import Any


class DummyModel(BaseModel):
    value: str


def dummy_run(input_data: BaseModel) -> Any:
    return f"Echo: {input_data.value}"


def test_tool_metadata_loads():
    tool = ToolEntry(
        name="dummy_tool",
        run=dummy_run,
        input_model=DummyModel,
        tags=["example"],
        description="Test tool",
    )
    metadata = load_tool_metadata(tool)
    assert "description" in metadata
    assert metadata["description"] == "Test tool"
