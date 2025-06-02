"""
Compare tool for web snapshots — diffs two HTML files.
"""

from difflib import unified_diff
from pathlib import Path

from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class WebSnapshotCompareInput(BaseModel):
    """Schema for diffing two HTML snapshot files.

:ivar file1: Path to the first HTML snapshot.
:ivar file2: Path to the second HTML snapshot."""
    file1: str = Field(..., description="Path to the first HTML snapshot")
    file2: str = Field(..., description="Path to the second HTML snapshot")


@register_tool(
    name="web_snapshot_compare",
    input_model=WebSnapshotCompareInput,
    description="Compares two HTML snapshots and returns a unified diff.",
    tags=["browser", "diff", "snapshot"],
    category="wrapper",
    safe_mode=True,
)
def web_snapshot_compare(input_data: WebSnapshotCompareInput) -> str:
    """
    Loads two HTML files and performs a unified diff.
    """
    logger.info(
        f"[web_snapshot_compare] Comparing {input_data.file1} vs {input_data.file2}"
    )

    path1 = Path(input_data.file1)
    path2 = Path(input_data.file2)

    if not path1.exists() or not path2.exists():
        return "One or both snapshot files not found."

    html1 = path1.read_text().splitlines()
    html2 = path2.read_text().splitlines()

    diff = unified_diff(
        html1, html2, fromfile=path1.name, tofile=path2.name, lineterm=""
    )
    diff_output = "".join(diff)

    logger.debug(f"[web_snapshot_compare] Diff length: {len(diff_output)} characters")
    return diff_output if diff_output else "No differences detected."
