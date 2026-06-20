"""
Smart Matching — suggests study groups to students based on:
  1. Shared courses
  2. Same program / year
  3. Groups that aren't full
  4. Groups they haven't joined yet
"""
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_verified_user
from app.models.student import (
    Student, StudyGroup, GroupMember,
    CourseEnrollment
)

router = APIRouter(prefix="/matching", tags=["Smart Matching"])


@router.get("/suggestions")
async def get_group_suggestions(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    """Return a ranked list of study groups the student might want to join."""

    # Get student's enrolled course IDs
    enrolled_result = await db.execute(
        select(CourseEnrollment.course_id)
        .where(CourseEnrollment.student_id == current_user.student_id)
    )
    enrolled_course_ids = [r[0] for r in enrolled_result.all()]

    # Get groups student is already in
    member_result = await db.execute(
        select(GroupMember.group_id)
        .where(GroupMember.student_id == current_user.student_id)
    )
    already_in = {r[0] for r in member_result.all()}

    # Fetch public groups with member counts
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

    # Score each group
    scored = []
    for group in all_groups:
        member_count = len(group.members)

        if member_count >= group.max_members:
            continue  # Skip full groups

        score = 0

        # +10 points if group is for a course the student is enrolled in
        if group.course_id and group.course_id in enrolled_course_ids:
            score += 10

        # +3 points for every 10% of capacity still available (prefer active but not full)
        available_pct = 1 - (member_count / group.max_members)
        score += int(available_pct * 5)

        # +2 points if group has at least 2 members (active group)
        if member_count >= 2:
            score += 2

        scored.append({
            "group_id": str(group.group_id),
            "group_name": group.group_name,
            "description": group.description,
            "course_code": group.course.course_code if group.course else None,
            "course_name": group.course.course_name if group.course else None,
            "member_count": member_count,
            "max_members": group.max_members,
            "match_score": score,
            "reason": _match_reason(group, enrolled_course_ids, member_count),
        })

    # Sort by score descending
    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:limit]


def _match_reason(group: StudyGroup, enrolled_courses: list, member_count: int) -> str:
    """Human-readable explanation of why this group was suggested."""
    reasons = []

    if group.course_id and group.course_id in enrolled_courses:
        reasons.append(f"matches your enrolled course ({group.course.course_code})")

    if member_count == 0:
        reasons.append("be the first to join")
    elif member_count < 5:
        reasons.append("small group forming")
    else:
        reasons.append(f"{member_count} active members")

    return " · ".join(reasons) if reasons else "Suggested for you"
