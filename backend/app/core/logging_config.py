"""Centralised structured logging for IDTCC.

JSON logs in production (machine-parseable for Loki/ELK/CloudWatch),
human-readable console logs in development. A per-request correlation id is
attached via a contextvar so every agent log line can be traced back to the
simulation that produced it.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any

# Correlation id shared across a single simulation request.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_CONFIGURED = False


class _JsonFormatter(logging.Formatter):
    """Render log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts":      time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
            "request_id": request_id_var.get(),
        }
        # Promote any structured `extra={"fields": {...}}` payload.
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict):
            payload.update(fields)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class _ConsoleFormatter(logging.Formatter):
    """Readable single-line format for local development."""

    def format(self, record: logging.LogRecord) -> str:
        rid = request_id_var.get()
        rid_str = f" [{rid[:8]}]" if rid and rid != "-" else ""
        base = f"{self.formatTime(record, '%H:%M:%S')} {record.levelname:<7}{rid_str} {record.name}: {record.getMessage()}"
        fields = getattr(record, "fields", None)
        if isinstance(fields, dict) and fields:
            extras = " ".join(f"{k}={v}" for k, v in fields.items())
            base = f"{base} | {extras}"
        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"
        return base


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Idempotently configure the root logger. Call once on startup."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter() if json_logs else _ConsoleFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Tame noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "urllib3", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, msg: str, **fields: Any) -> None:
    """Emit a log line with structured fields.

    Example:
        log_event(log, logging.INFO, "agent.done", agent="weather", latency_ms=812)
    """
    logger.log(level, msg, extra={"fields": fields})
