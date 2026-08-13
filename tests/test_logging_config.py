from __future__ import annotations

import logging

from logging_config import configure_logging


def _reset_root_logger():
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)


def test_configure_logging_adds_a_stream_handler():
    _reset_root_logger()

    configure_logging()

    root = logging.getLogger()
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)


def test_configure_logging_sets_the_requested_level():
    _reset_root_logger()

    configure_logging(level=logging.WARNING)

    assert logging.getLogger().level == logging.WARNING


def test_configure_logging_is_idempotent():
    _reset_root_logger()

    configure_logging()
    handler_count_after_first = len(logging.getLogger().handlers)
    configure_logging()

    assert len(logging.getLogger().handlers) == handler_count_after_first


def test_a_module_logger_actually_emits_through_the_configured_handler(capsys):
    _reset_root_logger()
    configure_logging(level=logging.INFO)

    logging.getLogger("some.module").info("hello from a module logger")

    captured = capsys.readouterr()
    assert "hello from a module logger" in captured.err
