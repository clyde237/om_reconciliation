"""Configuration du logging applicatif."""

import sys
from loguru import logger
from config.settings import LOG_LEVEL


def setup_logger():
    """Initialise le logger centralisé."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )
    return logger
