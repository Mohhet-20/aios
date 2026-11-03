import pytest

from tool_platform.core.exceptions import InvalidTransitionError, ValidationError
from tool_platform.domain.entities import Credential, PluginInstallation, Schedule, Tool, ToolExecution
from tool_platform.domain.enums import (
    CredentialStatus,
    ExecutionStatus,
    PluginInstallationStatus,
    ScheduleStatus,
    ToolStatus,
)


def _tool(**overrides):
    defaults = dict(id="tool-1", workspace_id="ws-1", organization_id="org-1", name="My Tool", slug="my-tool", owner_id="u1", category="rest_api")
    defaults.update(overrides)
    return Tool(**defaults)


def _execution(**overrides):
    defaults = dict(id="exec-1", tool_id="tool-1", tool_version_id="v-1", workspace_id="ws-1")
    defaults.update(overrides)
    return ToolExecution(**defaults)


def _plugin_install(**overrides):
    defaults = dict(id="pi-1", plugin_id="plugin-1", workspace_id="ws-1", installed_version="1.0.0", installed_by="u1")
    defaults.update(overrides)
    return PluginInstallation(**defaults)


def _credential(**overrides):
    defaults = dict(id="cred-1", workspace_id="ws-1", name="GitHub PAT", credential_type="api_key", owner_id="u1")
    defaults.update(overrides)
    return Credential(**defaults)


def _schedule(**overrides):
    defaults = dict(id="sched-1", tool_id="tool-1", workspace_id="ws-1", schedule_type="immediate", created_by="u1")
    defaults.update(overrides)
    return Schedule(**defaults)


# -- Tool --------------------------------------------------------------------------

class TestTool:
    def test_publish_first_version_flips_to_published(self):
        tool = _tool()
        tool.publish("v-1")
        assert tool.status == ToolStatus.PUBLISHED
        assert tool.current_version_id == "v-1"

    def test_publish_without_version_id_rejected(self):
        tool = _tool()
        with pytest.raises(ValidationError):
            tool.publish("")

    def test_republishing_already_published_tool_just_repoints_version(self):
        tool = _tool(status=ToolStatus.PUBLISHED, current_version_id="v-1")
        tool.publish("v-2")
        assert tool.status == ToolStatus.PUBLISHED
        assert tool.current_version_id == "v-2"

    def test_deprecate_then_republish(self):
        tool = _tool(status=ToolStatus.PUBLISHED, current_version_id="v-1")
        tool.deprecate()
        assert tool.status == ToolStatus.DEPRECATED
        tool.publish("v-2")
        assert tool.status == ToolStatus.PUBLISHED

    def test_disable_and_enable(self):
        tool = _tool(status=ToolStatus.PUBLISHED, current_version_id="v-1")
        tool.disable()
        assert tool.status == ToolStatus.DISABLED
        tool.enable()
        assert tool.status == ToolStatus.PUBLISHED

    def test_enable_only_from_disabled(self):
        tool = _tool(status=ToolStatus.DRAFT)
        with pytest.raises(InvalidTransitionError):
            tool.enable()

    def test_draft_cannot_deprecate_directly(self):
        tool = _tool()
        with pytest.raises(InvalidTransitionError):
            tool.deprecate()


# -- ToolExecution -------------------------------------------------------------------

class TestToolExecution:
    def test_happy_path_completes(self):
        execution = _execution()
        execution.queue()
        execution.start()
        assert execution.started_at is not None
        execution.succeed({"result": "ok"})
        assert execution.status == ExecutionStatus.SUCCEEDED
        assert execution.output_data == {"result": "ok"}
        assert execution.duration_ms is not None
        assert execution.duration_ms >= 0

    def test_pending_can_start_directly_without_queueing(self):
        execution = _execution()
        execution.start()
        assert execution.status == ExecutionStatus.RUNNING

    def test_fail_then_retry_then_succeed(self):
        execution = _execution(max_retries=2)
        execution.start()
        execution.fail("boom")
        assert execution.status == ExecutionStatus.FAILED
        execution.retry()
        assert execution.status == ExecutionStatus.RETRYING
        assert execution.attempt_number == 2
        execution.resume_after_retry()
        assert execution.status == ExecutionStatus.RUNNING
        execution.succeed()
        assert execution.status == ExecutionStatus.SUCCEEDED

    def test_retry_exhausted_raises_when_over_max(self):
        execution = _execution(max_retries=1, attempt_number=2)
        execution.start()
        execution.fail("boom")
        with pytest.raises(InvalidTransitionError):
            execution.retry()

    def test_exhaust_retries_must_be_retrying(self):
        execution = _execution()
        execution.start()
        execution.fail("boom")
        with pytest.raises(InvalidTransitionError):
            execution.exhaust_retries("gave up")

    def test_exhaust_retries_from_retrying_marks_failed(self):
        execution = _execution(max_retries=3)
        execution.start()
        execution.fail("boom")
        execution.retry()
        execution.exhaust_retries("out of attempts")
        assert execution.status == ExecutionStatus.FAILED
        assert execution.error_message == "out of attempts"

    def test_timeout_sets_default_message(self):
        execution = _execution()
        execution.start()
        execution.timeout()
        assert execution.status == ExecutionStatus.TIMED_OUT
        assert "timeout" in execution.error_message

    def test_rollback_only_from_failed_or_timed_out(self):
        execution = _execution()
        with pytest.raises(InvalidTransitionError):
            execution.rollback()
        execution.start()
        execution.fail("boom")
        execution.rollback()
        assert execution.status == ExecutionStatus.ROLLED_BACK

    def test_cancel_from_running(self):
        execution = _execution()
        execution.start()
        execution.cancel()
        assert execution.status == ExecutionStatus.CANCELLED

    def test_terminal_statuses(self):
        assert ExecutionStatus.SUCCEEDED.is_terminal()
        assert ExecutionStatus.CANCELLED.is_terminal()
        assert ExecutionStatus.ROLLED_BACK.is_terminal()
        assert not ExecutionStatus.FAILED.is_terminal()
        assert not ExecutionStatus.TIMED_OUT.is_terminal()

    def test_succeeded_is_truly_terminal_no_further_transitions(self):
        execution = _execution()
        execution.start()
        execution.succeed()
        with pytest.raises(InvalidTransitionError):
            execution.cancel()


