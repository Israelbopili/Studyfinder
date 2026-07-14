from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from app.core.config import settings
from app.core.database import engine, Base
from app.routers import auth, students, groups, courses, sessions, resources, notifications, matching, chat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Studyfinder API...")
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Connected to Supabase PostgreSQL")
            break
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(3)
            else:
                raise
    
    yield
    
    await engine.dispose()
    logger.info("🔌 Database disconnected")

app = FastAPI(
    title=settings.APP_NAME,
    description="Studyfinder API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.API_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(students.router, prefix=prefix)
app.include_router(groups.router, prefix=prefix)
app.include_router(courses.router, prefix=prefix)
app.include_router(sessions.router, prefix=prefix)
app.include_router(resources.router, prefix=prefix)
app.include_router(notifications.router, prefix=prefix)
app.include_router(matching.router, prefix=prefix)
app.include_router(chat.router, prefix=prefix)

@app.get("/")
async def root():
    return {"message": "Welcome to Studyfinder API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}