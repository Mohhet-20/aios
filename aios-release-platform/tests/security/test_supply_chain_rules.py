from release_platform.security.supply_chain_rules import compute_checksum, verify_checksum


def test_compute_checksum_deterministic():
    data = b"hello world"
    assert compute_checksum(data) == compute_checksum(data)


def test_verify_checksum_matches():
    data = b"artifact-bytes"
    checksum = compute_checksum(data)
    assert verify_checksum(data, expected=checksum) is True


def test_verify_checksum_rejects_tampered_data():
    data = b"artifact-bytes"
    checksum = compute_checksum(data)
    assert verify_checksum(b"tampered-bytes", expected=checksum) is False


def test_compute_checksum_supports_other_algorithms():
    data = b"hello"
    sha1 = compute_checksum(data, algorithm="sha1")
    sha256 = compute_checksum(data, algorithm="sha256")
    assert sha1 != sha256
    assert len(sha1) == 40
    assert len(sha256) == 64
