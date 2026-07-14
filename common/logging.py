"""Logging: structured JSON-ish lines, level from settings. All services log
to stdout so the ELK stack / Docker can aggregate them."""
from __future__ import annotations

import logging
import sys


def configure_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            f"%(asctime)s %(levelname)s [{service_name}] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger
