"""Structured JSON logging configuration.

Every log line includes the request id and tenant id (when available) so
that logs from the API, the Celery workers and the GPU worker fleet can be
correlated in a single trace across an asynchronous AI generation job.
"""

import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s " "%(request_id)s %(organization_id)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"},
        defaults={"request_id": "-", "organization_id": "-"},
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Quiet down noisy third-party loggers.
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
