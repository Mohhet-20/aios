import uuid

import pytest

from developer_platform.cli_platform.command_log_service import CliCommandLogService
from developer_platform.cli_platform.session_service import CliSessionService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_log_and_list_commands(repos, db_session):
    tenant_id = _tid()
    session_service = CliSessionService(repos)
    log_service = CliCommandLogService(repos)

    result = await session_service.start_session(tenant_id, developer_id="dev-1")
    await db_session.commit()

    await log_service.log_command(tenant_id, session_id=result.session.id, command="project list", exit_code=0)
    await log_service.log_command(
        tenant_id, session_id=result.session.id, command="deploy", args={"target": "agent-1"}, exit_code=1,
    )
    await db_session.commit()

    logs = await log_service.list_for_session(tenant_id, result.session.id)
    assert len(logs) == 2
    assert {log.command for log in logs} == {"project list", "deploy"}
