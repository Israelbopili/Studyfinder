import secrets
import uuid
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func

from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user
)
from app.models.student import Student
from app.schemas.schemas import (
    StudentRegister, StudentLogin, TokenResponse,
    RefreshTokenRequest, StudentOut, MessageResponse,
    OTPVerifyRequest, OTPResendRequest, OTPSendRequest,
    PasswordResetRequest, PasswordResetConfirm
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return f"{random.randint(100000, 999999)}"


# ─── EMAIL SENDING ─────────────────────────────────────────────────────

async def send_otp_email(email: str, first_name: str, otp_code: str):
    """Send OTP verification email via Gmail SMTP"""
    
    subject = "Your Verification Code - Studyfinder"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Verify Your Email</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
        <div style="background: linear-gradient(135deg, #1A3A6B, #2A4A7B); color: white; padding: 30px 20px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">📚 Studyfinder</h1>
            <p style="margin: 5px 0 0; opacity: 0.8;">Mulungushi University</p>
        </div>
        <div style="background: white; padding: 30px 20px; border-radius: 0 0 12px 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #1A3A6B;">Hi {first_name}! 👋</h2>
            <p>Thanks for joining <strong>Studyfinder</strong>! Use the code below to verify your email address.</p>
            
            <div style="text-align: center; margin: 30px 0; background: #f0f4f8; padding: 20px; border-radius: 8px;">
                <p style="font-size: 14px; color: #666; margin-bottom: 8px;">Your verification code is:</p>
                <div style="font-size: 48px; font-weight: bold; color: #1A3A6B; letter-spacing: 12px; font-family: monospace;">
                    {otp_code}
                </div>
            </div>
            
            <p style="font-size: 14px; color: #888;">⏰ This code will expire in <strong>10 minutes</strong>.</p>
            <p style="font-size: 14px; color: #888;">You have <strong>3 attempts</strong> to enter the correct code.</p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
            
            <p style="font-size: 14px; color: #888; margin: 0;">
                Best regards,<br>
                <strong style="color: #1A3A6B;">Studyfinder Team</strong>
            </p>
            <p style="font-size: 12px; color: #aaa; margin-top: 10px;">
                If you didn't create an account, please ignore this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = settings.MAIL_USERNAME
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
            print(f"✅ OTP email sent to {email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send OTP email: {e}")
        # Fallback: print OTP to console
        print(f"\n🔑 OTP for {first_name}: {otp_code}\n")
        return False


# ─── ROUTES ───────────────────────────────────────────────────────────

@router.post("/send-otp", response_model=MessageResponse)
async def send_otp(
    data: OTPSendRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Step 1: Send OTP without creating account"""
    
    # Check if email already exists
    result = await db.execute(select(Student).where(Student.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate OTP
    otp = generate_otp()
    otp_expires = datetime.utcnow() + timedelta(minutes=10)
    
    # Store OTP temporarily (using a temp table or cache)
    # For now, we'll store it in the student table with a flag
    # Since we don't have a temp table, we'll use a simple approach
    # Create a temporary entry or use Redis
    # For simplicity, we'll store in the student table with is_active=False
    
    # Check if a temp record exists
    temp_student = await db.execute(
        select(Student).where(
            Student.email == data.email,
            Student.is_active == False
        )
    )
    temp_student = temp_student.scalar_one_or_none()
    
    if temp_student:
        # Update existing temp record
        temp_student.otp_code = otp
        temp_student.otp_expires = otp_expires
        temp_student.otp_attempts = 0
        temp_student.first_name = data.first_name
        temp_student.last_name = data.last_name
    else:
        # Create temp student (inactive)
        temp_student = Student(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            student_number="TEMP_" + generate_token(8),
            password_hash="",
            is_active=False,
            otp_code=otp,
            otp_expires=otp_expires,
            otp_attempts=0
        )
        db.add(temp_student)
    
    await db.commit()
    
    # Send OTP email
    background_tasks.add_task(
        send_otp_email,
        data.email,
        data.first_name,
        otp
    )
    
    return {"message": "OTP sent to your email. Please verify to complete registration."}


@router.post("/verify-otp", response_model=MessageResponse)
async def verify_otp(
    data: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Step 2: Verify OTP code"""
    
    # Find student by email (including inactive/temp)
    result = await db.execute(
        select(Student).where(Student.email == data.email)
    )
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found. Please register first.")
    
    if student.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    # Check OTP expiry
    if student.otp_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")
    
    # Check attempts
    if student.otp_attempts >= 3:
        raise HTTPException(status_code=400, detail="Too many failed attempts. Please request a new OTP.")
    
    # Verify OTP
    if student.otp_code != data.otp_code:
        student.otp_attempts += 1
        await db.commit()
        remaining = 3 - student.otp_attempts
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid OTP. {remaining} attempts remaining."
        )
    
    # ─── OTP VERIFIED ──────────────────────────────────────────────────
    # Mark as verified (account will be created in /register)
    student.otp_code = None
    student.otp_expires = None
    student.otp_attempts = 0
    student.is_verified = True
    student.email_verified = True
    await db.commit()
    
    return {"message": "OTP verified successfully! Please complete your registration."}


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
async def register(
    data: StudentRegister,
    db: AsyncSession = Depends(get_db)
):
    """Step 3: Create account (only after OTP verified)"""
    
    # Check if email exists
    result = await db.execute(select(Student).where(Student.email == data.email))
    existing = result.scalar_one_or_none()
    
    if existing and existing.is_active:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if not existing or not existing.email_verified:
        raise HTTPException(
            status_code=400, 
            detail="Please verify your email first using the OTP code."
        )
    
    # Update the existing inactive record to active
    existing.first_name = data.first_name
    existing.last_name = data.last_name
    existing.student_number = data.student_number
    existing.password_hash = hash_password(data.password)
    existing.program = data.program
    existing.year_of_study = data.year_of_study
    existing.is_active = True
    existing.email_verified = True
    existing.is_verified = True
    existing.otp_code = None
    existing.otp_expires = None
    existing.otp_attempts = 0
    
    await db.commit()
    await db.refresh(existing)
    
    return {"message": "Registration successful! You can now log in."}


@router.post("/login", response_model=TokenResponse)
async def login(data: StudentLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.email == data.email))
    student = result.scalar_one_or_none()
    
    if not student or not verify_password(data.password, student.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not student.is_active:
        raise HTTPException(status_code=400, detail="Account disabled")
    
    if not student.email_verified:
        raise HTTPException(
            status_code=403, 
            detail="Please verify your email first. Check your email for the OTP code."
        )
    
    student.last_active = func.now()
    await db.commit()
    
    access_token = create_access_token(data={"sub": str(student.student_id)})
    refresh_token = create_refresh_token(data={"sub": str(student.student_id)})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(
    data: OTPResendRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Resend OTP verification code"""
    
    result = await db.execute(select(Student).where(Student.email == data.email))
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    if student.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    # Generate new OTP
    otp = generate_otp()
    student.otp_code = otp
    student.otp_expires = datetime.utcnow() + timedelta(minutes=10)
    student.otp_attempts = 0
    await db.commit()
    
    # Send new OTP
    background_tasks.add_task(
        send_otp_email,
        student.email,
        student.first_name,
        otp
    )
    
    return {"message": "New OTP sent to your email."}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(data.refresh_token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID")
    
    result = await db.execute(select(Student).where(Student.student_id == user_uuid))
    student = result.scalar_one_or_none()
    
    if not student or not student.is_active:
        raise HTTPException(status_code=401, detail="User not found")
    
    new_access = create_access_token(data={"sub": str(student.student_id)})
    new_refresh = create_refresh_token(data={"sub": str(student.student_id)})
    
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


@router.get("/me", response_model=StudentOut)
async def get_me(current_user: Student = Depends(get_current_user)):
    return current_user


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: PasswordResetRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Student).where(Student.email == data.email))
    student = result.scalar_one_or_none()
    
    if student:
        token = generate_token()
        student.reset_password_token = token
        student.reset_password_expires = datetime.utcnow() + timedelta(hours=24)
        await db.commit()
        
        background_tasks.add_task(
            send_password_reset_email,
            student.email,
            student.first_name,
            token
        )
    
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.reset_password_token == data.token))
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    if student.reset_password_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    student.password_hash = hash_password(data.new_password)
    student.reset_password_token = None
    student.reset_password_expires = None
    await db.commit()
    
    return {"message": "Password reset successful! You can now log in."}


# ─── PASSWORD RESET EMAIL ────────────────────────────────────────────

async def send_password_reset_email(email: str, first_name: str, token: str):
    """Send password reset email"""
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    subject = "Reset Your Password - Studyfinder"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reset Your Password</title>
    </head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
        <div style="background: linear-gradient(135deg, #D4A843, #E4B853); color: white; padding: 30px 20px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">🔑 Password Reset</h1>
            <p style="margin: 5px 0 0; opacity: 0.8;">Studyfinder</p>
        </div>
        <div style="background: white; padding: 30px 20px; border-radius: 0 0 12px 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color: #D4A843;">Hi {first_name},</h2>
            <p>We received a request to reset your password for <strong>Studyfinder</strong>.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}" 
                   style="background: linear-gradient(135deg, #D4A843, #E4B853); 
                          color: white; padding: 14px 40px; text-decoration: none; 
                          border-radius: 8px; font-weight: bold; display: inline-block;
                          box-shadow: 0 2px 8px rgba(212,168,67,0.3);">
                    🔐 Reset Password
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">Or copy this link into your browser:</p>
            <p style="background: #f5f5f5; padding: 12px; border-radius: 6px; word-break: break-all; font-size: 14px; color: #D4A843;">
                <a href="{reset_link}" style="color: #D4A843;">{reset_link}</a>
            </p>
            
            <p style="font-size: 14px; color: #888;">⏰ This link will expire in <strong>24 hours</strong>.</p>
            
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0; border-radius: 4px;">
                <p style="margin: 0; font-size: 14px; color: #856404;">
                    ⚠️ If you didn't request this, please ignore this email and your password will remain unchanged.
                </p>
            </div>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 25px 0;">
            
            <p style="font-size: 14px; color: #888; margin: 0;">
                Best regards,<br>
                <strong style="color: #D4A843;">Studyfinder Team</strong>
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = settings.MAIL_USERNAME
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
            print(f"✅ Password reset email sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        print(f"\n🔑 Reset link for {first_name}: {reset_link}\n")