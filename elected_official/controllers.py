# elected_official/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from .models import ElectedOfficial

logger = wevote_functions.admin.get_logger(__name__)


def move_elected_officials_to_another_politician(
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
    elected_officials_entries_moved = 0

    if positive_value_exists(from_politician_we_vote_id):
        try:
            elected_officials_entries_moved += ElectedOfficial.objects \
                .filter(politician_we_vote_id__iexact=from_politician_we_vote_id) \
                .update(politician_id=to_politician_id,
                        politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_ELECTED_OFFICIALS_BY_POLITICIAN_WE_VOTE_ID: " + str(e) + " "
            success = False

    if positive_value_exists(from_politician_id):
        try:
            elected_officials_entries_moved += ElectedOfficial.objects \
                .filter(politician_id=from_politician_id) \
                .update(politician_id=to_politician_id,
                        politician_we_vote_id=to_politician_we_vote_id)
        except Exception as e:
            status += "FAILED_MOVE_ELECTED_OFFICIALS_BY_POLITICIAN_ID: " + str(e) + " "
            success = False

    results = {
        'status':                           status,
        'success':                          success,
        'elected_officials_entries_moved':  elected_officials_entries_moved,
    }
    return results
