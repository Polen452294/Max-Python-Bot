from app.schemas.messages import NewMessageBody
from app.schemas.updates import MessageCreatedUpdate


async def handle_start(client, update: MessageCreatedUpdate) -> None:
    chat_id = update.message.recipient.chat_id if update.message and update.message.recipient else None
    if chat_id is None:
        return

    text = (
        "Привет! Я помогу оформить запрос на юридическую консультацию.\n\n"
        "⚠️ Важно:\n"
        "• Информация носит консультационный характер и не является публичной офертой.\n"
        "• Отправляя запрос, вы соглашаетесь на обработку ваших данных "
        "(Telegram ID, имя, username, текст обращения) исключительно для оказания консультации.\n\n"
        "Шаг 1/2: опишите вашу ситуацию одним сообщением.\n"
        "Если нужны контакты — я попрошу их на следующем шаге.\n\n"
        "Опишите вопрос/ситуацию максимально конкретно:\n"
        "• что произошло\n"
        "• какие документы или даты важны\n"
        "• что вы хотите получить "
        "(консультация / план действий / проверка договора и т.д.)"
    )

    await client.send_message(
        chat_id=chat_id,
        body=NewMessageBody(text=text),
    )