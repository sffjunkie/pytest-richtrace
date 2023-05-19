# type: ignore
# flake8: noqa
import pytest


@pytest.mark.skip(reason="skip: just because")
def test_skipped():
    assert 1 == 1


@pytest.mark.skipif(1 == 1, reason="skipif: ok")
def test_skipif():
    assert 1 == 1


@pytest.mark.skipif(1 == 2, reason="skipif: not ok")
def test_not_skipif():
    assert 1 == 1


@pytest.mark.skip(reason="skipped: just because")
@pytest.mark.skipif(1 == 1, reason="skipif: ok")
def test_skip_and_skipif():
    assert 1 == 1


@pytest.mark.skipif(1 == 1, reason="skipif: second overrides")
@pytest.mark.skip(reason="skipped: skip second overrides")
def test_skipif_and_skip():
    assert 1 == 1


@pytest.mark.skip(reason="skipped: skip first overrides")
@pytest.mark.skipif(1 == 2, reason="skipif: not ok")
def test_not_skipif_and_skip():
    assert 1 == 1


@pytest.mark.xfail
@pytest.mark.skipif(1 == 1, reason="Another reason")
def test_xfailed_with_skipif_that_passes():
    a[0] == 12
