from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_verified_user
from app.models.student import Student, StudyGroup, GroupMember, StudentCourse
from app.schemas.schemas import (
    StudyGroupCreate, StudyGroupUpdate, StudyGroupOut,
    StudyGroupDetail, MemberOut, AddMemberRequest,
    UpdateRoleRequest, MessageResponse
)

router = APIRouter(prefix="/groups", tags=["Study Groups"])


# ── Helpers ──────────────────────────────────────────────────────────

async def get_group_or_404(group_id: UUID, db: AsyncSession) -> StudyGroup:
    result = await db.execute(
        select(StudyGroup)
        .options(selectinload(StudyGroup.members).selectinload(GroupMember.student))
        .options(selectinload(StudyGroup.course))
        .where(StudyGroup.group_id == group_id, StudyGroup.is_active == True)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def is_admin(group: StudyGroup, student: Student) -> bool:
    return any(
        m.student_id == student.student_id and m.role in ("admin", "moderator")
        for m in group.members
    )


def member_count(group: StudyGroup) -> int:
    return len(group.members)


def build_group_out(group: StudyGroup, current_user: Student) -> dict:
    return {
        "group_id": group.group_id,
        "group_name": group.group_name,
        "description": group.description,
        "course_id": group.course_id,
        "creator_id": group.creator_id,
        "privacy_status": group.privacy_status,
        "max_members": group.max_members,
        "member_count": member_count(group),
        "is_member": any(m.student_id == current_user.student_id for m in group.members),
        "created_at": group.created_at,
    }


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/", response_model=list[StudyGroupOut])
async def list_groups(
    search: str = Query(None),
    course_id: UUID = Query(None),
    privacy: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    # Get student's enrolled course IDs
    enrolled = await db.execute(
        select(StudentCourse.course_id)
        .where(StudentCourse.student_id == current_user.student_id)
    )
    enrolled_course_ids = [r[0] for r in enrolled.all()]

    query = (
        select(StudyGroup)
        .options(selectinload(StudyGroup.members))
        .where(
            StudyGroup.is_active == True,
            or_(
                StudyGroup.privacy_status == "public",
                StudyGroup.course_id.in_(enrolled_course_ids),
                StudyGroup.members.any(GroupMember.student_id == current_user.student_id),
            )
        )
    )

    if search:
        query = query.where(
            or_(
                StudyGroup.group_name.ilike(f"%{search}%"),
                StudyGroup.description.ilike(f"%{search}%"),
            )
        )
    if course_id:
        query = query.where(StudyGroup.course_id == course_id)
    if privacy:
        query = query.where(StudyGroup.privacy_status == privacy)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    groups = result.scalars().all()

    return [build_group_out(g, current_user) for g in groups]


@router.post("/", response_model=StudyGroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: StudyGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = StudyGroup(
        group_name=data.group_name,
        description=data.description,
        course_id=data.course_id,
        creator_id=current_user.student_id,
        privacy_status=data.privacy_status.value,
        max_members=data.max_members,
    )
    db.add(group)
    await db.flush()

    # Creator becomes admin automatically
    admin_member = GroupMember(
        group_id=group.group_id,
        student_id=current_user.student_id,
        role="admin",
    )
    db.add(admin_member)
    await db.flush()

    # Reload group to properly reflect structural associations
    group = await get_group_or_404(group.group_id, db)
    return build_group_out(group, current_user)


@router.get("/{group_id}", response_model=StudyGroupDetail)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = await get_group_or_404(group_id, db)

    is_member = any(m.student_id == current_user.student_id for m in group.members)
    if group.privacy_status == "private" and not is_member:
        raise HTTPException(status_code=403, detail="This is a private group")

    members_out = [
        MemberOut(
            student_id=m.student.student_id,
            first_name=m.student.first_name,
            last_name=m.student.last_name,
            email=m.student.email,
            role=m.role,
            joined_at=m.joined_at,
        )
        for m in group.members
    ]

    return {
        **build_group_out(group, current_user),
        "members": members_out,
        "course": group.course,
    }


@router.put("/{group_id}", response_model=StudyGroupOut)
async def update_group(
    group_id: UUID,
    data: StudyGroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = await get_group_or_404(group_id, db)

    if group.creator_id != current_user.student_id and not is_admin(group, current_user):
        raise HTTPException(status_code=403, detail="Only group admins can update the group")

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "privacy_status":
            value = value.value
        setattr(group, field, value)

    await db.flush()
    group = await get_group_or_404(group_id, db)
    return build_group_out(group, current_user)


@router.delete("/{group_id}", response_model=MessageResponse)
async def delete_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = await get_group_or_404(group_id, db)

    if group.creator_id != current_user.student_id:
        raise HTTPException(status_code=403, detail="Only the creator can delete the group")

    group.is_active = False
    return {"message": "Group deleted successfully"}


@router.post("/{group_id}/join", response_model=MessageResponse)
async def join_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = await get_group_or_404(group_id, db)

    if group.privacy_status == "private":
        raise HTTPException(status_code=403, detail="This is a private group. Ask an admin to add you.")

    if any(m.student_id == current_user.student_id for m in group.members):
        raise HTTPException(status_code=400, detail="You are already a member")

    if member_count(group) >= group.max_members:
        raise HTTPException(status_code=400, detail="Group is full")

    db.add(GroupMember(group_id=group_id, student_id=current_user.student_id, role="member"))
    return {"message": "Successfully joined the group"}


@router.post("/{group_id}/leave", response_model=MessageResponse)
async def leave_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = await get_group_or_404(group_id, db)

    if group.creator_id == current_user.student_id:
        raise HTTPException(status_code=400, detail="Creator cannot leave. Transfer ownership first.")

    membership = next(
        (m for m in group.members if m.student_id == current_user.student_id), None
    )
    if not membership:
        raise HTTPException(status_code=400, detail="You are not a member of this group")

    await db.delete(membership)
    return {"message": "Successfully left the group"}


@router.post("/{group_id}/members", response_model=MessageResponse)
async def add_member(
    group_id: UUID,
    data: AddMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = await get_group_or_404(group_id, db)

    if not is_admin(group, current_user) and group.creator_id != current_user.student_id:
        raise HTTPException(status_code=403, detail="Only admins can add members")

    if any(m.student_id == data.student_id for m in group.members):
        raise HTTPException(status_code=400, detail="Student is already a member")

    if member_count(group) >= group.max_members:
        raise HTTPException(status_code=400, detail="Group is full")

    result = await db.execute(select(Student).where(Student.student_id == data.student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    db.add(GroupMember(group_id=group_id, student_id=data.student_id, role="member"))
    return {"message": f"{student.get_full_name()} added to the group"}


@router.delete("/{group_id}/members/{student_id}", response_model=MessageResponse)
async def remove_member(
    group_id: UUID,
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = await get_group_or_404(group_id, db)

    if not is_admin(group, current_user) and group.creator_id != current_user.student_id:
        raise HTTPException(status_code=403, detail="Only admins can remove members")

    if group.creator_id == student_id:
        raise HTTPException(status_code=400, detail="Cannot remove the group creator")

    membership = next((m for m in group.members if m.student_id == student_id), None)
    if not membership:
        raise HTTPException(status_code=404, detail="Student is not a member")

    await db.delete(membership)
    return {"message": "Member removed successfully"}


@router.put("/{group_id}/members/role", response_model=MessageResponse)
async def update_member_role(
    group_id: UUID,
    data: UpdateRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    group = await get_group_or_404(group_id, db)

    if group.creator_id != current_user.student_id and not is_admin(group, current_user):
        raise HTTPException(status_code=403, detail="Only admins can update roles")

    if group.creator_id == data.student_id:
        raise HTTPException(status_code=400, detail="Cannot change the creator's role")

    membership = next((m for m in group.members if m.student_id == data.student_id), None)
    if not membership:
        raise HTTPException(status_code=404, detail="Student is not a member")

    membership.role = data.role.value
    await db.flush()
    return {"message": "Role updated successfully"}