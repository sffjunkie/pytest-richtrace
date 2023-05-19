# type: ignore
# flake8: noqa
import pytest


# xpass
@pytest.mark.xfail
def test_xpassed():
    assert 1 == 1


# xpass
@pytest.mark.xfail(raises=IndexError)
def test_xpassed_not_raises():
    assert 1 == 1


# xpass
@pytest.mark.xfail(raises=IndexError, reason="A reason")
def test_xpassed_not_raises_with_reason():
    assert 1 == 1
