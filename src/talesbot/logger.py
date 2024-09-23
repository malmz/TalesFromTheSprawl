import logging
import logging.config
from typing import Any

LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "console": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "full": {
            "format": "%(asctime)s %(levelname)-8s %(name)-15s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "messages": {
            "format": "%(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "console",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "formatter": "full",
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
            "level": "DEBUG",
            "propagate": False,
        },
        "talesbot.messages": {
            "handlers": ["messages"],
            "level": "INFO",
            "propagate": False,
        },
        # "discord.client": {"handlers": ["default"], "level": "DEBUG"},
    },
}


def init_loggers():
    logging.config.dictConfig(LOGGING_CONFIG)
