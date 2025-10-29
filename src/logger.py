import logging


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[41m",  # Red background
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        levelname: str = record.levelname
        if levelname in self.COLORS:
            color = self.COLORS[levelname]
            record.levelname = f"{color}{levelname}{self.RESET}"
        return super().format(record)


def get_logger(name: str = "app_logger") -> logging.Logger:
    """
    Creates or returns already created logger.

    Args:
        name (str): Name of logger

    Returns:
        Logger.
    """
    logger: logging.Logger = logging.getLogger(name)

    if not logger.handlers:
        # Tracks any logger level from code
        logger.setLevel(logging.DEBUG)

        # Console handler
        console_handler: logging.StreamHandler = logging.StreamHandler()
        # To console only prints INFO and above
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ColorFormatter("[%(levelname)s] %(message)s"))
        logger.addHandler(console_handler)

    return logger
