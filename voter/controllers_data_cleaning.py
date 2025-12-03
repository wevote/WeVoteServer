# voter/controllers_data_cleaning.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from datetime import datetime

from django.db.models import Q
from config.base import get_environment_variable
from django.db.models.functions import Length

from politician.models import PoliticianManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_functions.functions_date import convert_we_vote_date_string_to_date_as_integer, \
    generate_localized_datetime_from_obj, get_current_year_as_integer
from .models import Voter

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def batch_process_maintenance_scripts_voter():
    status = ' :||: '
    success = True

    # ##################
    #
    # results = seo_friendly_path_updates(
    #     number_to_update=1000,
    # )
    # if positive_value_exists(results['status']):
    #     status += results['status'] + " :||: "

    results = {
        'status': status,
        'success': success,
    }
    return results
