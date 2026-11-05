"""Structured logging configuration for Gadispot backend."""

import json
import logging
import re
import sys
from typing import Any

# Regex patterns for sensitive field redaction
SENSITIVE_KEYS = re.compile(
    r"(password|token|secret|authorization|api[-_]?key|credit[-_]?card|cvv|access[-_]?token|refresh[-_]?token)",
    re.IGNORECASE,
)
REDACTED_STRING = "[REDACTED]"


class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs sensitive credentials from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = self._redact_string(record.msg)
        if isinstance(record.args, dict):
            record.args = self._redact_dict(record.args)
        elif isinstance(record.args, tuple):
            record.args = tuple(self._redact_string(str(arg)) if isinstance(arg, str) else arg for arg in record.args)
        return True

    def _redact_string(self, text: str) -> str:
        # Mask bearer tokens
        text = re.sub(
            r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*",
            r"\1" + REDACTED_STRING,
            text,
            flags=re.IGNORECASE,
        )
        return text

    def _redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}
        for k, v in data.items():
            if SENSITIVE_KEYS.search(str(k)):
                cleaned[k] = REDACTED_STRING
            elif isinstance(v, dict):
                cleaned[k] = self._redact_dict(v)
            elif isinstance(v, str):
                cleaned[k] = self._redact_string(v)
            else:
                cleaned[k] = v
        return cleaned


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter for production and cloud-native observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include request_id if present in extra
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logging(log_level: str = "INFO", use_json: bool = False) -> None:
    """Initialize structured logging across the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.addFilter(SensitiveDataFilter())

    if use_json:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Silence overly verbose external loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


# Default package logger
logger = logging.getLogger("gadispot")
