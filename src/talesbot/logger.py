import logging


def init_loggers():
    logging.basicConfig("config/logs/app.log", level=logging.DEBUG)

    cmd_logger = logging.getLogger("talesbot.messages")
    cmd_handler = logging.FileHandler("config/logs/messages.log")
    cmd_handler.setFormatter(logging.Formatter("%(messages)s"))
    cmd_logger.addHandler(cmd_handler)
