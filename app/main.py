from pathlib import Path
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
import jwt
from app.config import settings
from app.database import engine, Base, SessionLocal, StreamSession, Stream
from app.bot import dp, bot
from app.services.extractor import extract

app=FastAPI(title="Telegram Live Stream Bot")
@app.on_event("startup")
async def startup():
    # Schema changes are handled by Alembic in deployment.  Creating tables at
    # every cold start makes the Vercel function fail when DB access is absent.
    if settings().auto_create_tables:
        async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
@app.get("/health")
async def health(): return {"ok":True,"service":"telegram-live-bot"}
@app.get("/static/{asset}")
async def static(asset: str):
    path=Path("frontend") / asset
    if asset not in {"style.css","player.js"} or not path.is_file(): raise HTTPException(404)
    return FileResponse(path)
@app.post("/api/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str|None=Header(default=None)):
    cfg=settings()
    if cfg.bot_webhook_secret and x_telegram_bot_api_secret_token != cfg.bot_webhook_secret: raise HTTPException(403,"invalid webhook secret")
    instance=bot()
    if not instance: raise HTTPException(503,"bot is not configured")
    from aiogram.types import Update
    await dp.feed_update(instance, Update.model_validate(await request.json()))
    return {"ok":True}
@app.get("/watch/{sid}")
async def watch(sid: str, token: str):
    try: claims=jwt.decode(token,settings().jwt_secret,algorithms=["HS256"])
    except jwt.PyJWTError: raise HTTPException(401,"انتهت صلاحية رابط المشاهدة")
    if claims.get("sid")!=sid or claims.get("scope")!="watch": raise HTTPException(403,"رابط مشاهدة غير صالح")
    return FileResponse(Path("frontend/index.html"))
@app.get("/api/playback/{sid}")
async def playback(sid: str, token: str, quality: str="Best Available"):
    try: claims=jwt.decode(token,settings().jwt_secret,algorithms=["HS256"])
    except jwt.PyJWTError: raise HTTPException(401,"expired")
    if claims.get("sid")!=sid: raise HTTPException(403,"invalid")
    async with SessionLocal() as db:
        session=(await db.execute(select(StreamSession).where(StreamSession.session_id==sid))).scalar_one_or_none()
        if not session: raise HTTPException(404,"الجلسة غير موجودة")
        if session.status=="Processing": raise HTTPException(425,"جارٍ التحقق من بدء الفيديو")
        if session.status!="Live": raise HTTPException(404,"الجلسة متوقفة")
        # The source URL is intentionally resolved only server-side in a worker deployment.
        if not session.playback_url: raise HTTPException(409,"لم يسلّم العامل رابط التشغيل الآمن بعد")
        return {"url":session.playback_url,"quality":quality}
@app.post("/api/worker/session/{sid}/ready")
async def worker_ready(sid: str, request: Request, x_worker_secret: str|None=Header(default=None)):
    if x_worker_secret != settings().worker_callback_secret: raise HTTPException(403,"forbidden")
    data=await request.json(); url=data.get("playback_url")
    if not isinstance(url,str) or not url.startswith(("https://","http://")): raise HTTPException(422,"invalid playback url")
    async with SessionLocal() as db:
        session=(await db.execute(select(StreamSession).where(StreamSession.session_id==sid))).scalar_one_or_none()
        if not session: raise HTTPException(404)
        session.playback_url=url; session.status="Live"; await db.commit()
    return {"ok":True}
@app.post("/api/worker/session/{sid}/failed")
async def worker_failed(sid: str, x_worker_secret: str|None=Header(default=None)):
    if x_worker_secret != settings().worker_callback_secret: raise HTTPException(403)
    async with SessionLocal() as db:
        session=(await db.execute(select(StreamSession).where(StreamSession.session_id==sid))).scalar_one_or_none()
        if session: session.status="Failed"; await db.commit()
    return {"ok":True}
