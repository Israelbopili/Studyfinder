from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class PrivacyStatus(str, Enum):
    public = "public"
    private = "private"
    invite_only = "invite_only"

class StudentRegister(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    student_number: str = Field(..., min_length=3, max_length=20)
    password: str = Field(..., min_length=4)
    program: Optional[str] = None
    year_of_study: Optional[int] = Field(None, ge=1, le=10)

class StudentLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class StudentOut(BaseModel):
    student_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    student_number: str
    program: Optional[str] = None
    year_of_study: Optional[int] = None
    created_at: datetime
    is_verified: bool = False
    email_verified: bool = False
    
    class Config:
        from_attributes = True

class StudyGroupCreate(BaseModel):
    group_name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    privacy_status: PrivacyStatus = PrivacyStatus.public
    max_members: int = Field(default=50, ge=2, le=200)

class StudyGroupOut(BaseModel):
    group_id: UUID
    group_name: str
    description: Optional[str] = None
    creator_id: UUID
    privacy_status: str
    max_members: int
    member_count: int = 0
    is_member: bool = False
    created_at: datetime
    is_priority: bool = False
    unread_count: int = 0
    is_pending: bool = False
    is_admin: bool = False
    
    class Config:
        from_attributes = True

class MemberOut(BaseModel):
    student_id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: str
    joined_at: datetime
    
    class Config:
        from_attributes = True

class StudyGroupDetail(StudyGroupOut):
    members: List[MemberOut] = []

class MessageResponse(BaseModel):
    message: str

class EmailVerifyRequest(BaseModel):
    token: str

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=4)

class MessageCreate(BaseModel):
    content: str
    group_id: UUID
    message_type: Optional[str] = "text"

class MessageOut(BaseModel):
    message_id: UUID
    group_id: UUID
    sender_id: UUID
    sender_name: Optional[str] = None
    content: str
    message_type: str = "text"
    is_edited: bool = False
    sent_at: datetime
    
    class Config:
        from_attributes = True

# ─── NEW SCHEMAS ─────────────────────────────────────────────────────

class StudentProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    program: Optional[str] = None
    year_of_study: Optional[int] = Field(None, ge=1, le=10)
    bio: Optional[str] = None
    profile_photo_url: Optional[str] = None

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
    
    class Config:
        from_attributes = True

class StudySessionCreate(BaseModel):
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    group_id: UUID
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    start_time: datetime
    end_time: datetime

class StudySessionOut(BaseModel):
    session_id: UUID
    title: str
    description: Optional[str] = None
    group_id: UUID
    created_by: UUID
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ResourceOut(BaseModel):
    resource_id: UUID
    title: str
    description: Optional[str] = None
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    group_id: UUID
    uploaded_by: UUID
    downloads_count: int = 0
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationOut(BaseModel):
    notification_id: UUID
    title: str
    message: str
    type: Optional[str] = None
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
        # ─── OTP Schemas ─────────────────────────────────────────────────────

class OTPSendRequest(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str

class OTPVerifyRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)

class OTPResendRequest(BaseModel):
    email: EmailStr