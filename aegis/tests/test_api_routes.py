# aegis/tests/test_api_routes.py
"""
Tests for the FastAPI web application and its routes.
"""
from fastapi.testclient import TestClient

# The 'app' object is the main FastAPI instance from your serve_dashboard script.
# We import it to allow the TestClient to interact with it directly.
from aegis.serve_dashboard import app

# The TestClient gives us a way to make HTTP requests to our app in tests.
client = TestClient(app)


def test_get_inventory_api():
    """
    Tests the /api/inventory endpoint to ensure it returns a valid list of tools.
    """
    response = client.get("/api/inventory")

    # 1. Assert that the request was successful
    assert response.status_code == 200

    # 2. Assert that the response is a JSON list
    data = response.json()
    assert isinstance(data, list)

    # 3. Assert that the list is not empty (assuming tools are registered)
    assert len(data) > 0

    # 4. Assert that a known, critical tool is present in the inventory
    tool_names = [tool["name"] for tool in data]
    assert "run_local_command" in tool_names

    # 5. Assert that the structure of a tool entry is correct
    first_tool = data[0]
    assert "name" in first_tool
    assert "description" in first_tool
    assert "category" in first_tool
    assert "tags" in first_tool
    assert "input_schema" in first_tool
