import ipaddress, socket
from urllib.parse import urlparse
class UnsafeUrl(ValueError): pass
async def validate_public_url(url: str) -> str:
    p=urlparse(url)
    if p.scheme not in {"http","https"} or not p.hostname or p.username or p.password: raise UnsafeUrl("الرابط غير صالح")
    if p.hostname.lower() in {"localhost","metadata.google.internal"}: raise UnsafeUrl("العناوين الداخلية غير مسموحة")
    try:
        for item in socket.getaddrinfo(p.hostname, None):
            addr=ipaddress.ip_address(item[4][0])
            if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved: raise UnsafeUrl("العناوين الداخلية غير مسموحة")
    except socket.gaierror: raise UnsafeUrl("تعذر التحقق من اسم النطاق")
    return url
