import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


# ─── Student ─────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"
    
    student_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    student_number = Column(String(20), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    program = Column(String(100), nullable=True)
    year_of_study = Column(Integer, nullable=True)
    profile_photo_url = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    study_preferences = Column(JSONB, default={})
    
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    verification_token = Column(String(255), nullable=True)
    reset_password_token = Column(String(255), nullable=True)
    reset_password_expires = Column(DateTime, nullable=True)
    last_active = Column(DateTime, nullable=True)
    
    # OTP FIELDS
    otp_code = Column(String(6), nullable=True)
    otp_expires = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, default=0)
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    created_groups = relationship("StudyGroup", back_populates="creator", foreign_keys="StudyGroup.creator_id")
    group_memberships = relationship("GroupMember", back_populates="student")
    messages = relationship("Message", back_populates="sender")
    enrollments = relationship("StudentCourse", back_populates="student")
    sessions_created = relationship("Session", back_populates="creator")
    uploaded_resources = relationship("Resource", back_populates="uploader")
    notifications = relationship("Notification", back_populates="student")
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"


# ─── Course ──────────────────────────────────────────────────────────

class Course(Base):
    __tablename__ = "courses"
    
    course_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_code = Column(String(20), unique=True, nullable=False, index=True)
    course_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    credits = Column(Integer, default=3)
    department = Column(String(100), nullable=True)
    semester = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    enrollments = relationship("StudentCourse", back_populates="course")
    groups = relationship("StudyGroup", back_populates="course")


class StudentCourse(Base):
    __tablename__ = "student_courses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="CASCADE"))
    grade = Column(String(5), nullable=True)
    enrolled_at = Column(DateTime, server_default=func.now())
    
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course"),)
    
    student = relationship("Student", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


# ─── Study Group ─────────────────────────────────────────────────────

class StudyGroup(Base):
    __tablename__ = "study_groups"
    
    group_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.course_id", ondelete="SET NULL"), nullable=True)
    creator_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    privacy_status = Column(String(20), default="public")
    max_members = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    creator = relationship("Student", back_populates="created_groups", foreign_keys=[creator_id])
    course = relationship("Course", back_populates="groups")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    resources = relationship("Resource", back_populates="group")
    sessions = relationship("Session", back_populates="group")
    messages = relationship("Message", back_populates="group")


class GroupMember(Base):
    __tablename__ = "group_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("study_groups.group_id", ondelete="CASCADE"))
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    role = Column(String(20), default="member")
    joined_at = Column(DateTime, server_default=func.now())
    last_active = Column(DateTime, nullable=True)
    is_notified = Column(Boolean, default=True)
    is_priority = Column(Boolean, default=False)
    unread_count = Column(Integer, default=0)
    
    __table_args__ = (UniqueConstraint("group_id", "student_id", name="uq_group_member"),)
    
    group = relationship("StudyGroup", back_populates="members")
    student = relationship("Student", back_populates="group_memberships")


# ─── Resource ────────────────────────────────────────────────────────

class Resource(Base):
    __tablename__ = "resources"
    
    resource_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    group_id = Column(UUID(as_uuid=True), ForeignKey("study_groups.group_id", ondelete="CASCADE"))
    downloads_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    group = relationship("StudyGroup", back_populates="resources")
    uploader = relationship("Student", back_populates="uploaded_resources", foreign_keys=[uploaded_by])


# ─── Session ─────────────────────────────────────────────────────────

class Session(Base):
    __tablename__ = "sessions"
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("study_groups.group_id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    location = Column(String(200), nullable=True)
    meeting_link = Column(String(255), nullable=True)
    status = Column(String(20), default="scheduled")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    
    group = relationship("StudyGroup", back_populates="sessions")
    creator = relationship("Student", back_populates="sessions_created", foreign_keys=[created_by])


# ─── Message ─────────────────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"
    
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("study_groups.group_id", ondelete="CASCADE"))
    sender_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")
    reply_to_id = Column(UUID(as_uuid=True), ForeignKey("messages.message_id", ondelete="SET NULL"), nullable=True)
    is_edited = Column(Boolean, default=False)
    sent_at = Column(DateTime, server_default=func.now())
    edited_at = Column(DateTime, nullable=True)
    
    group = relationship("StudyGroup", back_populates="messages")
    sender = relationship("Student", back_populates="messages")


# ─── Notification ────────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    
    notification_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.student_id", ondelete="CASCADE"))
    type = Column(String(50), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    meta_data = Column(JSONB, default={})
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    student = relationship("Student", back_populates="notifications")