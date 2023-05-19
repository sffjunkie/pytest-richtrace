# type: ignore
# flake8: noqa
import pytest


# xfail
@pytest.mark.xfail
def test_xfailed():
    a[0] == 12


# xfail
@pytest.mark.xfail(reason="On purpose")
def test_xfailed_with_reason():
    a[0] == 12


# xfail
@pytest.mark.xfail(reason="On purpose", raises=IndexError)
def test_xfailed_raises_with_reason():
    a = [1]
    a[1] == 12


# xfail
@pytest.mark.xfail(raises=IndexError)
def test_xfailed_with_matching_raises():
    a = [1]
    a[1] == 12


# failed
@pytest.mark.xfail(raises=SyntaxError)
def test_xfailed_with_raises_incorrect_exception():
    a = [1]
    a[1] == 12
