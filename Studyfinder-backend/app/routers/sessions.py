from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student, GroupMember, Session
from app.schemas.schemas import StudySessionCreate, StudySessionOut, MessageResponse

router = APIRouter(prefix="/sessions", tags=["Study Sessions"])


async def check_group_member(group_id: UUID, student_id: UUID, db: AsyncSession):
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == student_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You must be a group member to do this")


@router.post("/", response_model=StudySessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: StudySessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    await check_group_member(data.group_id, current_user.student_id, db)

    session = Session(
        title=data.title,
        description=data.description,
        group_id=data.group_id,
        created_by=current_user.student_id,
        location=data.location,
        meeting_link=data.meeting_link,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/group/{group_id}", response_model=list[StudySessionOut])
async def list_group_sessions(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    # Check if user is a member
    member_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id
        )
    )
    if not member_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You must be a group member to view sessions")
    
    result = await db.execute(
        select(Session)
        .where(Session.group_id == group_id, Session.status != "cancelled")
        .order_by(Session.start_time)
    )
    return result.scalars().all()


@router.delete("/{session_id}", response_model=MessageResponse)
async def cancel_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    result = await db.execute(select(Session).where(Session.session_id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.created_by != current_user.student_id:
        raise HTTPException(status_code=403, detail="Only the session creator can cancel it")

    session.status = "cancelled"
    await db.commit()
    return {"message": "Session cancelled"}