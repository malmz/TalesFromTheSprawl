import logging

cmd_logger = None

messages_logpath = "config/messages.log"
bot_logpath = "config/bot.log"


def setup_command_logger():
    global cmd_logger
    logpath = "logs/all_commands.log"
    cmd_logger = logging.getLogger("log")
    cmd_logger.setLevel(logging.INFO)
    ch = logging.FileHandler(logpath)
    ch.setFormatter(logging.Formatter("%(message)s"))
    cmd_logger.addHandler(ch)


def log_command(author_id, player_name, channel, content):
    cmd_logger.info("%s : %s : %s : %s" % (author_id, player_name, channel, content))


def failed_to_log():
    cmd_logger.warn("Failed to log command (something went wrong)")


def init_message_logger() -> logging.Logger:
    logger = logging.getLogger("messages")

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    fh = logging.FileHandler(messages_logpath)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def init_bot_logger() -> logging.Logger:
    logger = logging.getLogger("bot")

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    fh = logging.FileHandler(bot_logpath)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger
