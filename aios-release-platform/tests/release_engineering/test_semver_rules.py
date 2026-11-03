import pytest

from release_platform.release_engineering.semver_rules import (
    InvalidSemVerError,
    compare_versions,
    is_compatible,
    parse_version,
)


def test_parse_version_basic():
    v = parse_version("2.10.4")
    assert (v.major, v.minor, v.patch) == (2, 10, 4)
    assert v.prerelease is None


def test_parse_version_with_prerelease_and_build():
    v = parse_version("1.2.3-rc.1+build.5")
    assert v.prerelease == "rc.1"
    assert v.build == "build.5"


def test_parse_version_rejects_invalid():
    with pytest.raises(InvalidSemVerError):
        parse_version("not-a-version")


def test_compare_versions_orders_by_number():
    assert compare_versions("1.2.3", "1.3.0") == -1
    assert compare_versions("2.0.0", "1.9.9") == 1
    assert compare_versions("1.0.0", "1.0.0") == 0


def test_compare_versions_stable_outranks_prerelease():
    assert compare_versions("1.2.3", "1.2.3-rc.1") == 1


def test_compare_versions_ignores_build_metadata():
    assert compare_versions("1.2.3+abc", "1.2.3+xyz") == 0


def test_is_compatible_within_range():
    assert is_compatible("1.5.0", compatible_from="1.0.0", compatible_to="2.0.0") is True


def test_is_compatible_below_range():
    assert is_compatible("0.9.0", compatible_from="1.0.0", compatible_to="2.0.0") is False


def test_is_compatible_above_range():
    assert is_compatible("2.5.0", compatible_from="1.0.0", compatible_to="2.0.0") is False


def test_is_compatible_no_upper_bound():
    assert is_compatible("99.0.0", compatible_from="1.0.0") is True
