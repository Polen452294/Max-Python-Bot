from app.schemas.common import BaseSchema


class ConsultationSession(BaseSchema):
    chat_id: int
    user_id: int | None = None
    state: str = "idle"

    description: str | None = None
    phone: str | None = None

    status: str = "new"
    crm_error: str | None = None
    crm_attempts: int = 0
    idempotency_key: str | None = None

    request_id: int | None = None
    price_rub: int | None = None
    payment_url: str | None = None

    bot_message_id: str | None = None
    last_callback_id: str | None = None