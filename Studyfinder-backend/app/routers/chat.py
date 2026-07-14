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
from sqlalchemy import select, desc
from datetime import datetime

from app.core.database import get_db, AsyncSessionLocal
from app.core.security import decode_token, get_current_user
from app.models.student import Student, Message, GroupMember, StudyGroup
from app.schemas.schemas import MessageCreate, MessageOut, MessageResponse

router = APIRouter(prefix="/chat", tags=["Chat"])


# ── Connection Manager ──────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, group_id: str, websocket: WebSocket):
        await websocket.accept()
        if group_id not in self.active_connections:
            self.active_connections[group_id] = set()
        self.active_connections[group_id].add(websocket)

    def disconnect(self, group_id: str, websocket: WebSocket):
        if group_id in self.active_connections:
            self.active_connections[group_id].discard(websocket)
            if not self.active_connections[group_id]:
                del self.active_connections[group_id]

    async def broadcast(self, group_id: str, message: dict, exclude: WebSocket = None):
        if group_id not in self.active_connections:
            return
        dead = set()
        for ws in self.active_connections[group_id]:
            if ws == exclude:
                continue
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections[group_id].discard(ws)


manager = ConnectionManager()


# ── Helper to get student name ──────────────────────────────────────

def get_student_name(student: Student) -> str:
    if hasattr(student, 'get_full_name'):
        return student.get_full_name()
    return f"{student.first_name} {student.last_name}"


# ── REST Endpoints ───────────────────────────────────────────────────

@router.post("/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    payload: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_user)
):
    """Send a message via HTTP"""
    
    # Check if student is a member of the group
    membership = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == payload.group_id,
            GroupMember.student_id == current_student.student_id
        )
    )
    membership = membership.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="You are not a member of this group")
    
    # Create message
    new_message = Message(
        group_id=payload.group_id,
        sender_id=current_student.student_id,
        content=payload.content,
        message_type=payload.message_type or "text",
        sent_at=datetime.utcnow()
    )
    
    db.add(new_message)
    await db.flush()
    
    # Increment unread count for all members except sender
    members = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == payload.group_id,
            GroupMember.student_id != current_student.student_id
        )
    )
    for member in members.scalars().all():
        member.unread_count = (member.unread_count or 0) + 1
    
    await db.commit()
    await db.refresh(new_message)
    
    sender_name = get_student_name(current_student)
    
    return MessageOut(
        message_id=new_message.message_id,
        group_id=new_message.group_id,
        sender_id=new_message.sender_id,
        sender_name=sender_name,
        content=new_message.content,
        message_type=new_message.message_type,
        is_edited=new_message.is_edited,
        sent_at=new_message.sent_at
    )


@router.get("/{group_id}/history")
async def get_chat_history(
    group_id: UUID,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_user)
):
    """Get chat history for a group"""
    
    # Check if student is a member
    membership = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_student.student_id
        )
    )
    if not membership.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You are not a member of this group")
    
    # Get messages
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(Message)
        .options(selectinload(Message.sender))
        .where(Message.group_id == group_id)
        .order_by(desc(Message.sent_at))
        .limit(limit)
    )
    messages = result.scalars().all()
    messages.reverse()
    
    return [
        {
            "message_id": str(m.message_id),
            "sender_id": str(m.sender_id),
            "sender_name": get_student_name(m.sender) if m.sender else "Unknown",
            "content": m.content,
            "sent_at": m.sent_at.isoformat() if m.sent_at else None,
            "message_type": m.message_type,
            "is_edited": m.is_edited,
        }
        for m in messages
    ]


# ─── MARK MESSAGES AS READ ──────────────────────────────────────────

@router.post("/{group_id}/read")
async def mark_as_read(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_user)
):
    """Mark all messages in a group as read"""
    member = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_student.student_id
        )
    )
    member = member.scalar_one_or_none()
    if member:
        member.unread_count = 0
        await db.commit()
    
    return {"message": "Marked as read"}


# ─── GET UNREAD COUNTS ──────────────────────────────────────────────

@router.get("/unread")
async def get_unread_counts(
    db: AsyncSession = Depends(get_db),
    current_student: Student = Depends(get_current_user)
):
    """Get unread message counts for all groups"""
    result = await db.execute(
        select(GroupMember.group_id, GroupMember.unread_count, GroupMember.is_priority)
        .where(GroupMember.student_id == current_student.student_id)
        .where(GroupMember.unread_count > 0)
    )
    groups = result.all()
    
    return [
        {
            "group_id": str(g[0]),
            "unread_count": g[1],
            "is_priority": g[2]
        }
        for g in groups
    ]


# ─── WEBSOCKET ────────────────────────────────────────────────────────

@router.websocket("/{group_id}")
async def chat_websocket(
    group_id: UUID,
    websocket: WebSocket,
    token: str = Query(...),
):
    """Real-time chat WebSocket"""
    
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token type")
            return
        student_id = payload.get("sub")
        if not student_id:
            await websocket.close(code=4001, reason="Invalid token")
            return
    except HTTPException:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Student).where(Student.student_id == student_id))
        student = result.scalar_one_or_none()
        if not student:
            await websocket.close(code=4001, reason="Student not found")
            return
        
        group_result = await db.execute(
            select(StudyGroup).where(StudyGroup.group_id == group_id)
        )
        group = group_result.scalar_one_or_none()
        if not group:
            await websocket.close(code=4004, reason="Group not found")
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
    
    student_name = get_student_name(student)
    
    await manager.broadcast(group_key, {
        "type": "system",
        "message": f"{student_name} joined the chat",
        "sender_name": "System"
    }, exclude=websocket)
    
    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            
            if data.get("type") == "typing":
                await manager.broadcast(group_key, {
                    "type": "typing",
                    "sender_name": get_student_name(student),
                    "is_typing": data.get("is_typing", True)
                }, exclude=websocket)
                continue
            
            content = data.get("content", "").strip()
            if not content:
                continue
            
            async with AsyncSessionLocal() as db:
                membership = await db.execute(
                    select(GroupMember).where(
                        GroupMember.group_id == group_id,
                        GroupMember.student_id == student.student_id
                    )
                )
                if not membership.scalar_one_or_none():
                    await websocket.close(code=4003, reason="Not a group member")
                    return
                
                msg = Message(
                    group_id=group_id,
                    sender_id=student.student_id,
                    content=content,
                    message_type=data.get("message_type", "text"),
                    sent_at=datetime.utcnow()
                )
                db.add(msg)
                await db.flush()
                
                members = await db.execute(
                    select(GroupMember).where(
                        GroupMember.group_id == group_id,
                        GroupMember.student_id != student.student_id
                    )
                )
                for member in members.scalars().all():
                    member.unread_count = (member.unread_count or 0) + 1
                
                await db.commit()
                await db.refresh(msg)
            
            await manager.broadcast(group_key, {
                "type": "message",
                "message_id": str(msg.message_id),
                "sender_id": str(student.student_id),
                "sender_name": get_student_name(student),
                "content": content,
                "sent_at": msg.sent_at.isoformat(),
                "message_type": msg.message_type,
                "is_edited": msg.is_edited,
            })
            
    except WebSocketDisconnect:
        manager.disconnect(group_key, websocket)
        await manager.broadcast(group_key, {
            "type": "system",
            "message": f"{get_student_name(student)} left the chat",
            "sender_name": "System"
        })
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(group_key, websocket)