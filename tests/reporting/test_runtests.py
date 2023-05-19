# type: ignore
# flake8: noqa
import pytest


def test_ok():
    assert 1 == 1


def test_failure():
    assert 1 == 2


def test_unbound_local_error():
    a += "1"


def test_index_error():
    a = []
    a[1] = 1
