import logging
import logging.config
from typing import Any

LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "messages": {
            "fmt": "%(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "config/logs/app.log",
        },
        "messages": {
            "formatter": "messages",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "config/logs/messages.log",
        },
    },
    "loggers": {
        "talesbot": {
            "handlers": ["default", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "talesbot.messages": {"handlers": ["messages"], "level": "INFO"},
    },
}


def init_loggers():
    logging.config.dictConfig(LOGGING_CONFIG)
