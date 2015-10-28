# admin_tools/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.controllers import candidates_import_from_sample_file
from election.controllers import elections_import_from_sample_file
from office.controllers import offices_import_from_sample_file
from organization.controllers import organizations_import_from_sample_file
from position.controllers import positions_import_from_sample_file
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def import_data_for_tests():

    # Import election data from We Vote export file
    elections_import_from_sample_file()

    # Import ContestOffices
    offices_import_from_sample_file()

    # Import candidate data from We Vote export file
    candidates_import_from_sample_file()

    # Import ContestMeasures

    # Import organization data from We Vote export file
    organizations_import_from_sample_file()

    # Import positions data from We Vote export file
    positions_import_from_sample_file()

    return
