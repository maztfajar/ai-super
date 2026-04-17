import logging
from logging.handlers import RotatingFileHandler
import structlog
from core.config import settings
from pathlib import Path


def setup_logging():
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "IMPORTANT": logging.WARNING,
        "ERROR": logging.ERROR
    }
    log_level = level_map.get(settings.LOG_LEVEL.upper(), logging.INFO)
    log_format = "%(asctime)s %(levelname)s %(message)s"
    formatter = logging.Formatter(log_format)

    # Root logger
    root = logging.getLogger()
    root.setLevel(log_level)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File handler — RotatingFileHandler: 5MB max, keep 3 backups
    file_handler = RotatingFileHandler(
        str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
