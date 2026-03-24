import asyncio
from typing import Any

import httpx

from app.schemas.messages import AnswerCallbackBody, NewMessageBody
from app.schemas.updates import MeResponse, UpdatesResponse


class MaxAPIError(Exception):
    pass


class MaxClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_me(self) -> MeResponse:
        response = await self.client.get("/me")
        self._raise_for_status(response)
        return MeResponse.model_validate(response.json())

    async def get_updates(
        self,
        marker: int | None,
        limit: int,
        timeout: int,
        types: list[str] | None = None,
    ) -> UpdatesResponse:
        params: dict[str, Any] = {
            "limit": limit,
            "timeout": timeout,
        }
        if marker is not None:
            params["marker"] = marker
        if types:
            params["types"] = ",".join(types)

        response = await self.client.get("/updates", params=params)
        self._raise_for_status(response)
        return UpdatesResponse.model_validate(response.json())

    async def send_message(
        self,
        *,
        chat_id: int | None = None,
        user_id: int | None = None,
        body: NewMessageBody,
        disable_link_preview: bool | None = None,
    ) -> dict:
        params: dict[str, Any] = {}
        if chat_id is not None:
            params["chat_id"] = chat_id
        if user_id is not None:
            params["user_id"] = user_id
        if disable_link_preview is not None:
            params["disable_link_preview"] = disable_link_preview

        response = await self.client.post(
            "/messages",
            params=params,
            json=body.model_dump(exclude_none=True),
        )
        self._raise_for_status(response)
        return response.json()

    async def edit_message(
        self,
        *,
        message_id: str,
        body: NewMessageBody,
        notify: bool = False,
    ) -> dict:
        response = await self.client.put(
            f"/messages/{message_id}",
            params={"notify": notify},
            json=body.model_dump(exclude_none=True),
        )
        self._raise_for_status(response)
        return response.json()

    async def answer_callback(
        self,
        *,
        callback_id: str,
        body: AnswerCallbackBody,
    ) -> dict:
        response = await self.client.post(
            "/answers",
            params={"callback_id": callback_id},
            json=body.model_dump(exclude_none=True),
        )
        self._raise_for_status(response)
        return response.json()

    async def close(self) -> None:
        await self.client.aclose()

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.is_success:
            return
        raise MaxAPIError(f"MAX API error: status={response.status_code}, body={response.text}")

    async def safe_typing_delay(self, seconds: float = 0.2) -> None:
        await asyncio.sleep(seconds)