import pytest


def test_ok():
    assert 1 == 1


def test_failure():
    assert 1 == 2


def test_syntax_error():
    a += "1"


def test_index_error():
    a = []
    a[1] = 1


@pytest.fixture
def bad_fixture():
    a[0] = 1


def test_setup_bad_fixture_fails(bad_fixture):
    assert 1 == 1


@pytest.mark.skip(reason="just because")
def test_skipped():
    assert 1 == 1


class TestTeardownFailure:
    def teardown_method(self, method):
        a[0] = 1

    def test_class_method(self):
        assert 1 == 1
