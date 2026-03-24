from typing import Literal

from app.schemas.common import BaseSchema


class UserRef(BaseSchema):
    user_id: int | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    is_bot: bool | None = None
    name: str | None = None


class Recipient(BaseSchema):
    chat_id: int | None = None
    chat_type: str | None = None
    user_id: int | None = None


class MessageBody(BaseSchema):
    mid: str | None = None
    seq: int | None = None
    text: str | None = None
    attachments: list[dict] | None = None


class Message(BaseSchema):
    recipient: Recipient | None = None
    timestamp: int | None = None
    body: MessageBody | None = None
    sender: UserRef | None = None


class Callback(BaseSchema):
    callback_id: str
    payload: str | None = None
    user: UserRef | None = None


class MessageCreatedUpdate(BaseSchema):
    update_type: Literal["message_created"]
    timestamp: int | None = None
    user_locale: str | None = None
    message: Message


class MessageCallbackUpdate(BaseSchema):
    update_type: Literal["message_callback"]
    timestamp: int | None = None
    user_locale: str | None = None
    callback: Callback
    message: Message | None = None


class BotStartedUpdate(BaseSchema):
    update_type: Literal["bot_started"]
    timestamp: int | None = None
    chat_id: int
    payload: str | None = None
    user: UserRef | None = None


class UpdatesResponse(BaseSchema):
    updates: list[dict]
    marker: int | None = None


class MeResponse(BaseSchema):
    user_id: int
    first_name: str | None = None
    username: str | None = None
    is_bot: bool | None = None