"""Long-running worker; deploy separately from Vercel (Railway/Fly/Render/Kubernetes)."""
import asyncio, os, secrets, time
from urllib.parse import urljoin
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
import httpx

app=FastAPI(title="Live stream worker")
CONTROL_API=os.environ["CONTROL_API"].rstrip("/")
SECRET=os.environ["WORKER_CALLBACK_SECRET"]
# Use Redis in multi-instance production. This in-memory store deliberately expires with worker restart.
sources: dict[str,tuple[str,float]]={}
TTL_SECONDS=7200
def ticket_for(url: str):
    token=secrets.token_urlsafe(32); sources[token]=(url,time.time()+TTL_SECONDS); return token
async def resolve(url):
    p=await asyncio.create_subprocess_exec("yt-dlp","-g","-f","best",url,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    out,err=await asyncio.wait_for(p.communicate(),35)
    if p.returncode: raise RuntimeError(err.decode(errors="ignore")[-200:])
    return out.decode().strip().splitlines()[0]
async def verify_video_starts(source):
    """Decode a frame: an extracted playlist or HTTP response alone is not success."""
    p=await asyncio.create_subprocess_exec("ffmpeg","-v","error","-i",source,"-map","0:v:0","-frames:v","1","-f","null","-",stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
    _,err=await asyncio.wait_for(p.communicate(),45)
    if p.returncode: raise RuntimeError("ffmpeg could not decode initial video frame: "+err.decode(errors="ignore")[-160:])
@app.post("/jobs")
async def job(payload: dict, x_worker_secret: str|None=Header(default=None)):
    if x_worker_secret!=SECRET: raise HTTPException(403)
    sid,url=payload.get("session_id"),payload.get("source_url")
    if not isinstance(sid,str) or not isinstance(url,str): raise HTTPException(422)
    try:
        source=await resolve(url)
        # Verify that a response can be opened before marking it playable.
        async with httpx.AsyncClient(follow_redirects=True,timeout=15) as client:
            check=await client.get(source,headers={"Range":"bytes=0-1023"})
            if check.status_code not in (200,206): raise RuntimeError("source returned HTTP "+str(check.status_code))
        await verify_video_starts(source)
        ticket=ticket_for(source)
        playback=f"{os.environ['PUBLIC_WORKER_URL'].rstrip('/')}/media/{ticket}"
        async with httpx.AsyncClient() as client: await client.post(f"{CONTROL_API}/api/worker/session/{sid}/ready",json={"playback_url":playback},headers={"X-Worker-Secret":SECRET})
        return {"ok":True}
    except Exception as exc:
        async with httpx.AsyncClient() as client: await client.post(f"{CONTROL_API}/api/worker/session/{sid}/failed",headers={"X-Worker-Secret":SECRET})
        raise HTTPException(502,"playback validation failed") from exc
@app.get("/media/{ticket}")
async def media(ticket: str):
    record=sources.get(ticket)
    if not record or record[1] < time.time():
        sources.pop(ticket,None); raise HTTPException(404)
    source=record[0]
    async with httpx.AsyncClient(follow_redirects=True,timeout=30) as client:
        response=await client.get(source)
    response.raise_for_status()
    content_type=response.headers.get("content-type","").split(";")[0]
    is_hls="m3u8" in content_type or source.split("?")[0].endswith(".m3u8") or response.text.lstrip().startswith("#EXTM3U")
    if is_hls:
        # Do not return source segment addresses: map every URI through a short-lived opaque ticket.
        lines=[]
        for line in response.text.splitlines():
            if line and not line.startswith("#"): lines.append(f"/media/{ticket_for(urljoin(source,line))}")
            else: lines.append(line)
        return StreamingResponse(iter([("\n".join(lines)+"\n").encode()]),media_type="application/vnd.apple.mpegurl")
    return StreamingResponse(iter([response.content]),media_type=content_type or "video/mp4")
