from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.student import Student, StudyGroup, GroupMember
from app.schemas.schemas import (
    StudyGroupCreate, StudyGroupOut, StudyGroupDetail,
    MemberOut, MessageResponse, PrivacyStatus
)

router = APIRouter(prefix="/groups", tags=["Study Groups"])

# ── Helper Functions ──────────────────────────────────────────────────

async def get_group_or_404(group_id: UUID, db: AsyncSession) -> StudyGroup:
    result = await db.execute(
        select(StudyGroup)
        .options(selectinload(StudyGroup.members).selectinload(GroupMember.student))
        .where(StudyGroup.group_id == group_id, StudyGroup.is_active == True)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


# ─── Endpoints ────────────────────────────────────────────────────────

@router.post("/", response_model=StudyGroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    data: StudyGroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    group = StudyGroup(
        group_name=data.group_name,
        description=data.description,
        creator_id=current_user.student_id,
        privacy_status=data.privacy_status.value,
        max_members=data.max_members,
    )
    db.add(group)
    await db.flush()
    
    # Creator becomes admin
    member = GroupMember(
        group_id=group.group_id,
        student_id=current_user.student_id,
        role="admin"
    )
    db.add(member)
    await db.commit()
    await db.refresh(group)
    
    return StudyGroupOut(
        group_id=group.group_id,
        group_name=group.group_name,
        description=group.description,
        creator_id=group.creator_id,
        privacy_status=group.privacy_status,
        max_members=group.max_members,
        member_count=1,
        is_member=True,
        created_at=group.created_at,
        is_priority=False,
        unread_count=0,
        is_pending=False
    )


@router.get("/", response_model=list[StudyGroupOut])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    result = await db.execute(
        select(StudyGroup)
        .options(selectinload(StudyGroup.members))
        .where(StudyGroup.is_active == True)
    )
    groups = result.scalars().all()
    
    memberships_result = await db.execute(
        select(GroupMember).where(GroupMember.student_id == current_user.student_id)
    )
    memberships = {m.group_id: m for m in memberships_result.scalars().all()}
    
    output = []
    for group in groups:
        membership = memberships.get(group.group_id)
        
        is_member = False
        is_pending = False
        is_priority = False
        unread_count = 0
        
        if membership:
            is_member = membership.role in ["admin", "moderator", "member"]
            is_pending = membership.role == "pending"
            is_priority = membership.is_priority or False
            unread_count = membership.unread_count or 0
        
        # Show private groups to members only, or if user has pending request
        if group.privacy_status == "private" and not is_member and not is_pending:
            continue
        
        # Show invite_only groups to members only
        if group.privacy_status == "invite_only" and not is_member:
            continue
        
        output.append(StudyGroupOut(
            group_id=group.group_id,
            group_name=group.group_name,
            description=group.description,
            creator_id=group.creator_id,
            privacy_status=group.privacy_status,
            max_members=group.max_members,
            member_count=len(group.members),
            is_member=is_member,
            created_at=group.created_at,
            is_priority=is_priority,
            unread_count=unread_count,
            is_pending=is_pending
        ))
    
    return output


@router.get("/{group_id}", response_model=StudyGroupDetail)
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    group = await get_group_or_404(group_id, db)
    
    membership = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id
        )
    )
    membership = membership.scalar_one_or_none()
    
    is_member = False
    is_pending = False
    is_admin_user = False
    is_priority = False
    unread_count = 0
    
    if membership:
        is_member = membership.role in ["admin", "moderator", "member"]
        is_pending = membership.role == "pending"
        is_admin_user = membership.role in ["admin", "moderator"]
        is_priority = membership.is_priority or False
        unread_count = membership.unread_count or 0
    
    # Check access
    if group.privacy_status == "private":
        if not is_member and not is_pending:
            raise HTTPException(status_code=403, detail="This is a private group. Request to join from group admin.")
    
    if group.privacy_status == "invite_only" and not is_member:
        raise HTTPException(status_code=403, detail="This is an invite-only group.")
    
    members_out = [
        MemberOut(
            student_id=m.student.student_id,
            first_name=m.student.first_name,
            last_name=m.student.last_name,
            email=m.student.email,
            role=m.role,
            joined_at=m.joined_at
        )
        for m in group.members
    ]
    
    return StudyGroupDetail(
        group_id=group.group_id,
        group_name=group.group_name,
        description=group.description,
        creator_id=group.creator_id,
        privacy_status=group.privacy_status,
        max_members=group.max_members,
        member_count=len(group.members),
        is_member=is_member,
        created_at=group.created_at,
        is_priority=is_priority,
        unread_count=unread_count,
        is_pending=is_pending,
        is_admin=is_admin_user,
        members=members_out
    )


