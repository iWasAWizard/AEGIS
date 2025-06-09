# aegis/tests/web/test_routes_stream.py
"""
Unit tests for the WebSocket log streaming API route.
"""
import pytest
from fastapi.testclient import TestClient

from aegis.serve_dashboard import app
from aegis.web.routes_stream import connected_clients, broadcast_log

client = TestClient(app)


def test_websocket_connection():
    """Verify that a client can connect and disconnect successfully."""
    # Ensure the list is empty before the test
    connected_clients.clear()
    assert len(connected_clients) == 0

    with client.websocket_connect("/api/ws/logs") as websocket:
        # After connecting, the client should be in the list
        assert len(connected_clients) == 1

    # After the 'with' block exits, the client should be disconnected and removed
    assert len(connected_clients) == 0


@pytest.mark.asyncio
async def test_websocket_broadcast():
    """Verify that a connected client receives broadcasted messages."""
    connected_clients.clear()

    with client.websocket_connect("/api/ws/logs") as websocket:
        # Broadcast a test message
        test_message = "Hello, WebSocket!"
        await broadcast_log(test_message)

        # Check if the client received the message
        received_data = websocket.receive_text()
        assert received_data == test_message


@pytest.mark.asyncio
async def test_multiple_clients_receive_broadcast():
    """Verify that all connected clients receive the same broadcast message."""
    connected_clients.clear()

    with client.websocket_connect("/api/ws/logs") as websocket1:
        with client.websocket_connect("/api/ws/logs") as websocket2:
            assert len(connected_clients) == 2

            test_message = "Broadcast to all!"
            await broadcast_log(test_message)

            # Check both clients
            received1 = websocket1.receive_text()
            received2 = websocket2.receive_text()

            assert received1 == test_message
            assert received2 == test_message
