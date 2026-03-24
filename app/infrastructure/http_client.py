import httpx

from app.config import get_settings


def build_async_client() -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(
        base_url=settings.max_api_base,
        headers={
            "Authorization": settings.max_bot_token,
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(connect=10.0, read=95.0, write=30.0, pool=10.0),
    )