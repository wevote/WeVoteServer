# wevote_functions/admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
"""Includes logging management methods. `setup_logging` should be called when
beginning execution. The `get_logger` method should always be used for fetching
log instances.
"""

import logging
import logging.handlers
import os
import socket
from config.base import get_environment_variable, convert_logging_level


_ch = None  # root stream handler.
_fh = None  # root file handler.
_only_log_once = None  # if LOG_FILE_LEVEL is misconfigured, only log that config error once per start-up of the server
host = socket.gethostname()



def _make_path(logfile):
    """Generates the string path `logfile` if it does not already exist.
    This will create directories-- make sure executing user has permissions.
    """
    filepath = os.path.dirname(logfile)
    if filepath and not os.path.exists(filepath):
        os.makedirs(filepath)


def get_logger(name):
    """Return a log instance.
    Stream/File handlers are added based on `setup_logging`.
    name parameter should be passed as `__name__`.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        if _ch:
            logger.addHandler(_ch)

        if _fh:
            logger.addHandler(_fh)

    if logger.level == 0:
        global _only_log_once
        environment_variable_log_level = get_environment_variable("LOG_FILE_LEVEL");
        if isinstance(environment_variable_log_level, str) and len(environment_variable_log_level):
            level = convert_logging_level(environment_variable_log_level)
            if isinstance(level, int):
                logger.level = level
            elif not _only_log_once:
                logger.error("LOG_FILE_LEVEL is invalid", {}, {})  # setup_logging hasn't run yet so just to the console
                _only_log_once = True
        elif not _only_log_once:
            logger.error("LOG_FILE_LEVEL is not set", {}, {})  # setup_logging() hasn't run yet, so just to the console
            _only_log_once = True

    return logger


def setup_logging(
        stream=True,
        logfile=None,
        stream_level=logging.INFO,
        file_level=logging.ERROR
    ):
    """Set-up format and verbosity.
    `stream` when True will turn on stream handler.
    `logfile` when passed (string path to log), file handler is activated.
    """
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] {0}:%(name)s: %(message)s".format(host)
    )

    if stream:
        global _ch
        _ch = logging.StreamHandler()
        _ch.setLevel(stream_level)
        _ch.setFormatter(formatter)
        logging.getLogger('').addHandler(_ch)

    if logfile:
        _make_path(logfile)

        global _fh
        _fh = logging.FileHandler(logfile)
        _fh.setLevel(file_level)
        _fh.setFormatter(formatter)
        logging.getLogger('').addHandler(_fh)
