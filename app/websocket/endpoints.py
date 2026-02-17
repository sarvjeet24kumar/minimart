"""
WebSocket Endpoints
"""

import json as _json
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.chat_service import ChatService
from app.services.redis_service import RedisService
from app.websocket.handlers import WebSocketHandler
from app.websocket.manager import manager

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

if settings.is_development:

    @router.get("/test/chat")
    async def chat_test_page():
        return FileResponse(_TEMPLATES_DIR / "chat.html", media_type="text/html")

    @router.get("/test/notifications")
    async def notifications_test_page():
        return FileResponse(_TEMPLATES_DIR / "notifications.html", media_type="text/html")

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time updates.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
        
        # Check if token is blacklisted (logout)
        token_id = payload.get("jti")
        if token_id and await RedisService.is_access_token_blacklisted(token_id):
            await websocket.close(code=4001, reason="Token revoked")
            return

        user_id = payload.get("sub")
        result = await db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()
        
        if not user or not (user.is_active and not user.deleted_at):
            await websocket.close(code=4001, reason="User not found, inactive, or deleted")
            return
        
    except JWTError as e:
        await websocket.close(code=4001, reason=f"Invalid token: {str(e)}")
        return
    
    # Connect with "global" scope
    await websocket.accept()
    await manager.connect(websocket, str(user.id), scope="global")
    handler = WebSocketHandler(websocket, user, db)
    
    try:
        # Send connection confirmation
        await websocket.send_text('{"type": "connected", "payload": {}}')
        
        # Message loop
        while True:
            message = await websocket.receive_text()
            await handler.handle_message(message)
            
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(str(user.id), websocket)


@router.websocket("/ws/shopping-lists/{list_id}/chat")
async def chat_websocket_endpoint(
    websocket: WebSocket,
    list_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db), 
):
    """
    Dedicated WebSocket endpoint for list-scoped real-time chat.
    """
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return

        # Check if token is blacklisted (logout)
        token_id = payload.get("jti")
        if token_id and await RedisService.is_access_token_blacklisted(token_id):
            await websocket.close(code=4001, reason="Token revoked")
            return

        user_id = payload.get("sub")
        result = await db.execute(
            select(User).where(User.id == UUID(user_id))
        )
        user = result.scalar_one_or_none()

        if not user or not (user.is_active and not user.deleted_at):
            await websocket.close(code=4001, reason="User not found, inactive, or deleted")
            return

    except JWTError as e:
        await websocket.close(code=4001, reason=f"Invalid token: {str(e)}")
        return

    # Validate membership & Subscribe
    try:
        list_uuid = UUID(list_id)
    except ValueError:
        await websocket.close(code=4003, reason="Invalid list_id format")
        return

    # Use manager to connect and subscribe (Dedicated scope for this list)
    chat_scope = f"chat:{list_id}"
    await websocket.accept()
    await manager.connect(websocket, str(user.id), scope=chat_scope)
    subscribed = await manager.subscribe_to_list(str(user.id), list_id, db, websocket=websocket)
    
    if not subscribed:
        await websocket.close(code=4003, reason="Not a member of this list")
        await manager.disconnect(str(user.id), websocket)
        return

    chat_service = ChatService(db)
    try:
        # Send connection confirmation
        await websocket.send_text(_json.dumps({
            "type": "connected",
            "payload": {"list_id": list_id},
        }))

        # Message loop
        while True:
            raw = await websocket.receive_text()

            try:
                data = _json.loads(raw)
            except _json.JSONDecodeError:
                await websocket.send_text(_json.dumps({
                    "type": "error",
                    "payload": {"message": "Invalid JSON"},
                }))
                continue

            msg_type = data.get("type")

            if msg_type == "chat_message":
                content = data.get("message", "").strip()
                if not content:
                    await websocket.send_text(_json.dumps({
                        "type": "error",
                        "payload": {"message": "Message content cannot be empty"},
                    }))
                    continue

                # Re-validate membership on every send
                try:
                    await chat_service._verify_membership(list_uuid, user)
                except Exception:
                    await websocket.send_text(_json.dumps({
                        "type": "error",
                        "payload": {"message": "You are no longer a member of this list"},
                    }))
                    continue

                # Persist & Broadcast
                try:
                    await chat_service.send_message(list_uuid, user, content)
                except Exception as e:
                    print(f"Chat WS: Error in send_message: {e}")
                    await websocket.send_text(_json.dumps({
                        "type": "error",
                        "payload": {"message": f"Server error: {str(e)}"},
                    }))
                    continue

            elif msg_type == "ping":
                await websocket.send_text(_json.dumps({"type": "pong", "payload": {}}))

            else:
                await websocket.send_text(_json.dumps({
                    "type": "error",
                    "payload": {"message": f"Unknown message type: {msg_type}"},
                }))

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(str(user.id), websocket)