# -- PluginInstallation ---------------------------------------------------------------

class TestPluginInstallation:
    def test_install_then_enable(self):
        install = _plugin_install()
        assert install.status == PluginInstallationStatus.INSTALLED
        install.enable()
        assert install.status == PluginInstallationStatus.ENABLED

    def test_update_cycle_success(self):
        install = _plugin_install(status=PluginInstallationStatus.ENABLED)
        install.begin_update()
        assert install.status == PluginInstallationStatus.UPDATING
        install.complete_update("2.0.0", was_enabled=True)
        assert install.status == PluginInstallationStatus.ENABLED
        assert install.installed_version == "2.0.0"

    def test_update_cycle_failure_preserves_old_version(self):
        install = _plugin_install(status=PluginInstallationStatus.ENABLED)
        install.begin_update()
        install.fail_update("checksum mismatch")
        assert install.status == PluginInstallationStatus.FAILED
        assert install.installed_version == "1.0.0"
        assert install.configuration["last_update_error"] == "checksum mismatch"

    def test_complete_update_requires_updating_status(self):
        install = _plugin_install(status=PluginInstallationStatus.ENABLED)
        with pytest.raises(InvalidTransitionError):
            install.complete_update("2.0.0", was_enabled=True)

    def test_uninstall_terminal(self):
        install = _plugin_install(status=PluginInstallationStatus.ENABLED)
        install.uninstall()
        assert install.status == PluginInstallationStatus.UNINSTALLED
        with pytest.raises(InvalidTransitionError):
            install.enable()


# -- Credential ----------------------------------------------------------------------

class TestCredential:
    def test_rotation_cycle(self):
        cred = _credential()
        cred.begin_rotation()
        assert cred.status == CredentialStatus.ROTATING
        cred.complete_rotation()
        assert cred.status == CredentialStatus.ACTIVE
        assert cred.rotated_at is not None

    def test_check_expiry_transitions_to_expired(self):
        from datetime import datetime, timedelta, timezone
        cred = _credential(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        expired_now = cred.check_expiry()
        assert expired_now is True
        assert cred.status == CredentialStatus.EXPIRED

    def test_check_expiry_idempotent(self):
        from datetime import datetime, timedelta, timezone
        cred = _credential(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        cred.check_expiry()
        assert cred.check_expiry() is False  # already expired, second sweep call is a no-op

    def test_check_expiry_handles_naive_datetime_from_db_roundtrip(self):
        from datetime import datetime, timedelta
        cred = _credential(expires_at=datetime.utcnow() - timedelta(seconds=1))  # naive, as SQLite would return
        assert cred.check_expiry() is True

    def test_revoke_terminal(self):
        cred = _credential()
        cred.revoke()
        assert cred.status == CredentialStatus.REVOKED
        with pytest.raises(InvalidTransitionError):
            cred.begin_rotation()


# -- Schedule ------------------------------------------------------------------------

class TestSchedule:
    def test_pause_resume(self):
        schedule = _schedule()
        schedule.pause()
        assert schedule.status == ScheduleStatus.PAUSED
        schedule.resume()
        assert schedule.status == ScheduleStatus.ACTIVE

    def test_record_run_one_shot_completes(self):
        schedule = _schedule()
        schedule.record_run(next_run_at=None)
        assert schedule.status == ScheduleStatus.COMPLETED
        assert schedule.run_count == 1

    def test_record_run_recurring_stays_active(self):
        from datetime import datetime, timedelta, timezone
        schedule = _schedule()
        next_run = datetime.now(timezone.utc) + timedelta(hours=1)
        schedule.record_run(next_run_at=next_run)
        assert schedule.status == ScheduleStatus.ACTIVE
        assert schedule.next_run_at == next_run

    def test_record_run_requires_active(self):
        schedule = _schedule()
        schedule.pause()
        with pytest.raises(InvalidTransitionError):
            schedule.record_run(next_run_at=None)
