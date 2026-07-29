"""Structured JSON logging configuration.

Logs are emitted as one JSON object per line, which is what lets the API,
the Celery workers and the GPU worker fleet ship to the same log
aggregator and be queried/filtered consistently. Call sites that want a
request id or tenant id attached to a specific log line can pass
`extra={"request_id": ..., "organization_id": ...}` to that call; fields
that aren't provided simply don't appear in that line's JSON, rather than
every line carrying a placeholder value for context it doesn't have.
"""
import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Quiet down noisy third-party loggers.
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
