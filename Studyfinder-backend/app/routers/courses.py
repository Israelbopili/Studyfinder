from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.core.database import get_db
from app.core.security import get_verified_user
from app.models.student import Course, Student  # ← ADDED Student
from app.schemas.schemas import CourseOut

router = APIRouter(prefix="/courses", tags=["Courses"])

@router.get("/", response_model=list[CourseOut])
async def list_courses(
    search: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),  # ← Now Student is defined
):
    query = select(Course).where(Course.is_active == True)
    if search:
        query = query.where(
            or_(
                Course.course_name.ilike(f"%{search}%"),
                Course.course_code.ilike(f"%{search}%")
            )
        )
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),  # ← Now Student is defined
):
    result = await db.execute(select(Course).where(Course.course_id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course