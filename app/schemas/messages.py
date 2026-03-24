from typing import Literal

from app.schemas.common import BaseSchema


class InlineKeyboardButtonCallback(BaseSchema):
    type: Literal["callback"] = "callback"
    text: str
    payload: str


class InlineKeyboardButtonMessage(BaseSchema):
    type: Literal["message"] = "message"
    text: str
    message: str


class InlineKeyboardButtonLink(BaseSchema):
    type: Literal["link"] = "link"
    text: str
    url: str


class InlineKeyboardButtonRequestContact(BaseSchema):
    type: Literal["request_contact"] = "request_contact"
    text: str


class Attachment(BaseSchema):
    type: str
    payload: dict


class NewMessageBody(BaseSchema):
    text: str | None = None
    attachments: list[Attachment] | None = None
    notify: bool | None = True
    format: str | None = None


class AnswerCallbackBody(BaseSchema):
    message: NewMessageBody | None = None
    notification: str | None = None


def inline_keyboard(buttons: list[list[dict]]) -> list[Attachment]:
    return [
        Attachment(
            type="inline_keyboard",
            payload={"buttons": buttons},
        )
    ]


def callback_button(text: str, payload: str) -> dict:
    return InlineKeyboardButtonCallback(text=text, payload=payload).model_dump(exclude_none=True)


def message_button(text: str, message: str) -> dict:
    return InlineKeyboardButtonMessage(text=text, message=message).model_dump(exclude_none=True)


def link_button(text: str, url: str) -> dict:
    return InlineKeyboardButtonLink(text=text, url=url).model_dump(exclude_none=True)


def request_contact_button(text: str) -> dict:
    return InlineKeyboardButtonRequestContact(text=text).model_dump(exclude_none=True)