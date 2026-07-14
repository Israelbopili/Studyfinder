from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_verified_user
from app.models.student import Student, StudyGroup, GroupMember, StudentCourse, Course

router = APIRouter(prefix="/matching", tags=["Smart Matching"])

@router.get("/suggestions")
async def get_group_suggestions(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    # Get student's enrolled courses
    enrolled_result = await db.execute(
        select(StudentCourse.course_id, Course.course_code)
        .join(Course, Course.course_id == StudentCourse.course_id)
        .where(StudentCourse.student_id == current_user.student_id)
    )
    enrolled_courses = {row[0]: row[1] for row in enrolled_result.all()}
    enrolled_course_ids = list(enrolled_courses.keys())

    # Get groups user is already in
    member_result = await db.execute(
        select(GroupMember.group_id)
        .where(GroupMember.student_id == current_user.student_id)
    )
    already_in = {r[0] for r in member_result.all()}

    # Get all public groups
    groups_result = await db.execute(
        select(StudyGroup)
        .options(selectinload(StudyGroup.members), selectinload(StudyGroup.course))
        .where(
            StudyGroup.is_active == True,
            StudyGroup.privacy_status == "public",
            StudyGroup.group_id.not_in(already_in) if already_in else True,
        )
    )
    all_groups = groups_result.scalars().all()

    scored = []
    for group in all_groups:
        member_count = len(group.members)
        if member_count >= group.max_members:
            continue

        score = 0
        reasons = []

        # Course match (highest weight)
        if group.course_id and group.course_id in enrolled_course_ids:
            score += 20
            reasons.append(f"📚 Matches your course")

        # Membership activity
        if member_count == 0:
            score += 10
            reasons.append("🚀 Be the first to join!")
        elif member_count < 5:
            score += 8
            reasons.append(f"👥 Small group ({member_count} members)")
        elif member_count < 15:
            score += 5
            reasons.append(f"👥 Active group ({member_count} members)")
        else:
            score += 3
            reasons.append(f"👥 Popular group ({member_count} members)")

        # Available spots
        available_pct = 1 - (member_count / group.max_members)
        score += int(available_pct * 5)
        if available_pct > 0.5:
            reasons.append(f"✅ {group.max_members - member_count} spots available")

        # Recent activity boost
        if group.created_at:
            days_old = (datetime.utcnow() - group.created_at).days
            if days_old < 7:
                score += 3
                reasons.append("🆕 New group")

        scored.append({
            "group_id": str(group.group_id),
            "group_name": group.group_name,
            "description": group.description,
            "course_code": group.course.course_code if group.course else None,
            "course_name": group.course.course_name if group.course else None,
            "member_count": member_count,
            "max_members": group.max_members,
            "match_score": score,
            "reasons": reasons,
            "privacy_status": group.privacy_status,
        })

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:limit]