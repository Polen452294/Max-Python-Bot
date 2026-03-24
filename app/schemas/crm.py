from app.schemas.common import BaseSchema


class CRMLeadCreate(BaseSchema):
    source: str
    chat_id: int
    user_id: int | None = None
    description: str
    phone: str | None = None
    idempotency_key: str


class CRMLeadCreateResponse(BaseSchema):
    ok: bool = True
    request_id: int
    price_rub: int
    payment_url: str