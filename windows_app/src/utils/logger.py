"""
Logger configuration using Loguru.
Uses centralized path resolution for log file storage.
"""
from loguru import logger
import sys
from utils.paths import get_log_dir, is_frozen


def setup_logger():
    """Setup loguru logger with file and console output"""

    # Remove default handler
    logger.remove()

    # Console handler — only in dev mode (production is windowed, no console)
    if not is_frozen():
        logger.add(
            sys.stdout,
            colorize=True,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )

    # File handler with rotation — always active
    log_dir = get_log_dir()

    logger.add(
        log_dir / 'nexremote.log',
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )

    logger.info("Logger initialized")
    logger.info(f"Log directory: {log_dir}")
    return logger


def get_logger(name: str):
    """Get logger instance for module"""
    return logger.bind(name=name)