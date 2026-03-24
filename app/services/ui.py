from app.schemas.messages import NewMessageBody


class UIService:
    def __init__(self, session_repo) -> None:
        self.session_repo = session_repo

    async def upsert_bot_message(self, client, chat_id: int, body: NewMessageBody) -> dict:
        session = self.session_repo.get(chat_id)
        if session and session.bot_message_id:
            try:
                result = await client.edit_message(
                    message_id=session.bot_message_id,
                    body=body,
                    notify=False,
                )
                return result
            except Exception:
                pass

        result = await client.send_message(chat_id=chat_id, body=body)

        if session:
            message = result.get("message") or result
            mid = (
                message.get("body", {}).get("mid")
                or message.get("mid")
                or message.get("message_id")
            )
            if mid:
                session.bot_message_id = mid
                self.session_repo.save(session)

        return result