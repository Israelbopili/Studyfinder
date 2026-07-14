from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user, get_verified_user
from app.models.student import Student, StudentCourse, Course
from app.schemas.schemas import StudentOut, StudentProfileUpdate, CourseOut, MessageResponse

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/profile", response_model=StudentOut)
async def get_profile(current_user: Student = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=StudentOut)
async def update_profile(
    data: StudentProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user),
):
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/my-courses", response_model=list[CourseOut])
async def get_my_courses(
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    result = await db.execute(
        select(Course)
        .join(StudentCourse, StudentCourse.course_id == Course.course_id)
        .where(StudentCourse.student_id == current_user.student_id)
    )
    return result.scalars().all()


@router.post("/enroll/{course_id}", response_model=MessageResponse)
async def enroll_in_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    # Check course exists
    result = await db.execute(select(Course).where(Course.course_id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Check not already enrolled
    existing = await db.execute(
        select(StudentCourse).where(
            StudentCourse.student_id == current_user.student_id,
            StudentCourse.course_id == course_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already enrolled in this course")

    enrollment = StudentCourse(
        student_id=current_user.student_id,
        course_id=course_id
    )
    db.add(enrollment)
    await db.commit()

    return {"message": f"Successfully enrolled in {course.course_name}"}


@router.delete("/unenroll/{course_id}", response_model=MessageResponse)
async def unenroll_from_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    result = await db.execute(
        select(StudentCourse).where(
            StudentCourse.student_id == current_user.student_id,
            StudentCourse.course_id == course_id
        )
    )
    enrollment = result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")

    await db.delete(enrollment)
    await db.commit()
    return {"message": "Successfully unenrolled"}