import logging

from fastapi import FastAPI, Header, HTTPException, Request

from app.config import get_settings
from app.infrastructure.http_client import build_async_client
from app.infrastructure.max_client import MaxClient
from app.logging_config import setup_logging
from app.services.dispatcher import UpdateDispatcher

setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI()


@app.on_event("startup")
async def on_startup() -> None:
    app.state.max_client = MaxClient(build_async_client())
    app.state.dispatcher = UpdateDispatcher()

    me = await app.state.max_client.get_me()
    logger.info(
        "Webhook app started for bot: id=%s username=%s",
        me.user_id,
        me.username,
    )


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await app.state.max_client.close()


@app.post(settings.max_webhook_path)
async def max_webhook(
    request: Request,
    x_max_bot_api_secret: str | None = Header(default=None),
) -> dict:
    if settings.max_webhook_secret:
        if x_max_bot_api_secret != settings.max_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    raw_update = await request.json()

    try:
        await app.state.dispatcher.dispatch(app.state.max_client, raw_update)
    except Exception:
        logger.exception("Webhook update processing failed: %s", raw_update)
        raise HTTPException(status_code=500, detail="Update processing failed")

    return {"ok": True}