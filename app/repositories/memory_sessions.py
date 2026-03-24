from app.schemas.session import ConsultationSession


class MemorySessionRepository:
    def __init__(self) -> None:
        self._storage: dict[int, ConsultationSession] = {}

    def get(self, chat_id: int) -> ConsultationSession | None:
        return self._storage.get(chat_id)

    def get_or_create(self, chat_id: int, user_id: int | None = None) -> ConsultationSession:
        session = self._storage.get(chat_id)
        if session is None:
            session = ConsultationSession(chat_id=chat_id, user_id=user_id)
            self._storage[chat_id] = session
        return session

    def save(self, session: ConsultationSession) -> None:
        self._storage[session.chat_id] = session

    def delete(self, chat_id: int) -> None:
        self._storage.pop(chat_id, None)