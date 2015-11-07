"""This should include methods that contain tasks that should be executed when
accessing the application.
"""

import wevote_functions.admin

from config import settings


def run():
    wevote_functions.admin.setup_logging(
        stream=settings.LOG_STREAM,
        logfile=settings.LOG_FILE,
        stream_level=settings.LOG_STREAM_LEVEL,
        file_level=settings.LOG_FILE_LEVEL
    )

    print('Running')
