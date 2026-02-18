"""
WebSocket Event Handlers

Handles incoming WebSocket messages for the global connection.
"""

import json

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class WebSocketHandler:
    """Handles WebSocket message processing for the global connection."""

    def __init__(self, websocket: WebSocket, user: User, db: AsyncSession):
        self.websocket = websocket
        self.user = user
        self.db = db
        self.user_id = str(user.id)

    async def handle_message(self, message: str) -> None:
        """Process an incoming WebSocket message."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "ping":
                await self._send_message({"type": "pong", "payload": {}})
            else:
                await self._send_error(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            await self._send_error("Invalid JSON message")
        except Exception as e:
            await self._send_error(str(e))

    async def _send_message(self, message: dict) -> None:
        """Send a message to the client."""
        try:
            await self.websocket.send_text(json.dumps(message))
        except Exception:
            pass

    async def _send_error(self, error: str) -> None:
        """Send an error message to the client."""
        await self._send_message({
            "type": "error",
            "payload": {"message": error},
        })
