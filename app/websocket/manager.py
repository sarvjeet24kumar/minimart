"""
WebSocket Connection Manager

Manages WebSocket connections and broadcasts.
Simplified for single-server deployment (Redis Pub/Sub removed).
"""

import json
from uuid import UUID

from fastapi import WebSocket
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shopping_list_member import ShoppingListMember


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    Supports multiple connections per user and scoped subscriptions.
    """

    def __init__(self):
        self.active_connections: dict[str, dict[WebSocket, str]] = {}
        self.list_subscribers: dict[str, set[tuple[str, WebSocket]]] = {}
        self.connection_subscriptions: dict[tuple[str, WebSocket], set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, scope: str = "global") -> None:
        """Accept a new WebSocket connection with a specific scope."""
        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}
        
        self.active_connections[user_id][websocket] = scope
        self.connection_subscriptions[(user_id, websocket)] = set()

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection."""
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
        Subscribe a specific connection (or all user's connections if websocket is None) to a list.
        """
        result = await db.execute(
            select(ShoppingListMember).where(
                and_(
                    ShoppingListMember.shopping_list_id == UUID(list_id),
                    ShoppingListMember.user_id == UUID(user_id),
                    ShoppingListMember.deleted_at.is_(None),
                )
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            return False

        # Determine which connections to subscribe
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
        """Unsubscribe a specific connection or all user's connections from a list."""
        target_sockets = [websocket] if websocket else list(self.active_connections.get(user_id, {}).keys())
        
        for ws in target_sockets:
            conn_key = (user_id, ws)
            if list_id in self.list_subscribers:
                self.list_subscribers[list_id].discard(conn_key)
                if not self.list_subscribers[list_id]:
                    del self.list_subscribers[list_id]
            
            if conn_key in self.connection_subscriptions:
                self.connection_subscriptions[conn_key].discard(list_id)

    async def _broadcast_to_list(
        self, 
        list_id: str, 
        message: dict, 
        exclude_user_id: str | None = None,
        only_scoped: bool = False,
        target_scope: str | None = None
    ) -> None:
        """
        Internal: Broadcast a message to all connections explicitly subscribed to this list.
        """
        if list_id not in self.list_subscribers:
            return
        
        message_str = json.dumps(message)
        subscribers = list(self.list_subscribers[list_id])
        
        for user_id, ws in subscribers:
            if exclude_user_id and user_id == exclude_user_id:
                continue

            if user_id in self.active_connections and ws in self.active_connections[user_id]:
                scope = self.active_connections[user_id][ws]
            
                effective_target = target_scope or list_id
                is_appropriate_scope = (scope == effective_target) or (scope == "global" and not only_scoped)

                if is_appropriate_scope:
                    try:
                        await ws.send_text(message_str)
                    except Exception:
                        await self.disconnect(user_id, ws)

    def is_user_subscribed(self, user_id: str, list_id: str) -> bool:
        """Check if a user has at least one connection subscribed to the list."""
        if list_id not in self.list_subscribers:
            return False

        user_conns = self.active_connections.get(user_id, {}).keys()
        for ws in user_conns:
            if (user_id, ws) in self.list_subscribers[list_id]:
                return True
        return False

    def is_user_watching_list(self, user_id: str, list_id: str) -> bool:
        """Check if a user is actively watching a list (scoped connection)."""
        if user_id not in self.active_connections:
            return False
        
        for ws, scope in self.active_connections[user_id].items():
            if scope == list_id or (scope and scope.startswith(f"chat:{list_id}")):
                return True
        return False
                
    async def broadcast_event(
        self, 
        list_id: str, 
        event_type: str, 
        data: dict, 
        exclude_user_id: str | None = None,
        only_scoped: bool = False,
        target_scope: str | None = None
    ) -> None:
        """Broadcast a structured event to all list subscribers."""
        if event_type == "member_removed" or event_type == "member_left":
            removed_user_id = str(data.get("user_id"))
            if removed_user_id:
                await self.kick_user_from_list(removed_user_id, list_id, event_type)

        await self._broadcast_to_list(
            list_id,
            {
                "type": "event",
                "payload": {
                    "event": event_type,
                    "list_id": list_id,
                    "data": data,
                },
            },
            exclude_user_id=exclude_user_id,
            only_scoped=only_scoped,
            target_scope=target_scope
        )

    async def broadcast_chat(
        self,
        list_id: str,
        data: dict,
        exclude_user_id: str | None = None,
    ) -> None:
        """Broadcast a flat chat message to list subscribers in the chat scope."""
        if "type" not in data:
            data["type"] = "chat_message"
            
        await self._broadcast_to_list(
            list_id,
            data,
            exclude_user_id=exclude_user_id,
            only_scoped=True,
            target_scope=f"chat:{list_id}"
        )

    async def send_to_user(self, user_id: str, message: dict) -> bool:
        """Send a message to a specific user (on all their connections)."""
        if user_id not in self.active_connections or not self.active_connections[user_id]:
            return False
        
        message_str = json.dumps(message)
        dead_sockets = []
        success = False
        
        sockets = list(self.active_connections[user_id].keys())
        for ws in sockets:
            try:
                await ws.send_text(message_str)
                success = True
            except Exception:
                dead_sockets.append(ws)
        
        for ws in dead_sockets:
            await self.disconnect(user_id, ws)
            
        return success

    async def send_notification_to_user(self, user_id: str, message: dict, related_list_id: str | None = None) -> bool:
        """
        Send a notification to a specific user, BUT skip connections 
        that are already explicitly subscribed to the related_list_id.
        """
        if user_id not in self.active_connections or not self.active_connections[user_id]:
            return False
        
        message_str = json.dumps(message)
        dead_sockets = []
        success = False
        
        sockets = list(self.active_connections[user_id].keys())
        for ws in sockets:
            if related_list_id:
                conn_key = (user_id, ws)
                if related_list_id in self.list_subscribers and conn_key in self.list_subscribers[related_list_id]:
                    continue

            try:
                await ws.send_text(message_str)
                success = True
            except Exception:
                dead_sockets.append(ws)
        
        for ws in dead_sockets:
            await self.disconnect(user_id, ws)
            
        return success

    async def disconnect_all_for_user(self, user_id: str, reason: str = "Logged out") -> None:
        """Close ALL WebSocket connections for a specific user immediately."""
        if user_id in self.active_connections:
            sockets = list(self.active_connections[user_id].keys())
            for ws in sockets:
                try:
                    await ws.close(code=4001, reason=reason)
                except Exception:
                    pass
                await self.disconnect(user_id, ws)

    async def kick_user_from_list(self, user_id: str, list_id: str, reason: str) -> None:
        """Kick a user from a specific list scope and close their dedicated sockets."""
        await self.send_to_user(user_id, {
            "type": "kicked",
            "payload": {
                "list_id": list_id,
                "reason": reason,
            },
        })

        if user_id in self.active_connections:
            to_close = [
                ws for ws, scope in self.active_connections[user_id].items()
                if scope == list_id or (scope and scope.startswith(f"chat:{list_id}"))
            ]
            for ws in to_close:
                try:
                    await ws.close(code=4003, reason=f"Kicked: {reason}")
                except Exception:
                    pass
                await self.disconnect(user_id, ws)

        await self.unsubscribe_from_list(user_id, list_id)


manager = ConnectionManager()
