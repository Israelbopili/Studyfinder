import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime,
    Text, ForeignKey, UniqueConstraint, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


# ── Student (User) ──────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    student_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    student_number = Column(String(20), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    program = Column(String(100), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    profile_photo = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    study_preferences = Column(JSONB, default={})

    is_active = Column(Boolean, default=True)
    is_staff = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    email_verification_token = Column(String(64), nullable=True)
    password_reset_token = Column(String(64), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    last_active = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    created_groups = relationship("StudyGroup", back_populates="creator", foreign_keys="StudyGroup.creator_id")
    group_memberships = relationship("GroupMember", back_populates="student")
    enrollments = relationship("CourseEnrollment", back_populates="student")
    uploaded_resources = relationship("Resource", back_populates="uploader")
    sessions_created = relationship("StudySession", back_populates="creator")
    notifications = relationship("Notification", back_populates="student")

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


# ── Course ──────────────────────────────────────────────────────────

class Course(Base):
    __tablename__ = "courses"

    course_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_code = Column(String(20), unique=True, nullable=False, index=True)
    course_name = Column(String(200), nullable=False)
    department = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    enrollments = relationship("CourseEnrollment", back_populates="course")
    groups = relationship("StudyGroup", back_populates="course")


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="CASCADE"))
    enrolled_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course"),)

    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


# ── Study Group ─────────────────────────────────────────────────────

class StudyGroup(Base):
    __tablename__ = "study_groups"

    group_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="SET NULL"), nullable=True)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    privacy_status = Column(
        SAEnum("public", "private", "invite_only", name="privacy_enum"),
        default="public"
    )
    max_members = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    creator = relationship("Student", back_populates="created_groups", foreign_keys=[creator_id])
    course = relationship("Course", back_populates="groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="group")
    sessions = relationship("StudySession", back_populates="group")
    messages = relationship("ChatMessage", back_populates="group")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("study_groups.group_id", ondelete="CASCADE"))
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    role = Column(
        SAEnum("admin", "moderator", "member", name="role_enum"),
        default="member"
    )
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active = Column(DateTime(timezone=True), nullable=True)
    is_notified = Column(Boolean, default=True)

    __table_args__ = (UniqueConstraint("group_id", "student_id", name="uq_group_member"),)

    group = relationship("StudyGroup", back_populates="members")
    student = relationship("Student", back_populates="group_memberships")


# ── Resource ────────────────────────────────────────────────────────

class Resource(Base):
    __tablename__ = "resources"

    resource_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("study_groups.group_id", ondelete="CASCADE"))
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("StudyGroup", back_populates="resources")
    uploader = relationship("Student", back_populates="uploaded_resources")


# ── Study Session ───────────────────────────────────────────────────

class StudySession(Base):
    __tablename__ = "study_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    group_id = Column(UUID(as_uuid=True), ForeignKey("study_groups.group_id", ondelete="CASCADE"))
    creator_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    location = Column(String(300), nullable=True)
    meeting_link = Column(String(500), nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    duration_minutes = Column(Integer, default=60)
    is_cancelled = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("StudyGroup", back_populates="sessions")
    creator = relationship("Student", back_populates="sessions_created")


# ── Chat Message ────────────────────────────────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("study_groups.group_id", ondelete="CASCADE"))
    sender_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_deleted = Column(Boolean, default=False)

    group = relationship("StudyGroup", back_populates="messages")
    sender = relationship("Student")


# ── Notification ────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=True)   # e.g. "group_invite", "session_reminder"
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="notifications")
