"""
Structured JSON logging setup for DocHub AI Backend.
"""

import json
import logging
import sys
from datetime import datetime, timezone


class _JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON for CloudWatch / any log aggregator."""

    _SKIP = frozenset({
        "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created",
        "msecs", "relativeCreated", "thread", "threadName", "processName",
        "process", "name", "message",
    })

    def format(self, record: logging.LogRecord) -> str:
        log: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log["exception"] = self.formatException(record.exc_info)
        # Append any extra= fields passed by callers
        for key, val in record.__dict__.items():
            if key not in self._SKIP:
                log[key] = val
        return json.dumps(log, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON output to stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JSONFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # Quieten noisy third-party loggers
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