@router.post("/{group_id}/join")
async def request_to_join(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    group = await get_group_or_404(group_id, db)
    
    # Check if already a member
    existing = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id
        )
    )
    existing_member = existing.scalar_one_or_none()
    
    if existing_member:
        if existing_member.role in ["admin", "moderator", "member"]:
            raise HTTPException(status_code=400, detail="You are already a member of this group")
        if existing_member.role == "pending":
            raise HTTPException(status_code=400, detail="Your request is already pending approval")
    
    if group.privacy_status == "public":
        # Public groups: join immediately
        member = GroupMember(
            group_id=group_id,
            student_id=current_user.student_id,
            role="member"
        )
        db.add(member)
        await db.commit()
        return {"message": "Successfully joined the group", "status": "joined"}
    
    elif group.privacy_status == "private":
        # Private groups: request approval
        member = GroupMember(
            group_id=group_id,
            student_id=current_user.student_id,
            role="pending"
        )
        db.add(member)
        await db.commit()
        return {"message": "Join request sent to group admin", "status": "pending"}
    
    elif group.privacy_status == "invite_only":
        raise HTTPException(status_code=403, detail="This group is invite-only. Ask an admin to invite you.")
    
    return {"message": "Action completed"}


@router.post("/{group_id}/approve/{student_id}")
async def approve_member(
    group_id: UUID,
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    group = await get_group_or_404(group_id, db)
    
    # Check if current user is admin
    admin_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id,
            GroupMember.role.in_(["admin", "moderator"])
        )
    )
    if not admin_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only admins can approve members")
    
    # Find the pending member
    pending_member = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == student_id,
            GroupMember.role == "pending"
        )
    )
    pending_member = pending_member.scalar_one_or_none()
    
    if not pending_member:
        raise HTTPException(status_code=404, detail="No pending request found for this user")
    
    # Approve: change role to member
    pending_member.role = "member"
    await db.commit()
    
    return {"message": "Member approved successfully"}


@router.post("/{group_id}/reject/{student_id}")
async def reject_member(
    group_id: UUID,
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    group = await get_group_or_404(group_id, db)
    
    # Check if current user is admin
    admin_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id,
            GroupMember.role.in_(["admin", "moderator"])
        )
    )
    if not admin_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only admins can reject requests")
    
    # Find the pending member
    pending_member = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == student_id,
            GroupMember.role == "pending"
        )
    )
    pending_member = pending_member.scalar_one_or_none()
    
    if not pending_member:
        raise HTTPException(status_code=404, detail="No pending request found for this user")
    
    # Reject: delete the request
    await db.delete(pending_member)
    await db.commit()
    
    return {"message": "Join request rejected"}


@router.post("/{group_id}/invite/{student_id}")
async def invite_member(
    group_id: UUID,
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    group = await get_group_or_404(group_id, db)
    
    # Check if current user is admin
    admin_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id,
            GroupMember.role.in_(["admin", "moderator"])
        )
    )
    if not admin_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only admins can invite members")
    
    # Check if user exists
    student = await db.execute(select(Student).where(Student.student_id == student_id))
    student = student.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    # Check if already a member or pending
    existing = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == student_id
        )
    )
    existing_member = existing.scalar_one_or_none()
    
    if existing_member:
        if existing_member.role in ["admin", "moderator", "member"]:
            raise HTTPException(status_code=400, detail="User is already a member")
        if existing_member.role == "pending":
            raise HTTPException(status_code=400, detail="User already has a pending request")
    
    # Add as member directly (invite bypasses approval)
    member = GroupMember(
        group_id=group_id,
        student_id=student_id,
        role="member"
    )
    db.add(member)
    await db.commit()
    
    return {"message": f"User {student.get_full_name()} has been invited to the group"}


@router.get("/{group_id}/pending-requests")
async def get_pending_requests(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    group = await get_group_or_404(group_id, db)
    
    # Check if current user is admin
    admin_check = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id,
            GroupMember.role.in_(["admin", "moderator"])
        )
    )
    if not admin_check.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only admins can view pending requests")
    
    pending = await db.execute(
        select(GroupMember)
        .options(selectinload(GroupMember.student))
        .where(
            GroupMember.group_id == group_id,
            GroupMember.role == "pending"
        )
    )
    pending_members = pending.scalars().all()
    
    return [
        {
            "student_id": str(m.student.student_id),
            "first_name": m.student.first_name,
            "last_name": m.student.last_name,
            "email": m.student.email,
            "requested_at": m.joined_at.isoformat()
        }
        for m in pending_members
    ]


@router.post("/{group_id}/leave", response_model=MessageResponse)
async def leave_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    group = await get_group_or_404(group_id, db)
    
    if group.creator_id == current_user.student_id:
        raise HTTPException(status_code=400, detail="Creator cannot leave the group")
    
    member = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id
        )
    )
    member = member.scalar_one_or_none()
    
    if not member:
        raise HTTPException(status_code=400, detail="Not a member")
    
    await db.delete(member)
    await db.commit()
    
    return {"message": "Left group successfully"}


@router.put("/{group_id}/priority")
async def toggle_priority(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_current_user)
):
    member_result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == current_user.student_id
        )
    )
    member = member_result.scalar_one_or_none()
    if not member or member.role not in ["admin", "moderator", "member"]:
        raise HTTPException(status_code=404, detail="Not a member of this group")
    
    member.is_priority = not member.is_priority
    await db.commit()
    
    return {"is_priority": member.is_priority}