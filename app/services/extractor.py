import asyncio, json
from dataclasses import dataclass
from urllib.parse import urlparse
from app.services.security import validate_public_url

@dataclass
class ExtractedStream:
    platform: str; title: str; channel: str; thumbnail: str|None; is_live: bool; formats: list[dict]
    @property
    def qualities(self):
        found=[]
        for f in self.formats:
            label=f.get("format_note") or (f"{f.get('height')}p" if f.get("height") else None)
            if label and label not in found: found.append(label)
        return found or ["Best Available"]
    def pick(self, quality: str):
        if quality == "Best Available": return next((f for f in self.formats if f.get("url")), None)
        return next((f for f in self.formats if quality.lower() in str(f.get("format_note","")).lower() or str(f.get("height", "")) in quality), None)

def platform_for(url):
    host=urlparse(url).hostname or ""
    if host.endswith("kick.com"): return "Kick"
    if host.endswith("twitch.tv"): return "Twitch"
    if host.endswith("youtube.com") or host.endswith("youtu.be"): return "YouTube"
    if url.split("?")[0].endswith(".m3u8"): return "HLS"
    if url.split("?")[0].endswith(".mpd"): return "DASH"
    return "Unknown"

async def extract(url: str) -> ExtractedStream:
    await validate_public_url(url)
    platform=platform_for(url)
    if platform == "Unknown": raise ValueError("المنصة غير مدعومة")
    if platform in {"HLS","DASH"}:
        return ExtractedStream(platform, "بث مباشر", "", None, True, [{"url":url,"format_note":"Best Available"}])
    proc=await asyncio.create_subprocess_exec("yt-dlp","--dump-single-json","--no-playlist",url, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out,err=await asyncio.wait_for(proc.communicate(), timeout=35)
    if proc.returncode: raise ValueError("تعذر استخراج البث: " + err.decode(errors="ignore")[-180:])
    data=json.loads(out); live=data.get("is_live") is True or data.get("live_status") in {"is_live","post_live"}
    if not live: raise ValueError("البث غير مباشر حالياً")
    formats=[f for f in data.get("formats",[]) if f.get("url") and f.get("protocol") not in {"mhtml"}]
    if not formats: raise ValueError("لم تتوفر صيغة تشغيل مسموحة")
    return ExtractedStream(platform, data.get("title") or "بث مباشر", data.get("uploader") or data.get("channel") or "", data.get("thumbnail"), True, formats)
