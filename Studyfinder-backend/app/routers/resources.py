from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status  # ← ADD status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os

from app.core.database import get_db
from app.core.security import get_verified_user
from app.models.student import Student, StudyGroup, GroupMember, Resource
from app.schemas.schemas import ResourceOut, MessageResponse

router = APIRouter(prefix="/resources", tags=["Resources"])

async def check_group_member(group_id: UUID, student_id: UUID, db: AsyncSession):
    result = await db.execute(
        select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.student_id == student_id
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="You must be a group member to do this")

@router.get("/group/{group_id}", response_model=list[ResourceOut])
async def list_group_resources(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    await check_group_member(group_id, current_user.student_id, db)

    result = await db.execute(
        select(Resource)
        .where(Resource.group_id == group_id)
        .order_by(Resource.created_at.desc())
    )
    return result.scalars().all()

@router.post("/group/{group_id}", response_model=ResourceOut, status_code=status.HTTP_201_CREATED)
async def upload_resource(
    group_id: UUID,
    title: str = Form(...),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    await check_group_member(group_id, current_user.student_id, db)

    # Create upload directory
    upload_dir = f"uploads/resources/{group_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = f"{upload_dir}/{file.filename}"
    
    # Save file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        file_size = len(content)

    resource = Resource(
        title=title,
        description=description,
        file_name=file.filename,
        file_path=file_path,
        file_type=file.content_type,
        file_size=file_size,
        group_id=group_id,
        uploaded_by=current_user.student_id,
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource

@router.delete("/{resource_id}", response_model=MessageResponse)
async def delete_resource(
    resource_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Student = Depends(get_verified_user),
):
    result = await db.execute(select(Resource).where(Resource.resource_id == resource_id))
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if resource.uploaded_by != current_user.student_id:
        raise HTTPException(status_code=403, detail="You can only delete your own resources")

    # Delete file
    if os.path.exists(resource.file_path):
        os.remove(resource.file_path)

    await db.delete(resource)
    await db.commit()
    return {"message": "Resource deleted"}