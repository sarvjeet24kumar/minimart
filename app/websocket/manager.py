"""
WebSocket Connection Manager

Manages WebSocket connections for notifications and chat.
Simplified for single-server deployment.
"""

import json
from uuid import UUID

from app.common.constants import WS_CLOSE_AUTH_FAILED, WS_CLOSE_FORBIDDEN
from fastapi import WebSocket
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserRole
from app.models.shopping_list import ShoppingList
from app.models.shopping_list_member import ShoppingListMember
from app.models.user import User


class ConnectionManager:
    """
    Manages WebSocket connections for:
    1. Notifications — sent to global-scoped connections (list members only)
    2. Chat — sent to chat-scoped connections (list members + tenant admins)
    """

    def __init__(self):
        # user_id → {websocket: scope}
        self.active_connections: dict[str, dict[WebSocket, str]] = {}
        # list_id → set of (user_id, websocket)
        self.list_subscribers: dict[str, set[tuple[str, WebSocket]]] = {}
        # (user_id, websocket) → set of list_ids
        self.connection_subscriptions: dict[tuple[str, WebSocket], set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, scope: str = "global") -> None:
        """Accept a new WebSocket connection with a specific scope."""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}

        self.active_connections[user_id][websocket] = scope
        self.connection_subscriptions[(user_id, websocket)] = set()

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection and clean up all references."""
        conn_key = (user_id, websocket)
        if conn_key in self.connection_subscriptions:
            for list_id in list(self.connection_subscriptions[conn_key]):
                if list_id in self.list_subscribers:
                    self.list_subscribers[list_id].discard(conn_key)
                    if not self.list_subscribers[list_id]:
                        del self.list_subscribers[list_id]
            del self.connection_subscriptions[conn_key]

        if user_id in self.active_connections:
            self.active_connections[user_id].pop(websocket, None)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def subscribe_to_list(
        self, user_id: str, list_id: str, db: AsyncSession, websocket: WebSocket | None = None
    ) -> bool:
        """
        Subscribe a connection to a list for chat.
        Tenant Admins can subscribe to any list within their tenant without membership.
        """
        user_result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = user_result.scalar_one_or_none()

        if user and user.role == UserRole.TENANT_ADMIN:
            list_result = await db.execute(select(ShoppingList).where(ShoppingList.id == UUID(list_id)))
            shopping_list = list_result.scalar_one_or_none()
            if not shopping_list or shopping_list.tenant_id != user.tenant_id:
                return False
        else:
            result = await db.execute(
                select(ShoppingListMember).where(
                    and_(
                        ShoppingListMember.shopping_list_id == UUID(list_id),
                        ShoppingListMember.user_id == UUID(user_id),
                        ShoppingListMember.deleted_at.is_(None),
                    )
                )
            )
            if not result.scalar_one_or_none():
                return False

        target_sockets = [websocket] if websocket else list(self.active_connections.get(user_id, {}).keys())

        for ws in target_sockets:
            conn_key = (user_id, ws)
            if list_id not in self.list_subscribers:
                self.list_subscribers[list_id] = set()
            self.list_subscribers[list_id].add(conn_key)

            if conn_key not in self.connection_subscriptions:
                self.connection_subscriptions[conn_key] = set()
            self.connection_subscriptions[conn_key].add(list_id)

        return True

    async def unsubscribe_from_list(self, user_id: str, list_id: str, websocket: WebSocket | None = None) -> None:
        """Unsubscribe a connection from a list."""
        target_sockets = [websocket] if websocket else list(self.active_connections.get(user_id, {}).keys())

        for ws in target_sockets:
            conn_key = (user_id, ws)
            if list_id in self.list_subscribers:
                self.list_subscribers[list_id].discard(conn_key)
                if not self.list_subscribers[list_id]:
                    del self.list_subscribers[list_id]

            if conn_key in self.connection_subscriptions:
                self.connection_subscriptions[conn_key].discard(list_id)

    async def kick_user_from_list(self, user_id: str, list_id: str, reason: str = "Removed from list") -> None:
        """Kick a user from a list's chat by closing their chat-scoped connection."""
        chat_scope = f"chat:{list_id}"

        if user_id not in self.active_connections:
            return

        # Find and close all chat connections for this list
        sockets_to_close = []
        for ws, scope in list(self.active_connections[user_id].items()):
            if scope == chat_scope:
                sockets_to_close.append(ws)

        for ws in sockets_to_close:
            try:
                await ws.send_text(json.dumps({
                    "type": "kicked",
                    "payload": {"reason": reason},
                }))
                await ws.close(code=4003, reason=reason)
            except Exception:
                pass
            await self.disconnect(user_id, ws)

    async def send_notification_to_user(self, user_id: str, message: dict) -> bool:
        """
        Send a notification to a user on all their global-scoped connections.
        Chat-scoped connections never receive notifications.
        """
        if user_id not in self.active_connections:
            return False

        message_str = json.dumps(message)
        dead_sockets = []
        success = False

        for ws, scope in list(self.active_connections[user_id].items()):
            if scope != "global":
                continue

            try:
                await ws.send_text(message_str)
                success = True
            except Exception:
                dead_sockets.append(ws)

        for ws in dead_sockets:
            await self.disconnect(user_id, ws)

        return success

    async def broadcast_chat(self, list_id: str, data: dict, exclude_user_id: str | None = None) -> None:
        """Broadcast a chat message to all chat-scoped connections subscribed to this list."""
        if list_id not in self.list_subscribers:
            return

        if "type" not in data:
            data["type"] = "chat_message"

        message_str = json.dumps(data)
        chat_scope = f"chat:{list_id}"

        for user_id, ws in list(self.list_subscribers[list_id]):
            if exclude_user_id and user_id == exclude_user_id:
                continue

            if user_id in self.active_connections and ws in self.active_connections[user_id]:
                scope = self.active_connections[user_id][ws]
                if scope == chat_scope:
                    try:
                        await ws.send_text(message_str)
                    except Exception:
                        await self.disconnect(user_id, ws)

    async def disconnect_all_for_user(self, user_id: str, reason: str = "Logged out") -> None:
        """Close ALL WebSocket connections for a specific user."""
        if user_id in self.active_connections:
            sockets = list(self.active_connections[user_id].keys())
            for ws in sockets:
                try:
                    await ws.close(code=4001, reason=reason)
                except Exception:
                    pass
                await self.disconnect(user_id, ws)


manager = ConnectionManager()
