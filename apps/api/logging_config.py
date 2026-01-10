"""
Logging configuration for RecipeNow API.
Sets up structured logging with file and console outputs.
"""
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Create logs directory if it doesn't exist
LOG_DIR = Path("/var/log/recipe-now") if Path("/var").exists() else Path("./logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log file paths
ACCESS_LOG_FILE = LOG_DIR / "access.log"
ERROR_LOG_FILE = LOG_DIR / "error.log"
APP_LOG_FILE = LOG_DIR / "app.log"

# Log format
DETAILED_FORMAT = "%(asctime)s [%(name)s:%(lineno)d] %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s - %(message)s"


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string to logging level
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything at root level

    # Console handler (stdout for INFO+, stderr for errors)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(SIMPLE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Application log file handler (rotating)
    try:
        app_handler = RotatingFileHandler(
            APP_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        app_handler.setLevel(logging.DEBUG)
        app_formatter = logging.Formatter(DETAILED_FORMAT)
        app_handler.setFormatter(app_formatter)
        root_logger.addHandler(app_handler)
    except Exception as e:
        print(f"Warning: Could not setup app log file: {e}")

    # Error log file handler (rotating)
    try:
        error_handler = RotatingFileHandler(
            ERROR_LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(DETAILED_FORMAT)
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
    except Exception as e:
        print(f"Warning: Could not setup error log file: {e}")

    # Set specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)
