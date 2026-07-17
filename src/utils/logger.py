"""Project logger.

Attaches its own stderr handler per logger so messages show up even under
`streamlit run`, which pre-configures root logging and would otherwise swallow
our INFO output.
"""

from __future__ import annotations

import logging

from ..config import settings

_FORMATTER = logging.Formatter(
    "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s", datefmt="%H:%M:%S"
)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_FORMATTER)
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(settings.log_level.upper())
    return logger
