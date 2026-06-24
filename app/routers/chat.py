import json
from uuid import UUID
from typing import Dict, Set
from fastapi import (
    APIRouter, 
    WebSocket, 
    WebSocketDisconnect, 
    Depends, 
    Query, 
    HTTPException, 
    status
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import decode_token, get_current_user
from app.models.student import Student, Message, GroupMember
from app.schemas.schemas import MessageCreate, MessageResponse

# Instantiated once with proper prefix configuration
router = APIRouter(prefix="/chat", tags=["Chat"])




class ConnectionManager:
    def __init__(self):
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


# ── REST Endpoints ───────────────────────────────────────────────────

@router.post("/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_user)
):
    """
    HTTP POST Endpoint to send chat messages via Postman / REST Client
    Resolves to: POST /api/v1/chat/messages
    """
    # Create a new Message instance using the user payload info
    new_message = Message(
        group_id=payload.group_id,
        sender_id=current_student.student_id,  # Linked to verified logged-in student
        content=payload.content,
        meta_data=payload.meta_data            # Validated JSONB configuration dictionary
    )
    
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)
    
    return new_message


@router.get("/{group_id}/history")
async def get_chat_history(
    group_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    HTTP GET Endpoint to fetch historical message payloads
    Resolves to: GET /api/v1/chat/{group_id}/history
    """
    result = await db.execute(
        select(Message)
        .where(Message.group_id == group_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    messages.reverse()

    return [
        {
            "message_id": str(m.message_id),
            "sender_id": str(m.sender_id),
            "content": m.content,
            "sent_at": m.created_at.isoformat() if m.created_at else None,
            "meta_data": m.meta_data
        }
        for m in messages
    ]


# ── WebSocket Server Endpoint ──────────────────────────────────────────

@router.websocket("/{group_id}")
async def chat_websocket(
    group_id: UUID,
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Real-time duplex WebSocket stream implementation
    Resolves to: ws://127.0.0.1:8000/api/v1/chat/{group_id}?token=YOUR_JWT_HERE
    """
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
        result = await db.execute(select(Student).where(Student.student_id == student_id))
        student = result.scalar_one_or_none()
        if not student:
            await websocket.close(code=4001, reason="Student not found")
            return

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

    # Notify room channel members that a student connected
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

            async with AsyncSessionLocal() as db:
                msg = Message(
                    group_id=group_id,
                    sender_id=student.student_id,
                    content=content,
                    meta_data=data.get("meta_data", {})
                )
                db.add(msg)
                await db.commit()
                await db.refresh(msg)

            # Broadcast incoming client packets out to active web channel nodes
            await manager.broadcast(group_key, {
                "type": "message",
                "message_id": str(msg.message_id),
                "sender_id": str(student.student_id),
                "sender_name": student.get_full_name(),
                "content": content,
                "sent_at": msg.created_at.isoformat() if hasattr(msg, "created_at") else msg.sent_at.isoformat(),
                "meta_data": msg.meta_data
            })

    except WebSocketDisconnect:
        manager.disconnect(group_key, websocket)
        await manager.broadcast(group_key, {
            "type": "system",
            "message": f"{student.get_full_name()} left the chat",
        })