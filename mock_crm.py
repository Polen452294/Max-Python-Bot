from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI()


class Lead(BaseModel):
    source: str
    chat_id: int
    user_id: int | None = None
    description: str
    phone: str | None = None
    idempotency_key: str


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/leads")
async def create_lead(lead: Lead, idempotency_key: str | None = Header(default=None)):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is required")

    return {
        "ok": True,
        "request_id": 1,
        "price_rub": 200,
        "payment_url": "https://example.com/pay/consultation/1",
    }