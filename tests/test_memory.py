import logging

import cv2
import pytest

from wardogs_spotter import memory
from wardogs_spotter.memory import OutOfMemoryGuard, is_out_of_memory


def cv_error(code: int) -> cv2.error:
    error = cv2.error("allocation failed")
    error.code = code
    return error


def test_recognizes_out_of_memory_from_numpy_and_opencv():
    assert is_out_of_memory(MemoryError())
    assert is_out_of_memory(cv_error(-4))
    assert not is_out_of_memory(cv_error(-215))  # an assertion failure is a bug, not memory
    assert not is_out_of_memory(ValueError())


def test_guard_swallows_out_of_memory_and_says_so():
    with OutOfMemoryGuard() as guard:
        raise MemoryError
    assert guard.tripped


def test_guard_is_quiet_when_nothing_fails():
    with OutOfMemoryGuard() as guard:
        pass
    assert not guard.tripped


def test_guard_lets_other_errors_through():
    with pytest.raises(ZeroDivisionError), OutOfMemoryGuard():
        1 / 0  # noqa: B018


def test_warns_once_per_interval(caplog, monkeypatch):
    monkeypatch.setattr(memory, "_last_warning", float("-inf"))
    with caplog.at_level(logging.WARNING, logger="wardogs_spotter.memory"):
        for _ in range(3):
            with OutOfMemoryGuard():
                raise MemoryError
    assert len(caplog.records) == 1
