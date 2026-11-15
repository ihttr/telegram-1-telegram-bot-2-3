from datetime import datetime
from sqlalchemy import String, BigInteger, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True); telegram_id: Mapped[int]=mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str|None]=mapped_column(String(100)); first_name: Mapped[str|None]=mapped_column(String(200)); is_banned: Mapped[bool]=mapped_column(Boolean, default=False); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
class Stream(Base):
    __tablename__="streams"
    id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id")); platform: Mapped[str]=mapped_column(String(40)); original_url: Mapped[str]=mapped_column(Text); title: Mapped[str|None]=mapped_column(Text); channel_name: Mapped[str|None]=mapped_column(String(300)); thumbnail: Mapped[str|None]=mapped_column(Text); status: Mapped[str]=mapped_column(String(30)); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
class StreamSession(Base):
    __tablename__="stream_sessions"
    id: Mapped[int]=mapped_column(primary_key=True); stream_id: Mapped[int]=mapped_column(ForeignKey("streams.id")); session_id: Mapped[str]=mapped_column(String(64), unique=True, index=True); quality: Mapped[str]=mapped_column(String(40)); playback_url: Mapped[str|None]=mapped_column(Text); status: Mapped[str]=mapped_column(String(30)); started_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow); stopped_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
class Log(Base):
    __tablename__="logs"
    id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"), nullable=True); action: Mapped[str]=mapped_column(String(80)); details: Mapped[str|None]=mapped_column(Text); created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

engine=create_async_engine(settings().database_url); SessionLocal=async_sessionmaker(engine, expire_on_commit=False)
async def get_db():
    async with SessionLocal() as db: yield db
