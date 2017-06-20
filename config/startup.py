"""This should include methods that contain tasks that should be executed when
accessing the application.
"""

import wevote_functions.admin

from config import settings


# TODO: This gets called after all the individual "logger = wevote_functions.admin.get_logger(__name__)" are called
# It appears to have no effect on the LOG_FILE_LEVEL, so only ERROR logging works
def run():
    wevote_functions.admin.setup_logging(
        stream=settings.LOG_STREAM,
        logfile=settings.LOG_FILE,
        stream_level=settings.LOG_STREAM_LEVEL,
        file_level=settings.LOG_FILE_LEVEL
    )

    print('Running')
