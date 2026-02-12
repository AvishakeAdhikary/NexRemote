"""
Logger configuration using Loguru
"""
from loguru import logger
import sys
from pathlib import Path

def setup_logger():
    """Setup loguru logger with file and console output"""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler with colors
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Add file handler with rotation
    log_dir = Path('./data/logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger.add(
        log_dir / 'nexremote.log',
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG"
    )
    
    logger.info("Logger initialized")
    return logger

def get_logger(name: str):
    """Get logger instance for module"""
    return logger.bind(name=name)

# Initialize on import
setup_logger()