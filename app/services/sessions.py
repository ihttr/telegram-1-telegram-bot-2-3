import secrets
from datetime import datetime, timedelta, timezone
import jwt
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import User, Stream, StreamSession, Log
from app.services.extractor import ExtractedStream

async def get_or_create_user(db, tg):
    user=(await db.execute(select(User).where(User.telegram_id==tg.id))).scalar_one_or_none()
    if not user:
        user=User(telegram_id=tg.id, username=tg.username, first_name=tg.first_name); db.add(user); await db.flush()
    return user
async def create_session(db: AsyncSession, user: User, original_url: str, result: ExtractedStream):
    stream=Stream(user_id=user.id,platform=result.platform,original_url=original_url,title=result.title,channel_name=result.channel,thumbnail=result.thumbnail,status="Live")
    db.add(stream); await db.flush()
    # A worker must validate and proxy the media before the session becomes Live.
    session=StreamSession(stream_id=stream.id,session_id=secrets.token_urlsafe(24),quality="Best Available",status="Processing")
    db.add(session); db.add(Log(user_id=user.id,action="stream_created",details=result.platform)); await db.commit(); await db.refresh(session)
    return session
def viewer_token(session: StreamSession):
    until=datetime.now(timezone.utc)+timedelta(minutes=settings().session_ttl_minutes)
    return jwt.encode({"sid":session.session_id,"exp":until,"scope":"watch"},settings().jwt_secret,algorithm="HS256")
def playback_path(session, token): return f"{settings().public_base_url.rstrip('/')}/watch/{session.session_id}?token={token}"
async def stop_session(db, sid, telegram_id):
    row=(await db.execute(select(StreamSession,Stream,User).join(Stream,StreamSession.stream_id==Stream.id).join(User,Stream.user_id==User.id).where(StreamSession.session_id==sid,User.telegram_id==telegram_id))).first()
    if not row: return False
    row[0].status="Stopped"; row[0].stopped_at=datetime.utcnow(); row[1].status="Stopped"; await db.commit(); return True
async def stats(db):
    return {"users":(await db.scalar(select(func.count(User.id)))) or 0,"streams":(await db.scalar(select(func.count(Stream.id)))) or 0,"active":(await db.scalar(select(func.count(StreamSession.id)).where(StreamSession.status=="Live"))) or 0,"failed":(await db.scalar(select(func.count(StreamSession.id)).where(StreamSession.status=="Failed"))) or 0}
async def submit_worker(session_id: str, source_url: str):
    """Queues validation; no media URL is returned to Telegram or the browser here."""
    cfg=settings()
    if not cfg.worker_url: raise RuntimeError("عامل البث غير مُعدّ. اضبط WORKER_URL.")
    async with httpx.AsyncClient(timeout=10) as client:
        response=await client.post(cfg.worker_url.rstrip("/")+"/jobs",json={"session_id":session_id,"source_url":source_url},headers={"X-Worker-Secret":cfg.worker_callback_secret})
        response.raise_for_status()
