"""Small webhook API: the user-facing experience is entirely in Telegram."""
from fastapi import FastAPI, HTTPException, Header, Request
from app.config import settings
from app.database import engine, Base
from app.bot import dp, bot

app = FastAPI(title="Telegram Live Stream Bot")

@app.on_event("startup")
async def startup():
    if settings().database_enabled and settings().auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

@app.get("/")
@app.get("/health")
async def health():
    return {"ok": True, "service": "telegram-live-bot", "mode": "telegram-only"}

@app.post("/api/telegram/webhook")
async def webhook(request: Request, x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    cfg = settings()
    if cfg.bot_webhook_secret and x_telegram_bot_api_secret_token != cfg.bot_webhook_secret:
        raise HTTPException(403, "invalid webhook secret")
    instance = bot()
    if not instance:
        raise HTTPException(503, "BOT_TOKEN is not configured")
    from aiogram.types import Update
    await dp.feed_update(instance, Update.model_validate(await request.json()))
    return {"ok": True}
