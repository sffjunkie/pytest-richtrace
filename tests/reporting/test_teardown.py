# type: ignore
# flake8: noqa
import pytest


@pytest.mark.class_marker
class TestTeardownFailure:
    def teardown_method(self, method):
        a[0] = 666
