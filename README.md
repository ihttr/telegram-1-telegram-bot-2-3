# Telegram Live Stream Bot

بوت خاص يستقبل رابط بث عام ومصرح به، وينشئ جلسة مشاهدة مؤقتة عبر Telegram Mini App أو المتصفح. لا يتجاوز تسجيل الدخول أو DRM أو قيود المنصات، ولا يدّعي أن وجود رابط M3U8 يعني أن الفيديو يعمل.

## التصميم

`Telegram → FastAPI/Vercel → PostgreSQL → Worker طويل التشغيل → مشغل HLS.js`

تتحقق خدمة API من المستخدم والرابط ومنع SSRF. يقوم `yt-dlp` بالاستعلام عن البيانات العامة فقط. العامل الخارجي يستخرج صيغة تشغيل، يفتحها فعلياً للتحقق من استجابة الفيديو، ثم يغير حالة الجلسة إلى `Live`. قبل ذلك يعرض المشغل حالة انتظار، وبعد الفشل يظهر السبب بدلاً من رابط وهمي.

Telegram Bot API لا يستطيع إنشاء بث حي داخل قناة من رابط HLS؛ البديل المطبق هو رابط مشاهدة مؤقت. لا تشغل العامل أو FFmpeg الطويل داخل Vercel.

## التشغيل المحلي

1. أنشئ بيئة Python وثبّت `pip install -r requirements.txt`.
2. انسخ `.env.example` إلى `.env` واضبط `BOT_TOKEN` و`DATABASE_URL` و`JWT_SECRET` وقوائم المعرفات.
3. شغّل `uvicorn app.main:app --reload`.
4. في الإنتاج اضبط webhook إلى `https://DOMAIN/api/telegram/webhook` مع `secret_token` مطابق.

قاعدة البيانات تستخدم SQLAlchemy. شغّل migration رقم `0001` على PostgreSQL قبل الإنتاج؛ لا ينشئ Vercel الجداول أثناء كل cold start. في تطوير محلي سريع فقط، عيّن `AUTO_CREATE_TABLES=true`. تقبل `DATABASE_URL` صيغة Vercel/Neon العادية (`postgresql://...`) أو صيغة `postgresql+asyncpg://...`.

## العامل

ابنِ `worker/Dockerfile` وانشره في خدمة تدعم عملية طويلة. عرّف `CONTROL_API` و`PUBLIC_WORKER_URL` و`WORKER_CALLBACK_SECRET`. أرسل مهمة موثقة إلى `POST /jobs` تتضمن `session_id` و`source_url`. في الإنتاج استبدل مخزن الذاكرة في العامل بـ Redis، وضع URL/task queue موقّعاً بين API والعامل، ووسّع proxy لإعادة كتابة قوائم HLS ومقاطعها كي لا تظهر روابط المصدر في المتصفح.

## الاختبارات

شغّل `pytest`. الاختبارات لا تتصل بمنصات البث. للتحقق التشغيلي اليدوي، اختبر بثاً عاماً مصرحاً به لكل من Kick وTwitch وYouTube في بيئة تملك `yt-dlp` محدثاً؛ النجاح يعني انتقال الجلسة إلى `Live` وبدء الفيديو، وليس نجاح الاستخراج فقط. قد تتطلب بعض المنصات قيوداً جغرافية أو تسجيل دخول، ويجب أن تفشل بوضوح بدلاً من التحايل عليها.

## تنبيهات النشر

Vercel مناسب للـ API والواجهة فقط؛ PostgreSQL وخدمة worker مدفوعتان غالباً بحسب المزوّد والاستهلاك. استخدم HTTPS، أسراراً طويلة، قوائم سماح ضيقة، Redis للـ rate limiting، ومراقبة لا تسجل أي URL موقّع.
