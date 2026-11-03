from identity_platform.security.encryption import SecretsEncryptor
from identity_platform.security.hashing import hash_password, verify_password
from identity_platform.security.tokens import generate_numeric_code, generate_raw_token, hash_token
from identity_platform.security.totp import generate_totp, generate_totp_secret, provisioning_uri, verify_totp


def test_hash_password_roundtrip():
    encoded = hash_password("Sup3r$ecretPass!")
    assert verify_password("Sup3r$ecretPass!", encoded)
    assert not verify_password("wrong-password", encoded)


def test_hash_password_unique_salts():
    a = hash_password("same-password-123!")
    b = hash_password("same-password-123!")
    assert a != b  # random salt each time


def test_verify_password_rejects_malformed_hash():
    assert not verify_password("anything", "not-a-valid-hash")


def test_generate_raw_token_is_unique_and_hash_is_deterministic():
    a = generate_raw_token()
    b = generate_raw_token()
    assert a != b
    assert hash_token(a) == hash_token(a)
    assert hash_token(a) != hash_token(b)


def test_generate_numeric_code_has_requested_digit_count():
    code = generate_numeric_code(digits=6)
    assert len(code) == 6
    assert code.isdigit()


def test_encrypt_decrypt_roundtrip():
    encryptor = SecretsEncryptor("x" * 32)
    ciphertext = encryptor.encrypt("super-secret-totp-seed")
    assert ciphertext != "super-secret-totp-seed"
    assert encryptor.decrypt(ciphertext) == "super-secret-totp-seed"


def test_totp_generate_and_verify_same_step():
    secret = generate_totp_secret()
    code = generate_totp(secret, timestamp=1_700_000_000)
    assert len(code) == 6
    assert verify_totp(secret, code, timestamp=1_700_000_000)


def test_totp_rejects_wrong_code():
    secret = generate_totp_secret()
    correct = generate_totp(secret, timestamp=1_700_000_000)
    wrong = "0" * 6 if correct != "0" * 6 else "1" * 6
    assert not verify_totp(secret, wrong, timestamp=1_700_000_000)


def test_totp_tolerates_one_step_drift():
    secret = generate_totp_secret()
    code = generate_totp(secret, timestamp=1_700_000_000)
    # one period (30s) later, still within the default valid_window=1
    assert verify_totp(secret, code, timestamp=1_700_000_030)


def test_totp_rejects_far_future_code():
    secret = generate_totp_secret()
    code = generate_totp(secret, timestamp=1_700_000_000)
    assert not verify_totp(secret, code, timestamp=1_700_001_000)


def test_provisioning_uri_contains_secret_and_issuer():
    secret = generate_totp_secret()
    uri = provisioning_uri(secret, account_name="jane@example.com", issuer="AIOS")
    assert uri.startswith("otpauth://totp/")
    assert secret in uri
    assert "issuer=AIOS" in uri
