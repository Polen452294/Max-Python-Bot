import asyncio

import httpx

from app.config import get_settings
from app.schemas.crm import CRMLeadCreateResponse


class CRMUnavailableError(Exception):
    pass


class CRMValidationError(Exception):
    pass


class CRMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = httpx.AsyncClient(
            base_url=settings.crm_base_url,
            headers={"X-Api-Key": settings.crm_api_key},
            timeout=20.0,
        )

    async def create_lead(self, lead) -> CRMLeadCreateResponse:
        last_error: Exception | None = None

        for attempt in range(1, self.settings.crm_max_retries + 1):
            try:
                response = await self.client.post(
                    "/leads",
                    json=lead.model_dump(),
                    headers={"Idempotency-Key": lead.idempotency_key},
                )

                if response.status_code >= 500:
                    raise CRMUnavailableError(
                        f"CRM temporary unavailable: status={response.status_code}, body={response.text}"
                    )

                if response.status_code >= 400:
                    raise CRMValidationError(
                        f"CRM rejected request: status={response.status_code}, body={response.text}"
                    )

                return CRMLeadCreateResponse.model_validate(response.json())

            except (CRMUnavailableError, httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt == self.settings.crm_max_retries:
                    break
                await asyncio.sleep(self.settings.crm_retry_base_delay * attempt)

        if last_error:
            raise last_error

        raise CRMUnavailableError("CRM request failed without explicit error")

    async def close(self) -> None:
        await self.client.aclose()