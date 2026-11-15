from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from app.config import settings
from app.database import SessionLocal
from app.services.extractor import extract
from app.services.sessions import get_or_create_user, create_session, viewer_token, playback_path, stop_session, stats, submit_worker

dp=Dispatcher()
def permitted(uid): return not settings().allowed_ids or uid in settings().allowed_ids
async def guard(message):
    if not permitted(message.from_user.id): await message.answer("هذا البوت خاص ولا تملك صلاحية الوصول."); return False
    return True
@dp.message(Command("start"))
async def start(m: Message):
    if await guard(m): await m.answer("مرحباً بك في Live Stream Bot 🎥\n\nأرسل رابط بث عام ومصرح به من Kick أو Twitch أو YouTube أو HLS/DASH للبدء.")
@dp.message(Command("help"))
async def help_(m):
    if await guard(m): await m.answer("أرسل رابط بث مباشر. بعد التحقق من قابلية التشغيل ستصلك صفحة مشاهدة مؤقتة. لا يدعم البوت المحتوى الخاص أو المحمي بـ DRM.")
@dp.message(Command("status"))
async def status(m):
    if await guard(m): await m.answer("الخدمة تعمل. معالجة الفيديو الطويلة تتم خارج Vercel.")
@dp.message(Command("streams"))
async def streams(m):
    if await guard(m): await m.answer("استخدم زر الإيقاف في رسالة كل جلسة، أو /stop <معرّف الجلسة>.")
@dp.message(Command("stop"))
async def stop(m):
    if not await guard(m): return
    parts=m.text.split(maxsplit=1)
    if len(parts)<2: await m.answer("أرسل /stop ثم معرّف الجلسة."); return
    async with SessionLocal() as db: ok=await stop_session(db,parts[1],m.from_user.id)
    await m.answer("تم إيقاف الجلسة." if ok else "لم تُعثر على جلسة تملكها.")
@dp.message(Command("admin"))
async def admin(m):
    if m.from_user.id not in settings().admin_ids: await m.answer("هذا الأمر للمشرف فقط."); return
    async with SessionLocal() as db: s=await stats(db)
    await m.answer(f"لوحة المشرف\nالمستخدمون: {s['users']}\nالروابط: {s['streams']}\nالنشطة: {s['active']}\nالفاشلة: {s['failed']}")
@dp.message(F.text.regexp(r"^https?://"))
async def url(m):
    if not await guard(m): return
    progress=await m.answer("⏳ جاري تحليل رابط البث والتحقق من بدء الفيديو فعلياً...")
    try:
        result=await extract(m.text.strip())
        async with SessionLocal() as db:
            user=await get_or_create_user(db,m.from_user); session=await create_session(db,user,m.text.strip(),result)
            token=viewer_token(session); watch=playback_path(session,token)
        await submit_worker(session.session_id,m.text.strip())
        keyboard=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="▶️ فتح صفحة المشاهدة",web_app=WebAppInfo(url=watch))],[InlineKeyboardButton(text="🌐 فتح في المتصفح الخارجي",url=watch)],[InlineKeyboardButton(text="⏹ إيقاف البث",callback_data=f"stop:{session.session_id}")]])
        qualities="\n".join(f"- {q}" for q in result.qualities[:8])
        await progress.edit_text(f"🎥 معلومات البث\n\n👤 صاحب البث: {result.channel or 'غير متاح'}\n📡 المنصة: {result.platform}\n🟡 الحالة: جارٍ تجهيز مشغل آمن والتحقق من بدء الفيديو\n📝 العنوان: {result.title}\n🎞 الجودات المتاحة:\n{qualities}\n\nلن يبدأ المشغل قبل تأكيد العامل نجاح التشغيل.",reply_markup=keyboard)
    except Exception as e: await progress.edit_text(f"تعذر إنشاء جلسة مشاهدة: {str(e)[:350]}")
@dp.callback_query(F.data.startswith("stop:"))
async def stop_button(q: CallbackQuery):
    async with SessionLocal() as db: ok=await stop_session(db,q.data[5:],q.from_user.id)
    await q.answer("تم إيقاف الجلسة" if ok else "الجلسة غير متاحة",show_alert=True)
def bot(): return Bot(settings().bot_token) if settings().bot_token else None
