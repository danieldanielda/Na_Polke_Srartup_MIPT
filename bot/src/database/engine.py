# database/database.py
import os
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from src.database.models import Base
from config import BotSettings

settings = BotSettings()

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:"
    f"{settings.postgres_password}@{settings.postgres_host}:"
    f"{settings.postgres_port}/{settings.postgres_db}"
)
engine = create_async_engine(DATABASE_URL, echo=False)

session_maker = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
async def drop_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)