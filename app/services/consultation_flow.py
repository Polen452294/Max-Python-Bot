import logging
import re
import uuid

import httpx

from app.infrastructure.crm_client import CRMUnavailableError, CRMValidationError
from app.schemas.crm import CRMLeadCreate
from app.schemas.messages import (
    NewMessageBody,
    callback_button,
    inline_keyboard,
    link_button,
    request_contact_button,
)

logger = logging.getLogger(__name__)


def normalize_phone(value: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", value.strip())
    if cleaned.startswith("8") and len(cleaned) == 11:
        cleaned = "+7" + cleaned[1:]
    if cleaned.startswith("7") and len(cleaned) == 11:
        cleaned = "+" + cleaned
    return cleaned


def extract_phone_from_vcf(vcf_info: str) -> str | None:
    for line in vcf_info.splitlines():
        line = line.strip()
        if line.startswith("TEL"):
            parts = line.split(":", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return None


class ConsultationFlowService:
    def __init__(self, session_repo, crm_client, ui_service) -> None:
        self.session_repo = session_repo
        self.crm_client = crm_client
        self.ui = ui_service

    async def start_flow_from_command(self, client, chat_id: int, user_id: int | None) -> None:
        session = self.session_repo.get_or_create(chat_id, user_id)
        session.state = "waiting_description"
        session.status = "new"
        session.crm_error = None
        session.crm_attempts = 0
        session.description = None
        session.phone = None
        session.request_id = None
        session.price_rub = None
        session.payment_url = None
        session.idempotency_key = str(uuid.uuid4())
        self.session_repo.save(session)

        text = (
            "Привет! Я помогу оформить запрос на юридическую консультацию.\n\n"
            "⚠️ Важно:\n"
            "• Информация носит консультационный характер и не является публичной офертой.\n"
            "• Отправляя запрос, вы соглашаетесь на обработку ваших данных исключительно для оказания консультации.\n\n"
            "Шаг 1/2: опишите вашу ситуацию одним сообщением.\n"
            "Если нужны контакты — я попрошу их на следующем шаге.\n\n"
            "Опишите вопрос максимально конкретно:\n"
            "• что произошло\n"
            "• какие документы или даты важны\n"
            "• что вы хотите получить"
        )

        await self.ui.upsert_bot_message(
            client,
            chat_id,
            NewMessageBody(
                text=text,
            ),
        )

    async def handle_text(self, client, chat_id: int, user_id: int | None, text: str) -> None:
        session = self.session_repo.get_or_create(chat_id, user_id)

        if not text:
            return

        if session.state in {"idle", "done"}:
            await self.start_flow_from_command(client, chat_id, user_id)
            return

        if session.state == "waiting_description":
            session.description = text
            session.state = "waiting_phone_optional"
            self.session_repo.save(session)

            await self.ui.upsert_bot_message(
                client,
                chat_id,
                NewMessageBody(
                    text=(
                        "Шаг 2/2 (опционально): хотите оставить номер телефона для связи?\n"
                        "Нажмите кнопку ниже или пропустите этот шаг."
                    ),
                    attachments=inline_keyboard(
                        [
                            [request_contact_button("📞 Поделиться контактом")],
                            [callback_button("Пропустить", "skip_phone")],
                            [callback_button("Ввести вручную", "phone_manual")],
                        ]
                    ),
                ),
            )
            return

        if session.state == "waiting_phone_manual":
            phone = normalize_phone(text)
            if len(phone) < 11:
                await self.ui.upsert_bot_message(
                    client,
                    chat_id,
                    NewMessageBody(
                        text=(
                            "Номер выглядит неполным.\n"
                            "Отправьте его в формате +79991234567."
                        ),
                        attachments=inline_keyboard(
                            [
                                [callback_button("Пропустить", "skip_phone")],
                            ]
                        ),
                    ),
                )
                return

            session.phone = phone
            self.session_repo.save(session)
            await self.submit_to_crm(client, chat_id)
            return

    async def handle_contact_message(self, client, chat_id: int, user_id: int | None, raw_update: dict) -> bool:
        session = self.session_repo.get_or_create(chat_id, user_id)
        if session.state not in {"waiting_phone_optional", "waiting_phone_manual"}:
            return False

        message = raw_update.get("message", {}) or {}
        body = message.get("body", {}) or {}

        logger.info("CONTACT BODY: %s", body)

        possible_phones: list[str] = []

        text_value = body.get("text")
        if isinstance(text_value, str) and text_value.strip():
            possible_phones.append(text_value.strip())

        for key in ("phone", "phone_number", "value"):
            value = body.get(key)
            if value:
                possible_phones.append(str(value))

        contact = body.get("contact")
        if isinstance(contact, dict):
            for key in ("phone", "phone_number", "value"):
                value = contact.get(key)
                if value:
                    possible_phones.append(str(value))

        attachments = body.get("attachments", [])
        if isinstance(attachments, list):
            for attachment in attachments:
                if not isinstance(attachment, dict):
                    continue

                attachment_type = attachment.get("type")
                payload = attachment.get("payload", {}) or {}

                for key in ("phone", "phone_number", "value"):
                    value = attachment.get(key)
                    if value:
                        possible_phones.append(str(value))

                if isinstance(payload, dict):
                    for key in ("phone", "phone_number", "value"):
                        value = payload.get(key)
                        if value:
                            possible_phones.append(str(value))

                    nested_contact = payload.get("contact")
                    if isinstance(nested_contact, dict):
                        for key in ("phone", "phone_number", "value"):
                            value = nested_contact.get(key)
                            if value:
                                possible_phones.append(str(value))

                    if attachment_type == "contact":
                        vcf_info = payload.get("vcf_info")
                        if isinstance(vcf_info, str) and vcf_info.strip():
                            phone_from_vcf = extract_phone_from_vcf(vcf_info)
                            if phone_from_vcf:
                                possible_phones.append(phone_from_vcf)

        logger.info("POSSIBLE PHONES: %s", possible_phones)

        for raw_phone in possible_phones:
            phone = normalize_phone(raw_phone)
            if len(phone) >= 11:
                session.phone = phone
                self.session_repo.save(session)
                await self.submit_to_crm(client, chat_id)
                return True

        await self.ui.upsert_bot_message(
            client,
            chat_id,
            NewMessageBody(
                text=(
                    "Я получил контакт, но не смог распознать номер телефона.\n\n"
                    "Вы можете отправить номер вручную в формате +79991234567 "
                    "или пропустить этот шаг."
                ),
                attachments=inline_keyboard(
                    [
                        [callback_button("Ввести вручную", "phone_manual")],
                        [callback_button("Пропустить", "skip_phone")],
                    ]
                ),
            ),
        )
        return True

    async def request_manual_phone(self, client, chat_id: int) -> None:
        session = self.session_repo.get(chat_id)
        if not session:
            return

        session.state = "waiting_phone_manual"
        self.session_repo.save(session)

        await self.ui.upsert_bot_message(
            client,
            chat_id,
            NewMessageBody(
                text="Отправьте номер телефона сообщением в формате +79991234567.",
                attachments=inline_keyboard(
                    [
                        [callback_button("Пропустить", "skip_phone")],
                    ]
                ),
            ),
        )

    async def skip_phone(self, client, chat_id: int) -> None:
        await self.submit_to_crm(client, chat_id)

    async def submit_to_crm(self, client, chat_id: int) -> None:
        session = self.session_repo.get(chat_id)
        if session.state == "waiting_payment":
            return

        if session.status == "paid":
            return

        lead = CRMLeadCreate(
            source="max",
            chat_id=session.chat_id,
            user_id=session.user_id,
            description=session.description or "",
            phone=session.phone,
            idempotency_key=session.idempotency_key or str(uuid.uuid4()),
        )

        try:
            session.crm_attempts += 1
            self.session_repo.save(session)

            response = await self.crm_client.create_lead(lead)

            session.status = "sent_to_crm"
            session.crm_error = None
            session.request_id = response.request_id
            session.price_rub = response.price_rub
            session.payment_url = response.payment_url
            session.state = "waiting_payment"
            self.session_repo.save(session)

            await self.ui.upsert_bot_message(
                client,
                chat_id,
                NewMessageBody(
                    text=(
                        "Заявка отправлена ✅\n"
                        "Юрист проверит обращение, после чего мы выставим стоимость консультации или уточним детали."
                    ),
                ),
            )

            await client.send_message(
                chat_id=chat_id,
                body=NewMessageBody(
                    text=(
                        f"Стоимость консультации: {session.price_rub} RUB.\n"
                        "Нажмите «Оплатить», чтобы перейти к оплате."
                    ),
                    attachments=inline_keyboard(
                        [
                            [link_button("💳 Оплатить", session.payment_url or "https://example.com/pay")],
                            [callback_button("Я уже оплатил", "paid_mock")],
                        ]
                    ),
                ),
            )

        except CRMUnavailableError as exc:
            session.status = "crm_error"
            session.crm_error = str(exc)
            self.session_repo.save(session)

            logger.exception("CRM temporarily unavailable for chat_id=%s", chat_id)

            await self.ui.upsert_bot_message(
                client,
                chat_id,
                NewMessageBody(
                    text=(
                        "Не удалось передать заявку в CRM: сервис временно недоступен.\n"
                        "Попробуйте ещё раз немного позже."
                    ),
                    attachments=inline_keyboard(
                        [
                            [callback_button("Повторить отправку", "retry_crm_submit")],
                            [callback_button("Начать заново", "restart_flow")],
                        ]
                    ),
                ),
            )

        except (CRMValidationError, httpx.HTTPError) as exc:
            session.status = "crm_error"
            session.crm_error = str(exc)
            self.session_repo.save(session)

            logger.exception("CRM submit error for chat_id=%s", chat_id)

            await self.ui.upsert_bot_message(
                client,
                chat_id,
                NewMessageBody(
                    text=(
                        "Не удалось отправить заявку.\n"
                        "Попробуйте пройти форму ещё раз."
                    ),
                    attachments=inline_keyboard(
                        [
                            [callback_button("Начать заново", "restart_flow")],
                        ]
                    ),
                ),
            )

    async def retry_submit(self, client, chat_id: int) -> None:
        await self.submit_to_crm(client, chat_id)

    async def restart_flow(self, client, chat_id: int, user_id: int | None) -> None:
        await self.start_flow_from_command(client, chat_id, user_id)

    async def mark_paid_mock(self, client, chat_id: int) -> None:
        session = self.session_repo.get(chat_id)
        if not session:
            return

        session.state = "done"
        session.status = "paid"
        self.session_repo.save(session)

        await client.send_message(
            chat_id=chat_id,
            body=NewMessageBody(
                text="Оплата получена ✅\nЮрист скоро свяжется с вами."
            ),
        )

        self.session_repo.delete(chat_id)

    def extract_phone_from_vcf(vcf_info: str) -> str | None:
        for line in vcf_info.splitlines():
            line = line.strip()
            if line.startswith("TEL"):
                parts = line.split(":", 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return None