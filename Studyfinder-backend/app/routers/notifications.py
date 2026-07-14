from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_verified_user
from app.models.student import Student, Notification
from app.schemas.schemas import NotificationOut, MessageResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=list[NotificationOut])
async def get_notifications(
    unread_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    query = select(Notification).where(Notification.student_id == current_user.student_id)
    if unread_only:
        query = query.where(Notification.is_read == False)
    query = query.order_by(Notification.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()

@router.put("/{notification_id}/read", response_model=MessageResponse)
async def mark_as_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.notification_id == notification_id,
            Notification.student_id == current_user.student_id
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    return {"message": "Marked as read"}

@router.put("/mark-all-read", response_model=MessageResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    result = await db.execute(
        select(Notification).where(
            Notification.student_id == current_user.student_id,
            Notification.is_read == False
        )
    )
    notifications = result.scalars().all()
    for n in notifications:
        n.is_read = True
    await db.commit()

    return {"message": f"Marked {len(notifications)} notifications as read"}