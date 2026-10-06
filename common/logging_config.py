"""
Structured, JSON-lines tracing for every Tool, Resource, and Prompt in the
MCP server layer.

    @trace(logger)
    def my_tool(...): ...

    @trace(logger, redact=redact_for_logging)
    def my_tool_with_pii_args(...): ...

Produces exactly one JSON object per log line:

  ENTER  (DEBUG) -- fully-qualified function name, call_id, bound args
  EXIT   (DEBUG) -- same call_id, duration_ms, truncated return preview
  FAILED (ERROR) -- same call_id, duration_ms, exception type, full
                    traceback -- then the original exception is re-raised

LOG_LEVEL is read from the environment and defaults to DEBUG.
"""
from __future__ import annotations

import functools
import inspect
import json
import logging
import os
import sys
import time
import traceback
import uuid
from typing import Callable

LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG").upper()

_PREVIEW_MAX_CHARS = 400


def get_logger(name: str) -> logging.Logger:
    """
    One structured-JSON stdout logger per server/module. Safe to call
    multiple times with the same name (handlers are only attached once).
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(LOG_LEVEL)
    return logger


def _preview(value, max_chars: int = _PREVIEW_MAX_CHARS) -> str:
    try:
        text = json.dumps(value, default=str)
    except TypeError:
        text = repr(value)
    return text if len(text) <= max_chars else text[: max_chars - 15] + "...(truncated)"


def _bind_arguments(func: Callable, args: tuple, kwargs: dict) -> dict:
    try:
        bound = inspect.signature(func).bind_partial(*args, **kwargs)
        return dict(bound.arguments)
    except TypeError:
        # Fall back to something always loggable rather than failing tracing.
        return {"args": list(args), "kwargs": dict(kwargs)}


def _emit(logger: logging.Logger, level: str, payload: dict) -> None:
    line = json.dumps(payload, default=str)
    getattr(logger, level.lower())(line)


def trace(logger: logging.Logger, redact: Callable[[dict], dict] | None = None):
    """
    Decorator factory. `redact`, if provided, is applied to the bound
    ENTER argument dict and to the EXIT return value when the return
    value is itself a dict (tool/resource responses in this codebase are
    always plain dicts, so this covers every real case without guessing
    at arbitrary object shapes).
    """

    def decorator(func: Callable) -> Callable:
        qualname = getattr(func, "__qualname__", func.__name__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            call_id = uuid.uuid4().hex[:12]
            bound_args = _bind_arguments(func, args, kwargs)
            logged_args = redact(bound_args) if redact else bound_args
            _emit(
                logger,
                "DEBUG",
                {
                    "event": "ENTER",
                    "function": qualname,
                    "call_id": call_id,
                    "args": {k: _preview(v) for k, v in logged_args.items()},
                },
            )

            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                duration_ms = round((time.perf_counter() - start) * 1000, 3)
                _emit(
                    logger,
                    "ERROR",
                    {
                        "event": "FAILED",
                        "function": qualname,
                        "call_id": call_id,
                        "duration_ms": duration_ms,
                        "exception_type": type(exc).__name__,
                        "traceback": traceback.format_exc(),
                    },
                )
                raise

            duration_ms = round((time.perf_counter() - start) * 1000, 3)
            logged_result = redact(result) if (redact and isinstance(result, dict)) else result
            _emit(
                logger,
                "DEBUG",
                {
                    "event": "EXIT",
                    "function": qualname,
                    "call_id": call_id,
                    "duration_ms": duration_ms,
                    "return_preview": _preview(logged_result),
                },
            )
            return result

        return wrapper

    return decorator
