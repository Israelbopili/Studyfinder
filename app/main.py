from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine, Base

# Import all models so they register with Base metadata
from app.models.student import (
    Student, Course, StudentCourse, StudyGroup,
    GroupMember, Resource, Session, Message, Notification
)

# Import routers
from app.routers.auth import router as auth_router
from app.routers.students import router as students_router
from app.routers.groups import router as groups_router
from app.routers.other import (
    courses_router, sessions_router,
    resources_router, notifications_router
)
from app.routers.chat import router as chat_router
from app.routers.matching import router as matching_router


# ── Startup / Shutdown ───────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup: create all tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Connected to Supabase PostgreSQL")
    yield
    # On shutdown: dispose connection pool
    await engine.dispose()
    print("🔌 Database connection closed")


# ── App ──────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="REST API for Study Group Finder — built with FastAPI + Supabase PostgreSQL",
    version="1.0.0",
    docs_url="/docs",       # Swagger UI at /docs
    redoc_url="/redoc",     # ReDoc at /redoc
    lifespan=lifespan,
)


# ── CORS ─────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Register Routers ─────────────────────────────────────────────────

prefix = settings.API_PREFIX

app.include_router(auth_router,          prefix=prefix)
app.include_router(students_router,      prefix=prefix)
app.include_router(groups_router,        prefix=prefix)
app.include_router(courses_router,       prefix=prefix)
app.include_router(sessions_router,      prefix=prefix)
app.include_router(resources_router,     prefix=prefix)
app.include_router(notifications_router, prefix=prefix)
app.include_router(chat_router,          prefix=prefix)
app.include_router(matching_router,      prefix=prefix)


# ── Health Check ─────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }
