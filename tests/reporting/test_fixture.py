# type: ignore
# flake8: noqa
import pytest


@pytest.fixture
def bad_fixture():
    a[0] = 1


# failed
def test_setup_bad_fixture_fails(bad_fixture):
    assert 1 == 1
