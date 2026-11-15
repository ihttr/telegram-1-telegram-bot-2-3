from datetime import datetime
from sqlalchemy import String, BigInteger, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
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

_database_url = settings().database_url
# Vercel is serverless. Supabase transaction pooler (port 6543) must not retain
# connections or prepare statements across transactions.
_engine_options = {}
if _database_url.startswith("postgresql+asyncpg://"):
    _engine_options = {
        "poolclass": NullPool,
        "connect_args": {"statement_cache_size": 0, "ssl": "require"},
    }
engine = create_async_engine(_database_url, **_engine_options) if settings().database_enabled else None
SessionLocal = async_sessionmaker(engine, expire_on_commit=False) if engine else None
async def get_db():
    if SessionLocal is None: raise RuntimeError("قاعدة البيانات معطلة")
    async with SessionLocal() as db: yield db
