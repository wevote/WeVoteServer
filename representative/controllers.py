# representative/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from .models import Representative

logger = wevote_functions.admin.get_logger(__name__)


def move_representatives_to_another_politician(
        from_politician_id=0,
        from_politician_we_vote_id='',
        to_politician_id=0,
        to_politician_we_vote_id=''):
    """

    :param from_politician_id:
    :param from_politician_we_vote_id:
    :param to_politician_id:
    :param to_politician_we_vote_id:
    :return:
    """
    status = ''
    success = True
    representatives_entries_moved = 0

    if positive_value_exists(from_politician_we_vote_id):
        try:
            representatives_entries_moved += Representative.objects \
                .filter(politician_we_vote_id__iexact=from_politician_we_vote_id) \
                .update(politician_id=to_politician_id,
                        politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_REPRESENTATIVES_BY_POLITICIAN_WE_VOTE_ID: " + str(e) + " "
            success = False

    if positive_value_exists(from_politician_id):
        try:
            representatives_entries_moved += Representative.objects \
                .filter(politician_id=from_politician_id) \
                .update(politician_id=to_politician_id,
                        politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_REPRESENTATIVES_BY_POLITICIAN_ID: " + str(e) + " "
            success = False

    results = {
        'status':                           status,
        'success':                          success,
        'representatives_entries_moved':  representatives_entries_moved,
    }
    return results
