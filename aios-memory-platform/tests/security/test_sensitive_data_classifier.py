from memory_platform.domain.enums import SensitivityLevel
from memory_platform.security.sensitive_data_classifier import classify_sensitivity


def test_plain_text_is_internal():
    result = classify_sensitivity("The team meets every Tuesday at 10am.")
    assert result.level == SensitivityLevel.INTERNAL
    assert result.findings == []


def test_empty_text_is_public():
    result = classify_sensitivity("")
    assert result.level == SensitivityLevel.PUBLIC


def test_email_flags_confidential():
    result = classify_sensitivity("Please contact jane.doe@example.com about this.")
    assert result.level == SensitivityLevel.CONFIDENTIAL
    assert any(f.finding_type == "email" for f in result.findings)


def test_ssn_flags_restricted():
    result = classify_sensitivity("His SSN is 123-45-6789 on file.")
    assert result.level == SensitivityLevel.RESTRICTED
    assert any(f.finding_type == "ssn" for f in result.findings)


def test_aws_key_flags_restricted():
    result = classify_sensitivity("export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")
    assert result.level == SensitivityLevel.RESTRICTED
    assert any(f.finding_type == "aws_access_key" for f in result.findings)


def test_generic_api_key_flags_restricted():
    result = classify_sensitivity('api_key: "sk-th1sIsAFakeButLongEnoughSecret"')
    assert result.level == SensitivityLevel.RESTRICTED


def test_private_key_block_flags_restricted():
    result = classify_sensitivity("-----BEGIN RSA PRIVATE KEY-----\nMIIEow...\n-----END RSA PRIVATE KEY-----")
    assert result.level == SensitivityLevel.RESTRICTED


def test_match_preview_is_truncated_not_full_secret():
    result = classify_sensitivity("api_key: 'sk-th1sIsAFakeButLongEnoughSecretValue123456'")
    finding = next(f for f in result.findings if f.finding_type == "generic_api_key")
    assert "…" in finding.match_preview
    assert len(finding.match_preview) < 30
