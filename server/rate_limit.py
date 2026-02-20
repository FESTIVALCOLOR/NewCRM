"""
Общий Rate Limiter (slowapi) — импортируется в main.py и роутерах.
"""
from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded


def _get_real_client_ip(request: Request) -> str:
    """Получить реальный IP клиента (за Nginx прокси)"""
    return (
        request.headers.get('X-Real-IP')
        or request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
        or (request.client.host if request.client else "unknown")
    )


limiter = Limiter(key_func=_get_real_client_ip, default_limits=["300/minute"])
