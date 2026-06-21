from pathlib import Path

from loguru import logger

# Create logs directory
Path("logs").mkdir(exist_ok=True)

# Remove default logger
logger.remove()

# Console logging
logger.add(
    sink=lambda msg: print(msg, end=""),
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "{message}",
)

# File logging
logger.add(
    "logs/titan.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)

__all__ = ["logger"]
