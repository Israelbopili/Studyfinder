from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


# ── Enums ───────────────────────────────────────────────────────────

class PrivacyStatus(str, Enum):
    public = "public"
    private = "private"
    invite_only = "invite_only"

class MemberRole(str, Enum):
    admin = "admin"
    moderator = "moderator"
    member = "member"


# ── Auth Schemas ────────────────────────────────────────────────────

class StudentRegister(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    student_number: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=8)
    program: Optional[str] = None
    year_of_study: Optional[int] = Field(None, ge=1, le=10)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class StudentLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class EmailVerifyRequest(BaseModel):
    token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ── Student Schemas ─────────────────────────────────────────────────

class StudentBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    student_number: str
    program: Optional[str] = None
    year_of_study: Optional[int] = None
    bio: Optional[str] = None


class StudentOut(StudentBase):
    student_id: UUID
    is_verified: bool
    email_verified: bool
    profile_photo: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StudentProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    program: Optional[str] = None
    year_of_study: Optional[int] = Field(None, ge=1, le=10)
    bio: Optional[str] = None


# ── Course Schemas ──────────────────────────────────────────────────

class CourseCreate(BaseModel):
    course_code: str = Field(..., max_length=20)
    course_name: str = Field(..., max_length=200)
    department: Optional[str] = None
    description: Optional[str] = None


class CourseOut(BaseModel):
    course_id: UUID
    course_code: str
    course_name: str
    department: Optional[str] = None
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ── Group Schemas ───────────────────────────────────────────────────

class StudyGroupCreate(BaseModel):
    group_name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    course_id: Optional[UUID] = None
    privacy_status: PrivacyStatus = PrivacyStatus.public
    max_members: int = Field(default=50, ge=2, le=200)


class StudyGroupUpdate(BaseModel):
    group_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    privacy_status: Optional[PrivacyStatus] = None
    max_members: Optional[int] = Field(None, ge=2, le=200)


class MemberOut(BaseModel):
    student_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: MemberRole
    joined_at: datetime

    model_config = {"from_attributes": True}


class StudyGroupOut(BaseModel):
    group_id: UUID
    group_name: str
    description: Optional[str] = None
    course_id: Optional[UUID] = None
    creator_id: UUID
    privacy_status: PrivacyStatus
    max_members: int
    member_count: int = 0
    is_member: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class StudyGroupDetail(StudyGroupOut):
    members: List[MemberOut] = []
    course: Optional[CourseOut] = None


class AddMemberRequest(BaseModel):
    student_id: UUID

class UpdateRoleRequest(BaseModel):
    student_id: UUID
    role: MemberRole


# ── Resource Schemas ────────────────────────────────────────────────

class ResourceOut(BaseModel):
    resource_id: UUID
    title: str
    description: Optional[str] = None
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    group_id: UUID
    uploader_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Session Schemas ─────────────────────────────────────────────────

class StudySessionCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    group_id: UUID
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int = Field(default=60, ge=15, le=480)


class StudySessionOut(BaseModel):
    session_id: UUID
    title: str
    description: Optional[str] = None
    group_id: UUID
    creator_id: UUID
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    scheduled_at: datetime
    duration_minutes: int
    is_cancelled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Chat Schemas ────────────────────────────────────────────────────

class ChatMessageOut(BaseModel):
    message_id: UUID
    group_id: UUID
    sender_id: UUID
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Notification Schemas ────────────────────────────────────────────

class NotificationOut(BaseModel):
    notification_id: UUID
    title: str
    message: str
    type: Optional[str] = None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generic ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list
