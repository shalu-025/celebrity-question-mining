"""
Centralized Logging Utility
Provides file-based logging organized by date/time: Logging/{year}/{month}/{date}/log_{HH:MM}.log
All logs are also displayed on console
"""

import logging
import os
from datetime import datetime
from pathlib import Path


class DateTimeLogger:
    """
    Centralized logger that writes to date/time organized files
    File structure: Logging/{year}/{month}/{date}/log_{HH:MM}.log
    """

    _initialized = False
    _log_file_path = None

    @classmethod
    def setup_logging(cls, base_dir: str = "Logging", log_level: str = "INFO"):
        """
        Setup logging configuration with date/time organized files

        Args:
            base_dir: Base directory for logs (default: "Logging")
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if cls._initialized:
            return cls._log_file_path

        # Get current datetime
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        date = now.strftime("%d")
        time_str = now.strftime("%H:%M")

        # Create directory structure: Logging/{year}/{month}/{date}/
        log_dir = Path(base_dir) / year / month / date
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create log file: log_{HH:MM}.log
        log_filename = f"log_{time_str}.log"
        log_file_path = log_dir / log_filename
        cls._log_file_path = str(log_file_path)

        # Configure logging format
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        date_format = '%Y-%m-%d %H:%M:%S'

        # Convert log level string to logging constant
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)

        # Create formatters
        formatter = logging.Formatter(log_format, datefmt=date_format)

        # Get root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        # Remove existing handlers to avoid duplicates
        root_logger.handlers.clear()

        # Create file handler
        file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)

        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        cls._initialized = True

        # Log initialization message
        root_logger.info(f"Logging initialized. Log file: {log_file_path}")

        return str(log_file_path)

    @classmethod
    def get_log_file_path(cls):
        """Get the current log file path"""
        return cls._log_file_path


def get_logger(name: str = None, log_level: str = "INFO") -> logging.Logger:
    """
    Get a logger instance with centralized file logging

    Args:
        name: Logger name (typically __name__ of the module)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger instance

    Example:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("This will be logged to both console and file")
    """
    # Setup logging if not already done
    if not DateTimeLogger._initialized:
        DateTimeLogger.setup_logging(log_level=log_level)

    # Return logger for the specific module
    return logging.getLogger(name or __name__)


def get_current_log_file() -> str:
    """
    Get the path to the current log file

    Returns:
        String path to the current log file
    """
    if not DateTimeLogger._initialized:
        DateTimeLogger.setup_logging()

    return DateTimeLogger.get_log_file_path()


if __name__ == "__main__":
    # Test the logging system
    logger = get_logger("TestModule", log_level="DEBUG")

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    print(f"\nLog file created at: {get_current_log_file()}")
