# aegis/tools/wrappers/browser/web_snapshot_compare.py
"""
A tool for comparing two previously captured HTML snapshots.

This module provides a tool that performs a unified diff on two HTML files
to identify changes between them.
"""

from difflib import unified_diff
from pathlib import Path

from pydantic import BaseModel, Field

# Import ToolExecutionError
from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class WebSnapshotCompareInput(BaseModel):
    """Input model for comparing two HTML files.

    :ivar file1: The file path to the first HTML snapshot.
    :vartype file1: str
    :ivar file2: The file path to the second HTML snapshot.
    :vartype file2: str
    """

    file1: str = Field(..., description="The file path to the first HTML snapshot.")
    file2: str = Field(..., description="The file path to the second HTML snapshot.")


@register_tool(
    name="web_snapshot_compare",
    input_model=WebSnapshotCompareInput,
    description="Compares two HTML snapshots and returns a unified diff of their contents.",
    tags=["browser", "diff", "snapshot", "web", "wrapper"],
    category="wrapper",
    safe_mode=True,
    purpose="Identify differences between two captured web page states.",
)
def web_snapshot_compare(input_data: WebSnapshotCompareInput) -> str:
    """Loads two HTML files from disk and returns a unified diff string.

    This tool is useful for regression testing of web UIs, where the agent can
    capture the state of a page before and after an action and then use this
    tool to see exactly what changed in the DOM.

    :param input_data: An object containing the paths to the two files to compare.
    :type input_data: WebSnapshotCompareInput
    :return: A string containing the diff, or a message if no differences are found.
    :rtype: str
    :raises ToolExecutionError: If files are not found or cannot be read.
    """
    logger.info(f"Comparing web snapshots: {input_data.file1} vs {input_data.file2}")

    path1 = Path(input_data.file1)
    path2 = Path(input_data.file2)

    if not path1.is_file():
        raise ToolExecutionError(f"File not found: {path1}")
    if not path2.is_file():
        raise ToolExecutionError(f"File not found: {path2}")

    try:
        html1_lines = path1.read_text(encoding="utf-8").splitlines()
        html2_lines = path2.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        logger.exception("Failed to read one of the snapshot files.")
        raise ToolExecutionError(f"Could not read snapshot files: {e}")

    diff = unified_diff(
        html1_lines, html2_lines, fromfile=path1.name, tofile=path2.name, lineterm=""
    )
    diff_output = "\n".join(diff)

    if not diff_output:
        return "No differences were detected between the two files."

    logger.debug(f"Diff generated with length: {len(diff_output)} characters")
    return diff_output
