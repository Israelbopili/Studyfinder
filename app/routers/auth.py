import secrets
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user
)
from app.models.student import Student
from app.schemas.schemas import (
    StudentRegister, StudentLogin, TokenResponse,
    RefreshTokenRequest, EmailVerifyRequest,
    PasswordResetRequest, PasswordResetConfirm,
    StudentOut, MessageResponse
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Helpers ─────────────────────────────────────────────────────────

def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


async def send_verification_email(email: str, first_name: str, token: str):
    """
    Plug in FastAPI-Mail or any email service here.
    For now this is a placeholder — the token is printed for local dev.
    """
    from app.core.config import settings
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    print(f"\n[EMAIL] Verification link for {first_name}: {link}\n")


async def send_password_reset_email(email: str, first_name: str, token: str):
    from app.core.config import settings
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    print(f"\n[EMAIL] Password reset link for {first_name}: {link}\n")


# ── Routes ──────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
async def register(data: StudentRegister, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(Student).where(Student.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    result_num = await db.execute(select(Student).where(Student.student_number == data.student_number))
    if result_num.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Student number already registered")

    v_token = generate_token()

    # Create new Student instance mapping to correct columns
    new_student = Student(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        student_number=data.student_number,
        password_hash=hash_password(data.password),
        program=data.program,
        year_of_study=data.year_of_study,
        verification_token=v_token
    )

    db.add(new_student)
    await db.flush()  

    background_tasks.add_task(
        send_verification_email, new_student.email, new_student.first_name, v_token
    )

    return {"message": "Registration successful! Please check your terminal console for the verification email link token."}


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(data: EmailVerifyRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.verification_token == data.token))
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    student.email_verified = True
    student.is_verified = True
    student.verification_token = None  # Consume the token

    return {"message": "Email verified successfully! You can now log in."}


@router.post("/login", response_model=TokenResponse)
async def login(data: StudentLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.email == data.email))
    student = result.scalar_one_or_none()

    if not student or not verify_password(data.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not student.is_active:
        raise HTTPException(status_code=400, detail="Account disabled")

    # Generate access & refresh JSON Web Tokens
    access_token = create_access_token(data={"sub": str(student.student_id)})
    refresh_token = create_refresh_token(data={"sub": str(student.student_id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(Student).where(Student.student_id == uuid.UUID(user_id)))
    student = result.scalar_one_or_none()

    if not student or not student.is_active:
        raise HTTPException(status_code=401, detail="User not found or suspended")

    new_access = create_access_token(data={"sub": str(student.student_id)})
    new_refresh = create_refresh_token(data={"sub": str(student.student_id)})

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: PasswordResetRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.email == data.email))
    student = result.scalar_one_or_none()

    # Always return success to avoid revealing if email exists
    if student:
        token = generate_token()
        student.reset_password_token = token
        student.reset_password_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        background_tasks.add_task(
            send_password_reset_email, student.email, student.first_name, token
        )

    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Student).where(Student.reset_password_token == data.token)
    )
    student = result.scalar_one_or_none()

    if not student:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if student.reset_password_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")

    student.password_hash = hash_password(data.new_password)
    student.reset_password_token = None
    student.reset_password_expires = None

    return {"message": "Password reset successful. You can now log in."}


@router.get("/me", response_model=StudentOut)
async def get_me(current_user: Student = Depends(get_current_user)):
    return current_user