from typing import AsyncGenerator

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tabtrack.config import DATABASE_URL
from tabtrack.schemas import Base

async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def init_db():
    global async_session_maker
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        # Create TimescaleDB extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
        # Convert time_series table to hypertable if not already
        await conn.execute(
            text("""
            SELECT create_hypertable('time_series', 'timestamp',
                if_not_exists => TRUE,
                migrate_data => TRUE
            )
        """)
        )

    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if not async_session_maker:
        raise HTTPException(status_code=500, detail="Database not initialized")
    async with async_session_maker() as session:
        yield session
