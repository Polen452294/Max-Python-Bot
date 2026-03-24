from app.schemas.updates import MessageCreatedUpdate


def extract_text(update: MessageCreatedUpdate) -> str:
    text = update.message.body.text if update.message and update.message.body else None
    return (text or "").strip()