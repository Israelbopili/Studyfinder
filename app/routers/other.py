from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_verified_user
from app.models.student import (
    Student, Course, StudySession, Resource,
    Notification, StudyGroup, GroupMember
)
from app.schemas.schemas import (
    CourseCreate, CourseOut,
    StudySessionCreate, StudySessionOut,
    ResourceOut, NotificationOut, MessageResponse
)

# ── Courses ──────────────────────────────────────────────────────────

courses_router = APIRouter(prefix="/courses", tags=["Courses"])


@courses_router.get("/", response_model=list[CourseOut])
async def list_courses(
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    query = select(Course).where(Course.is_active == True)
    if search:
        query = query.where(
            Course.course_name.ilike(f"%{search}%") |
            Course.course_code.ilike(f"%{search}%")
        )
    result = await db.execute(query)
    return result.scalars().all()


@courses_router.post("/", response_model=CourseOut, status_code=201)
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    if not current_user.is_staff:
        raise HTTPException(status_code=403, detail="Only staff can create courses")

    existing = await db.execute(select(Course).where(Course.course_code == data.course_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Course code already exists")

    course = Course(**data.model_dump())
    db.add(course)
    await db.flush()
    return course


@courses_router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    result = await db.execute(select(Course).where(Course.course_id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


# ── Sessions ─────────────────────────────────────────────────────────

sessions_router = APIRouter(prefix="/sessions", tags=["Study Sessions"])


async def _check_group_member(group_id: UUID, student: Student, db: AsyncSession):
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == student.student_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You must be a group member to do this")


@sessions_router.post("/", response_model=StudySessionOut, status_code=201)
async def create_session(
    data: StudySessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    await _check_group_member(data.group_id, current_user, db)

    session = StudySession(
        title=data.title,
        description=data.description,
        group_id=data.group_id,
        creator_id=current_user.student_id,
        location=data.location,
        meeting_link=data.meeting_link,
        scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes,
    )
    db.add(session)
    await db.flush()
    return session


@sessions_router.get("/group/{group_id}", response_model=list[StudySessionOut])
async def list_group_sessions(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    await _check_group_member(group_id, current_user, db)

    result = await db.execute(
        select(StudySession)
        .where(StudySession.group_id == group_id, StudySession.is_cancelled == False)
        .order_by(StudySession.scheduled_at)
    )
    return result.scalars().all()


@sessions_router.delete("/{session_id}", response_model=MessageResponse)
async def cancel_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    result = await db.execute(select(StudySession).where(StudySession.session_id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.creator_id != current_user.student_id:
        raise HTTPException(status_code=403, detail="Only the session creator can cancel it")

    session.is_cancelled = True
    return {"message": "Session cancelled"}


# ── Resources ─────────────────────────────────────────────────────────

resources_router = APIRouter(prefix="/resources", tags=["Resources"])


@resources_router.get("/group/{group_id}", response_model=list[ResourceOut])
async def list_group_resources(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    await _check_group_member(group_id, current_user, db)

    result = await db.execute(
        select(Resource)
        .where(Resource.group_id == group_id)
        .order_by(Resource.created_at.desc())
    )
    return result.scalars().all()


@resources_router.post("/group/{group_id}", response_model=ResourceOut, status_code=201)
async def upload_resource(
    group_id: UUID,
    title: str,
    description: str = None,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    await _check_group_member(group_id, current_user, db)

    # In production: upload file to S3 and get URL back
    # For now, store the filename as URL placeholder
    file_url = f"/media/resources/{group_id}/{file.filename}"
    file_size = 0

    try:
        contents = await file.read()
        file_size = len(contents)
    finally:
        await file.close()

    resource = Resource(
        title=title,
        description=description,
        file_url=file_url,
        file_type=file.content_type,
        file_size=file_size,
        group_id=group_id,
        uploader_id=current_user.student_id,
    )
    db.add(resource)
    await db.flush()
    return resource


@resources_router.delete("/{resource_id}", response_model=MessageResponse)
async def delete_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    result = await db.execute(select(Resource).where(Resource.resource_id == resource_id))
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if resource.uploader_id != current_user.student_id and not current_user.is_staff:
        raise HTTPException(status_code=403, detail="You can only delete your own resources")

    await db.delete(resource)
    return {"message": "Resource deleted"}


# ── Notifications ─────────────────────────────────────────────────────

notifications_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notifications_router.get("/", response_model=list[NotificationOut])
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


@notifications_router.put("/{notification_id}/read", response_model=MessageResponse)
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
    return {"message": "Marked as read"}


@notifications_router.put("/mark-all-read", response_model=MessageResponse)
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

    return {"message": f"Marked {len(notifications)} notifications as read"}
