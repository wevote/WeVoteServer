# exception/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import inspect
import wevote_functions.admin


default_logger = wevote_functions.admin.get_logger(__name__)


def _log_exception(exception_message, logger, e):
    """Log an exception with a custom message."""
    if logger is None:
        logger = default_logger

    caller_frame_record = inspect.stack()[2]
    frame = caller_frame_record[0]
    info = inspect.getframeinfo(frame)

    logger.error(e)
    logger.error("{message}, function: {function}, file: {filename}, line: {line}".format(
        message=exception_message,
        filename=info.filename,
        function=info.function,
        line=info.lineno))


def handle_exception(e, logger=None, exception_message=""):
    _log_exception(exception_message, logger, e)


def handle_record_not_deleted_exception(e, logger=None, exception_message_optional=""):
    exception_message = "Database record not deleted. " + exception_message_optional
    _log_exception(exception_message, logger, e)


def handle_record_not_found_exception(e, logger=None, exception_message_optional=""):
    exception_message = "Database record not found. " + exception_message_optional
    _log_exception(exception_message, logger, e)


def handle_record_found_more_than_one_exception(e, logger=None, exception_message_optional=""):
    exception_message = "More than one Database record found - only one expected. " + exception_message_optional
    _log_exception(exception_message, logger, e)


def handle_record_not_saved_exception(e, logger=None, exception_message_optional=""):
    exception_message = "Could not save. " + exception_message_optional
    _log_exception(exception_message, logger, e)


def print_to_log(logger=None, exception_message_optional=""):
    exception_message = "[PRINT_TO_LOG] " + exception_message_optional
    _log_print(exception_message, logger)


def _log_print(exception_message, logger):
    """Log an exception with a custom message."""
    if logger is None:
        logger = default_logger

    caller_frame_record = inspect.stack()[2]
    frame = caller_frame_record[0]
    info = inspect.getframeinfo(frame)

    logger.error("{message}, function: {function}, file: {filename}, line: {line}".format(
        message=exception_message,
        filename=info.filename,
        function=info.function,
        line=info.lineno))
