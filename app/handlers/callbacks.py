from app.schemas.messages import AnswerCallbackBody, NewMessageBody, callback_button, inline_keyboard
from app.schemas.updates import MessageCallbackUpdate


async def handle_ping_callback(client, update: MessageCallbackUpdate) -> None:
    callback_id = update.callback.callback_id

    body = AnswerCallbackBody(
        notification="Pong",
        message=NewMessageBody(
            text="Кнопка нажата. Всё работает.",
            attachments=inline_keyboard(
                [
                    [callback_button("Нажать ещё раз", "ping")],
                ]
            ),
        ),
    )
    await client.answer_callback(callback_id=callback_id, body=body)