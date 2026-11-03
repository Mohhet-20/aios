import datetime as dt

import pytest

from docs_platform.core.exceptions import ValidationError
from docs_platform.versioning.deprecation_service import DeprecationService
from docs_platform.versioning.release_note_service import ReleaseNoteService

pytestmark = pytest.mark.asyncio

TENANT = "t-versioning"


async def test_create_note_rejects_unsupported_kind(repos):
    svc = ReleaseNoteService(repos)
    with pytest.raises(ValidationError):
        await svc.create_note(TENANT, version_label="v1.0", title="X", kind="not-a-kind")


async def test_create_and_list_notes_by_version(repos):
    svc = ReleaseNoteService(repos)
    await svc.create_note(TENANT, version_label="v1.0", title="Launch", kind="feature")
    await svc.create_note(TENANT, version_label="v1.1", title="Bugfix", kind="fix")
    v1_notes = await svc.list_notes(TENANT, version_label="v1.0")
    assert len(v1_notes) == 1
    assert v1_notes[0].title == "Launch"


async def test_deprecation_notice_and_removal_check(repos):
    svc = DeprecationService(repos)
    future_notice = await svc.create_notice(
        TENANT, subject_ref="api:/v0/old", message="use /v1",
        removal_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30),
    )
    assert svc.is_past_removal(future_notice) is False

    past_notice = await svc.create_notice(
        TENANT, subject_ref="api:/v0/older", message="removed",
        removal_at=dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1),
    )
    assert svc.is_past_removal(past_notice) is True

    no_removal_notice = await svc.create_notice(TENANT, subject_ref="api:/v0/soft", message="soft deprecated")
    assert svc.is_past_removal(no_removal_notice) is False

    notices = await svc.list_notices(TENANT)
    assert len(notices) == 3
