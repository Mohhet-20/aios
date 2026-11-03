import pytest

from tool_platform.core.exceptions import NetworkPolicyViolationError
from tool_platform.domain.enums import SandboxNetworkPolicy
from tool_platform.sandbox.network_policy import NetworkPolicy


def test_deny_all_blocks_everything():
    policy = NetworkPolicy(policy_type=SandboxNetworkPolicy.DENY_ALL)
    with pytest.raises(NetworkPolicyViolationError):
        policy.check_url("https://api.github.com/repos")


def test_allow_all_permits_everything():
    policy = NetworkPolicy(policy_type=SandboxNetworkPolicy.ALLOW_ALL)
    policy.check_url("https://anything.example.com")  # no raise


def test_allow_list_exact_match():
    policy = NetworkPolicy(policy_type=SandboxNetworkPolicy.ALLOW_LIST, allowed_hosts=["api.github.com"])
    policy.check_url("https://api.github.com/repos")  # no raise
    with pytest.raises(NetworkPolicyViolationError):
        policy.check_url("https://evil.com/exfiltrate")


def test_allow_list_wildcard_subdomain():
    policy = NetworkPolicy(policy_type=SandboxNetworkPolicy.ALLOW_LIST, allowed_hosts=["*.slack.com"])
    policy.check_url("https://hooks.slack.com/services/x")  # no raise
    with pytest.raises(NetworkPolicyViolationError):
        policy.check_url("https://slack.com.evil.com/phish")


def test_allow_list_case_insensitive():
    policy = NetworkPolicy(policy_type=SandboxNetworkPolicy.ALLOW_LIST, allowed_hosts=["API.GitHub.com"])
    policy.check_url("https://api.github.com/repos")  # no raise
