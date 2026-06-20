"""
WebSocket Chat — Real-time group messaging

Each group has its own "room". Students connect via:
  ws://your-api/api/v1/chat/{group_id}?token=<access_token>

Messages are broadcast to all connected members in the same group.
"""
import json
from uuid import UUID
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import decode_token
from app.models.student import Student, ChatMessage, GroupMember

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Connection Manager ────────────────────────────────────────────────

class ConnectionManager:
    """Tracks active WebSocket connections per group room."""

    def __init__(self):
        # group_id (str) → set of WebSockets
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def connect(self, group_id: str, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(group_id, set()).add(websocket)

    def disconnect(self, group_id: str, websocket: WebSocket):
        if group_id in self.rooms:
            self.rooms[group_id].discard(websocket)
            if not self.rooms[group_id]:
                del self.rooms[group_id]

    async def broadcast(self, group_id: str, message: dict, exclude: WebSocket = None):
        if group_id not in self.rooms:
            return
        dead = set()
        for ws in self.rooms[group_id]:
            if ws == exclude:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.rooms[group_id].discard(ws)


manager = ConnectionManager()


# ── WebSocket Endpoint ────────────────────────────────────────────────

@router.websocket("/{group_id}")
async def chat_websocket(
    group_id: UUID,
    websocket: WebSocket,
    token: str = Query(..., description="JWT access token"),
):
    # Authenticate user from token
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
        student_id = payload.get("sub")
    except HTTPException:
        await websocket.close(code=4001, reason="Invalid token")
        return

    async with AsyncSessionLocal() as db:
        # Check student exists
        result = await db.execute(select(Student).where(Student.student_id == student_id))
        student = result.scalar_one_or_none()
        if not student:
            await websocket.close(code=4001, reason="Student not found")
            return

        # Check student is a group member
        membership = await db.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id,
                GroupMember.student_id == student.student_id
            )
        )
        if not membership.scalar_one_or_none():
            await websocket.close(code=4003, reason="Not a group member")
            return

    group_key = str(group_id)
    await manager.connect(group_key, websocket)

    # Announce join
    await manager.broadcast(group_key, {
        "type": "system",
        "message": f"{student.get_full_name()} joined the chat",
    }, exclude=websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            content = data.get("content", "").strip()

            if not content:
                continue

            # Persist message to DB
            async with AsyncSessionLocal() as db:
                msg = ChatMessage(
                    group_id=group_id,
                    sender_id=student.student_id,
                    content=content,
                )
                db.add(msg)
                await db.commit()
                await db.refresh(msg)

            # Broadcast to everyone in room
            await manager.broadcast(group_key, {
                "type": "message",
                "message_id": str(msg.message_id),
                "sender_id": str(student.student_id),
                "sender_name": student.get_full_name(),
                "content": content,
                "created_at": msg.created_at.isoformat(),
            })

    except WebSocketDisconnect:
        manager.disconnect(group_key, websocket)
        await manager.broadcast(group_key, {
            "type": "system",
            "message": f"{student.get_full_name()} left the chat",
        })


# ── REST: Fetch Chat History ──────────────────────────────────────────

@router.get("/{group_id}/history")
async def get_chat_history(
    group_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(lambda: None),  # replaced below
):
    """Get the last N messages for a group (for loading chat history on connect)."""
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.group_id == group_id, ChatMessage.is_deleted == False)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    messages.reverse()  # oldest first

    return [
        {
            "message_id": str(m.message_id),
            "sender_id": str(m.sender_id),
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
