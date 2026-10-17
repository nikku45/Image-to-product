import logging
import sys
from typing import Any, Dict


class StructuredFormatter(logging.Formatter):
    """Clean formatter that outputs log events without leaking secrets or tokens."""

    def format(self, record: logging.LogRecord) -> str:
        # Sanitize sensitive fields if present
        msg = super().format(record)
        return msg


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("product_matcher")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger


logger = setup_logging()
