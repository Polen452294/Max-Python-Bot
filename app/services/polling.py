import asyncio
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class PollingRunner:
    def __init__(self, client, dispatcher) -> None:
        self.client = client
        self.dispatcher = dispatcher
        self.settings = get_settings()
        self.marker: int | None = None

    async def run(self) -> None:
        me = await self.client.get_me()
        logger.info(
            "Connected bot: id=%s username=%s first_name=%s",
            me.user_id,
            me.username,
            me.first_name,
        )

        while True:
            try:
                response = await self.client.get_updates(
                    marker=self.marker,
                    limit=self.settings.max_long_poll_limit,
                    timeout=self.settings.max_long_poll_timeout,
                    types=self.settings.allowed_update_types,
                )

                self.marker = response.marker

                for raw_update in response.updates:
                    try:
                        await self.dispatcher.dispatch(self.client, raw_update)
                    except Exception:
                        logger.exception("Failed to process update: %s", raw_update)

            except httpx.HTTPError:
                logger.exception("HTTP/network error while polling")
                await asyncio.sleep(3)

            except Exception:
                logger.exception("Unexpected polling error")
                await asyncio.sleep(3)