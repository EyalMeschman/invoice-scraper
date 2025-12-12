import logging


class Logger:
    @staticmethod
    def create() -> logging.Logger:
        log = logging.getLogger(__name__)
        if not log.hasHandlers():
            formatter = logging.Formatter(
                "[%(asctime)s] p%(process)s {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
                "%m-%d %H:%M:%S",
            )
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)

            log.addHandler(console_handler)

        return log
