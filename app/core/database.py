from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Create async engine connected to Supabase PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,       # logs all SQL queries when DEBUG=True
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,        # checks connection is alive before using it
    pool_recycle=3600,         # recycle connections every hour
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Base class all models inherit from
class Base(DeclarativeBase):
    pass


# Dependency — use this in every route that needs the DB
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
