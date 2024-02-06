import logging


def init_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')


class LoggingContext:

    def __init__(self, entry_msg=None, success_msg=None, failure_msg=None, exit_msg=None, logger=None,
                 entry_level=logging.DEBUG, exit_level=logging.DEBUG,
                 success_level=logging.INFO, failure_level=logging.ERROR):
        self.entry_msg = entry_msg
        self.success_msg = success_msg
        self.failure_msg = failure_msg
        self.exit_msg = exit_msg
        self.logger = logger or logging.getLogger(__name__)
        self.entry_level = entry_level
        self.exit_level = exit_level
        self.success_level = success_level
        self.failure_level = failure_level

    def __enter__(self):
        self.log(self.entry_msg, level=self.entry_level)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.log(self.success_msg, level=self.success_level)
        else:
            self.log(self.failure_msg, level=self.failure_level)

        self.log(self.exit_msg, level=self.exit_level)

    def log(self, message, level=logging.INFO):
        if message:
            self.logger.log(level, message)
