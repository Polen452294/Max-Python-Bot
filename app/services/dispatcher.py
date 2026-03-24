import logging

from app.schemas.messages import AnswerCallbackBody
from app.schemas.updates import BotStartedUpdate, MessageCallbackUpdate, MessageCreatedUpdate

logger = logging.getLogger(__name__)


class UpdateDispatcher:
    def __init__(self, flow_service) -> None:
        self.flow_service = flow_service

    async def dispatch(self, client, raw_update: dict) -> None:
        update_type = raw_update.get("update_type")

        if update_type == "bot_started":
            update = BotStartedUpdate.model_validate(raw_update)
            await self._dispatch_bot_started(client, update)
            return

        if update_type == "message_created":
            update = MessageCreatedUpdate.model_validate(raw_update)
            await self._dispatch_message_created(client, update, raw_update)
            return

        if update_type == "message_callback":
            update = MessageCallbackUpdate.model_validate(raw_update)
            await self._dispatch_message_callback(client, update)
            return

        logger.info("Skipped unsupported update type: %s", update_type)

    async def _dispatch_bot_started(self, client, update: BotStartedUpdate) -> None:
        await self.flow_service.start_flow_from_command(
            client=client,
            chat_id=update.chat_id,
            user_id=update.user.user_id if update.user else None,
        )

    async def _dispatch_message_created(self, client, update: MessageCreatedUpdate, raw_update: dict) -> None:
        chat_id = update.message.recipient.chat_id if update.message and update.message.recipient else None
        user_id = update.message.sender.user_id if update.message and update.message.sender else None
        text = (update.message.body.text if update.message and update.message.body else "") or ""

        if chat_id is None:
            return

        logger.info("RAW MESSAGE UPDATE: %s", raw_update)

        handled_contact = await self.flow_service.handle_contact_message(
            client=client,
            chat_id=chat_id,
            user_id=user_id,
            raw_update=raw_update,
        )
        if handled_contact:
            return

        if text.lower().strip() in {"/start", "start", "старт"}:
            await self.flow_service.start_flow_from_command(client, chat_id, user_id)
            return

        await self.flow_service.handle_text(client, chat_id, user_id, text)

    async def _dispatch_message_callback(self, client, update: MessageCallbackUpdate) -> None:
        payload = (update.callback.payload or "").strip()
        callback_id = update.callback.callback_id
        chat_id = update.message.recipient.chat_id if update.message and update.message.recipient else None
        user_id = update.callback.user.user_id if update.callback.user else None

        if chat_id is None:
            return

        session = self.flow_service.session_repo.get_or_create(chat_id, user_id)

        if session.last_callback_id == callback_id:
            await client.answer_callback(
                callback_id=callback_id,
                body=AnswerCallbackBody(notification="Уже обработано"),
            )
            return

        session.last_callback_id = callback_id
        self.flow_service.session_repo.save(session)

        await client.answer_callback(
            callback_id=callback_id,
            body=AnswerCallbackBody(notification="Готово"),
        )

        if payload == "skip_phone":
            if session.state not in {"waiting_phone_optional", "waiting_phone_manual"}:
                return
            await self.flow_service.skip_phone(client, chat_id)
            return

        if payload == "phone_manual":
            if session.state not in {"waiting_phone_optional", "waiting_phone_manual"}:
                return
            await self.flow_service.request_manual_phone(client, chat_id)
            return

        if payload == "retry_crm_submit":
            if session.status != "crm_error":
                return
            await self.flow_service.retry_submit(client, chat_id)
            return

        if payload == "restart_flow":
            await self.flow_service.restart_flow(client, chat_id, user_id)
            return

        if payload == "paid_mock":
            if session.state != "waiting_payment":
                return
            await self.flow_service.mark_paid_mock(client, chat_id)
            return