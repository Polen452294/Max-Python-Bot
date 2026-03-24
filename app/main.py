import asyncio

from app.infrastructure.crm_client import CRMClient
from app.infrastructure.http_client import build_async_client
from app.infrastructure.max_client import MaxClient
from app.logging_config import setup_logging
from app.repositories.memory_sessions import MemorySessionRepository
from app.services.consultation_flow import ConsultationFlowService
from app.services.dispatcher import UpdateDispatcher
from app.services.polling import PollingRunner
from app.services.ui import UIService


async def _run() -> None:
    max_client = MaxClient(build_async_client())
    crm_client = CRMClient()
    session_repo = MemorySessionRepository()
    ui_service = UIService(session_repo)
    flow_service = ConsultationFlowService(session_repo, crm_client, ui_service)
    dispatcher = UpdateDispatcher(flow_service)
    runner = PollingRunner(max_client, dispatcher)

    try:
        await runner.run()
    finally:
        await max_client.close()
        await crm_client.close()


def main() -> None:
    setup_logging()
    asyncio.run(_run())


if __name__ == "__main__":
    main()