import pytest

from docs_platform.core.exceptions import UnsupportedSdkLanguageError
from docs_platform.sdk_docs.sdk_doc_service import SdkDocService

pytestmark = pytest.mark.asyncio


async def test_create_entry_rejects_unsupported_language(repos):
    svc = SdkDocService(repos)
    with pytest.raises(UnsupportedSdkLanguageError):
        await svc.create_entry("t-sdk-docs", sdk_language="not-a-language", package_ref="pkg", title="X")


async def test_create_and_list_by_language(repos):
    svc = SdkDocService(repos)
    await svc.create_entry("t-sdk-docs", sdk_language="python", package_ref="aios-sdk-py", title="Python Quickstart")
    await svc.create_entry("t-sdk-docs", sdk_language="typescript", package_ref="aios-sdk-ts", title="TS Quickstart")

    python_entries = await svc.list_for_language("t-sdk-docs", "python")
    assert len(python_entries) == 1
    assert python_entries[0].sdk_language == "python"

    all_entries = await svc.list_entries("t-sdk-docs")
    assert len(all_entries) == 2
