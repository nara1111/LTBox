import logging
import sys
from contextlib import contextmanager
from typing import Optional

try:
    import colorama

    colorama.init()
except ImportError:
    pass

LOGGER_NAME = "ltbox"
_logger = logging.getLogger(LOGGER_NAME)
_logger.setLevel(logging.INFO)


class ColoredConsoleFormatter(logging.Formatter):
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        stripped_msg = msg.lstrip()

        if stripped_msg.startswith("[+]"):
            return f"{self.GREEN}{msg}{self.RESET}"
        elif stripped_msg.startswith("[*]"):
            return f"{self.CYAN}{msg}{self.RESET}"
        elif stripped_msg.startswith("[!]"):
            return (
                f"{self.RED}{msg}{self.RESET}"
                if record.levelno >= logging.ERROR
                else f"{self.YELLOW}{msg}{self.RESET}"
            )
        elif record.levelno >= logging.ERROR:
            return f"{self.RED}{msg}{self.RESET}"
        return msg


if not _logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColoredConsoleFormatter("%(message)s"))
    _logger.addHandler(console_handler)


def get_logger() -> logging.Logger:
    return _logger


@contextmanager
def logging_context(log_filename: Optional[str] = None):
    handlers_to_remove = []

    has_file_handler = any(isinstance(h, logging.FileHandler) for h in _logger.handlers)

    try:
        if log_filename and not has_file_handler:
            file_handler = logging.FileHandler(log_filename, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(message)s", datefmt="%H:%M:%S")
            )
            _logger.addHandler(file_handler)
            handlers_to_remove.append(file_handler)

        yield _logger

    finally:
        for handler in handlers_to_remove:
            handler.close()
            _logger.removeHandler(handler)
