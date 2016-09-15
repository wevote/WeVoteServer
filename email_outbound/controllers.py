# email_outbound/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
import copy
from exception.models import handle_record_found_more_than_one_exception
from position.models import PositionManager, PERCENT_RATING
import requests
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

