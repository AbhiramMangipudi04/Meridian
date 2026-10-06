from __future__ import annotations

import json

import pytest

from common.guardrails import redact_for_logging
from common.logging_config import get_logger, trace


@pytest.fixture()
def logger():
    return get_logger("test_logging_config_module")


def test_enter_and_exit_lines_are_emitted(capfd, logger):
    @trace(logger)
    def add(a, b):
        return a + b

    result = add(2, 3)
    assert result == 5

    lines = [json.loads(l) for l in capfd.readouterr().out.strip().splitlines()]
    events = [l["event"] for l in lines]
    assert events == ["ENTER", "EXIT"]


def test_enter_line_has_required_fields(capfd, logger):
    @trace(logger)
    def greet(name):
        return f"hello {name}"

    greet("Arjun")
    lines = [json.loads(l) for l in capfd.readouterr().out.strip().splitlines()]
    enter = lines[0]
    assert enter["event"] == "ENTER"
    assert enter["function"].endswith("greet")
    assert "call_id" in enter and enter["call_id"]
    assert enter["args"]["name"] == '"Arjun"'


def test_exit_line_has_duration_and_call_id_matching_enter(capfd, logger):
    @trace(logger)
    def noop():
        return None

    noop()
    lines = [json.loads(l) for l in capfd.readouterr().out.strip().splitlines()]
    enter, exit_ = lines
    assert enter["call_id"] == exit_["call_id"]
    assert "duration_ms" in exit_
    assert exit_["duration_ms"] >= 0


def test_failed_line_has_exception_type_and_traceback_then_reraises(capfd, logger):
    @trace(logger)
    def boom():
        raise RuntimeError("kaboom")

    with pytest.raises(RuntimeError):
        boom()

    lines = [json.loads(l) for l in capfd.readouterr().out.strip().splitlines()]
    enter, failed = lines
    assert failed["event"] == "FAILED"
    assert failed["call_id"] == enter["call_id"]
    assert failed["exception_type"] == "RuntimeError"
    assert "Traceback" in failed["traceback"]
    assert "kaboom" in failed["traceback"]
    assert "duration_ms" in failed


def test_redact_applies_to_entered_arguments(capfd, logger):
    @trace(logger, redact=redact_for_logging)
    def lookup(account_id, phone):
        return {"account_id": account_id, "phone": phone}

    lookup(account_id="ACC-20077", phone="+91-9876543210")
    lines = [json.loads(l) for l in capfd.readouterr().out.strip().splitlines()]
    enter = lines[0]
    assert "ACC-20077" not in json.dumps(enter)
    assert "9876543210" not in json.dumps(enter)
    assert "****0077" in enter["args"]["account_id"]


def test_redact_applies_to_dict_return_value(capfd, logger):
    @trace(logger, redact=redact_for_logging)
    def lookup():
        return {"account_id": "ACC-20077", "status": "ACTIVE"}

    lookup()
    lines = [json.loads(l) for l in capfd.readouterr().out.strip().splitlines()]
    exit_line = lines[1]
    assert "ACC-20077" not in exit_line["return_preview"]
    assert "****0077" in exit_line["return_preview"]


def test_every_log_line_is_a_single_valid_json_object(capfd, logger):
    @trace(logger)
    def f(x):
        return x * 2

    f(21)
    raw_lines = capfd.readouterr().out.strip().splitlines()
    assert len(raw_lines) == 2
    for line in raw_lines:
        parsed = json.loads(line)  # raises if not valid JSON
        assert isinstance(parsed, dict)


def test_log_level_defaults_to_debug():
    import common.logging_config as logging_config

    assert logging_config.LOG_LEVEL == "DEBUG"
