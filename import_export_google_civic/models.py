# import_export_google_civic/models.py
# Brought to you by We Vote. Be good.
# https://developers.google.com/resources/api-libraries/documentation/civicinfo/v2/python/latest/civicinfo_v2.elections.html
# -*- coding: UTF-8 -*-

from ballot.models import BallotItem
import wevote_functions.admin
from wevote_functions.models import positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)


def retrieve_google_civic_election_id_for_voter(voter_id):
    """
    Grab the first ballot_item we can find for this voter and return the google_civic_election_id
    """
    google_civic_election_id = 0
    success = False

    if positive_value_exists(voter_id):
        try:
            ballot_item_query = BallotItem.objects.filter(
                voter_id__exact=voter_id,
            )
            ballot_item_list = list(ballot_item_query[:1])
            if ballot_item_list:
                one_ballot_item = ballot_item_list[0]
                google_civic_election_id = one_ballot_item.google_civic_election_id
                success = True
        except BallotItem.DoesNotExist:
            pass

    results = {
        'success': success,
        'google_civic_election_id': google_civic_election_id,
    }
    return results


def fetch_google_civic_election_id_for_voter_id(voter_id):
    # Look to see if we have ballot_items stored for this voter and pull google_civic_election_id from that
    results = retrieve_google_civic_election_id_for_voter(voter_id)
    if results['success']:
        google_civic_election_id = results['google_civic_election_id']
    else:
        google_civic_election_id = 0

    return google_civic_election_id
