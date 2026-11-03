"""Version protection: an explicit, reusable guard for callers who
want to check editability up front (e.g. before opening an edit form)
rather than discovering it via the generic ValidationError that
DocPageService.update_content already raises inline. Both guards
express the same rule (published pages aren't directly content-edited
— they go through submit_for_review -> ... -> a fresh draft/version);
this one just gives that specific failure mode its own exception type
per the prompt's "Version Protection" governance concept."""
from __future__ import annotations

from docs_platform.core.exceptions import VersionProtectedError
from docs_platform.models.documentation import DocPageModel

_PROTECTED_STATUSES = {"published", "archived", "deprecated"}


class GovernanceService:
    def assert_editable(self, page: DocPageModel) -> None:
        if page.status in _PROTECTED_STATUSES:
            raise VersionProtectedError(
                f"Doc page '{page.id}' is '{page.status}' and is version-protected — it cannot be edited directly"
            )
