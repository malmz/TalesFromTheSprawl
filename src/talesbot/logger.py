import logging

cmd_logger = None


def setup_command_logger():
    global cmd_logger
    logpath = "config/logs/all_commands.log"
    cmd_logger = logging.getLogger("log")
    cmd_logger.setLevel(logging.INFO)
    ch = logging.FileHandler(logpath)
    ch.setFormatter(logging.Formatter("%(message)s"))
    cmd_logger.addHandler(ch)


def log_command(author_id, player_name, channel, content):
    cmd_logger.info(f"{author_id} : {player_name} : {channel} : {content}")


def failed_to_log():
    cmd_logger.warn("Failed to log command (something went wrong)")
