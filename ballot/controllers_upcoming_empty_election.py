# ballot/controllers_upcoming_empty_election.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from election.models import ElectionManager
from voter.constants import MINIMUM_ADDRESS_LENGTH_TO_HAVE_STREET_ADDRESS
from voter.models import VoterAddressManager
import wevote_functions.admin
from wevote_functions.functions import extract_state_code_from_address_string, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def retrieve_next_election_from_this_state(
        voter_device_link=None,
        voter_address=None
):
    election_day_text = ''
    election_description_text = ''
    google_civic_election_id = 0
    status = ''
    voter_address_manager = VoterAddressManager()

    # Retrieve the voter_address if its missing
    voter_address_exists = \
        voter_address and hasattr(voter_address, 'voter_id') and positive_value_exists(voter_address.voter_id)
    if not voter_address_exists:
        # Get the voter_id from the voter_device_link
        voter_id = voter_device_link.voter_id if hasattr(voter_device_link, 'voter_id') else 0
        if positive_value_exists(voter_id):
            voter_address_results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
            if voter_address_results['voter_address_found']:
                voter_address = voter_address_results['voter_address']
            else:
                voter_address = None
        voter_address_exists = \
            voter_address and hasattr(voter_address, 'voter_id') and positive_value_exists(voter_address.voter_id)
    text_for_map_search = voter_address.text_for_map_search if voter_address_exists else ''
    text_for_map_search_too_short = True
    if positive_value_exists(text_for_map_search):
        state_code = extract_state_code_from_address_string(text_for_map_search)

        length_of_text_for_map_search = 0
        if isinstance(text_for_map_search, str):
            length_of_text_for_map_search = len(text_for_map_search)
        text_for_map_search_too_short = length_of_text_for_map_search <= MINIMUM_ADDRESS_LENGTH_TO_HAVE_STREET_ADDRESS
    else:
        state_code = ''

    if positive_value_exists(state_code):
        election_manager = ElectionManager()
        election_results = election_manager.retrieve_next_election_for_state(
            state_code, require_include_in_list_for_voters=True)
        if election_results['election_found']:
            election = election_results['election']
            google_civic_election_id = election.google_civic_election_id
            election_day_text = election.election_day_text
            election_description_text = election.election_name
            status += "NEXT_ELECTION_FOUND_FOR_STATE: " + str(google_civic_election_id) + " "
    json_data = {
        'status':                   status,
        'success':                  True,
        'ballot_item_list':         [],
        'ballot_item_list_found':   False,
        'candidate_position_list':  [],
        'election_day_text':        election_day_text,
        'election_description_text': election_description_text,
        'google_civic_election_id': google_civic_election_id,
        'state_code':               state_code,
        'text_for_map_search':      text_for_map_search,
        'text_for_map_search_too_short': text_for_map_search_too_short,
        'use_election_without_ballot_data': True,
        'voter_ballot_saved':       None,
        'voter_ballot_saved_found': False,
    }
    return json_data
