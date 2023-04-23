# ballot/controllers_ballot_from_offices_held.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import BallotItem
from election.models import ElectionManager
from exception.models import handle_exception
from office.models import ContestOffice
from office_held.models import OfficeHeld, OfficeHeldManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def generate_ballot_data_from_offices_held(
        voter_device_link=None,
        google_civic_election_id='',
        voter_address=None):
    offices_held_for_location_id = ''
    status = ''
    success = True

    election_manager = ElectionManager()

    try:
        voter_device_id = voter_device_link.voter_device_id
        voter_id = voter_device_link.voter_id
    except Exception as e:
        status += "PROBLEM_WITH_VOTER_DEVICE_LINK_OBJECT: " + str(e) + " "
        voter_device_id = ''
        voter_id = 0

    voter_address_exists = \
        voter_address and hasattr(voter_address, 'voter_id') and positive_value_exists(voter_address.voter_id)

    if not positive_value_exists(voter_id):
        status += "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID "
        results = {
            'status':                   status,
            'success':                  False,
            'google_civic_election_id': google_civic_election_id,
            'offices_held_for_location_id': offices_held_for_location_id,
            'state_code':               '',
            'use_office_held_ballot':   False,
            'voter_ballot_saved':       None,
            'voter_ballot_saved_found': False,
        }
        return results

    text_for_map_search = voter_address.text_for_map_search if voter_address_exists else ''

    if positive_value_exists(google_civic_election_id):
        # If a specific google_civic_election_id came in, we need to return a ballot in that particular election,
        # even if it isn't an election the voter has seen before.
        text_for_map_search_for_google_civic_retrieve = ""
        # Is the voter's address in a particular state?
        if voter_address_exists:
            state_code_from_text_for_map_search = voter_address.get_state_code_from_text_for_map_search()
        else:
            state_code_from_text_for_map_search = ''
        if positive_value_exists(state_code_from_text_for_map_search):
            # If the voter address is for another state, then remove
            election_results = election_manager.retrieve_election(google_civic_election_id)
            if election_results['election_found']:
                election = election_results['election']
                # If the voter's address is in a state supported by this election, pass in the text_for_map_search
                if election.state_code.lower() == "na" or election.state_code.lower() == "":
                    # If a National election, then we want the address passed in
                    text_for_map_search_for_google_civic_retrieve = text_for_map_search
                elif election.state_code.lower() == state_code_from_text_for_map_search.lower():
                    text_for_map_search_for_google_civic_retrieve = text_for_map_search
                else:
                    text_for_map_search_for_google_civic_retrieve = ""
        else:
            # Voter address state_code not found, so we don't use the text_for_map_search value
            text_for_map_search_for_google_civic_retrieve = ""

        # YY)

    # If a partial address doesn't exist, exit because we can't generate a ballot without an address
    if voter_address_exists and not positive_value_exists(voter_address.text_for_map_search):
        status += "VOTER_ADDRESS_BLANK "
        results = {
            'status': status,
            'success': True,
            'google_civic_election_id': google_civic_election_id,
            'offices_held_for_location_id': offices_held_for_location_id,
            'state_code': '',
            'use_office_held_ballot':   False,
            'voter_ballot_saved_found': False,
            'voter_ballot_saved': None,
        }
        return results

    # 1) Find ballot specific to the voter's address
    # Search for these variables elsewhere when updating code
    turn_off_direct_voter_ballot_retrieve = True
    default_election_data_source_is_google_civic = False
    if turn_off_direct_voter_ballot_retrieve:
        # We set this option to force retrieval of a nearby ballot (instead of custom to voter's address)
        pass

    use_office_held_ballot = False
    results = find_closest_ballot_from_offices_held_data(
        # google_civic_election_id=google_civic_election_id,
        read_only=True,
        text_for_map_search=text_for_map_search,  # Make this more robust
    )
    if positive_value_exists(results['offices_held_for_location_id']):
        offices_held_for_location_id = results['offices_held_for_location_id']
        use_office_held_ballot = True

    results = {
        'status':                   status,
        'success':                  True,
        'google_civic_election_id': 0,
        'offices_held_for_location_id':   offices_held_for_location_id,
        'state_code':               '',
        'text_for_map_search':      '',
        'use_office_held_ballot':   use_office_held_ballot,
        'voter_ballot_saved':       None,
        'voter_ballot_saved_found': '',
    }
    return results


def find_closest_ballot_from_offices_held_data(
        google_civic_election_id=0,
        read_only=True,
        text_for_map_search='',
    ):
    offices_held_for_location = None
    offices_held_for_location_found = False
    offices_held_for_location_id = ''
    status = ""
    success = True
    office_held_manager = OfficeHeldManager()
    results = office_held_manager.find_closest_offices_held_for_location(
        text_for_map_search=text_for_map_search,
        # google_civic_election_id=google_civic_election_id,
        read_only=read_only)
    if results['offices_held_for_location_found']:
        offices_held_for_location = results['offices_held_for_location']
        offices_held_for_location_id = offices_held_for_location.id
        offices_held_for_location_found = True

    results = {
        'status': status,
        'geocoder_quota_exceeded': True,
        'offices_held_for_location': offices_held_for_location,
        'offices_held_for_location_found': offices_held_for_location_found,
        'offices_held_for_location_id': offices_held_for_location_id,
    }
    return results


def voter_ballot_items_retrieve_for_one_election_by_offices_held_for_api(  # voterBallotItemsRetrieve
        # voter_device_id,
        # voter_id=0,
        google_civic_election_id='',
        offices_held_for_location_id=''):
    google_civic_election_id = 0
    polling_location_we_vote_id = ''
    status = ""
    success = True

    if positive_value_exists(offices_held_for_location_id):
        pass
        # ballot_returned_results = \
        #     ballot_returned_manager.retrieve_ballot_returned_from_ballot_returned_we_vote_id(offices_held_for_location_id)
        # if ballot_returned_results['ballot_returned_found']:
        #     ballot_returned = ballot_returned_results['ballot_returned']
        #     polling_location_we_vote_id = ballot_returned.polling_location_we_vote_id

    ballot_item_object_list = []
    ballot_item_list_found = False
    office_held_manager = OfficeHeldManager()
    results = office_held_manager.retrieve_offices_held_for_location(
        offices_held_for_location_id=offices_held_for_location_id,
        read_only=True)
    if results['offices_held_for_location_found']:
        offices_held_for_location = results['offices_held_for_location']
        polling_location_we_vote_id = offices_held_for_location.polling_location_we_vote_id
        office_held_index_count = 1
        office_held_maximum_number = 30
        office_held_we_vote_id_list = []
        while office_held_index_count <= office_held_maximum_number:
            # name_key = "office_held_name_{index:02}".format(index=office_held_index_count)
            we_vote_id_key = "office_held_we_vote_id_{index:02}".format(index=office_held_index_count)
            if not hasattr(offices_held_for_location, we_vote_id_key):
                office_held_index_count += 1
                continue
            office_held_we_vote_id = getattr(offices_held_for_location, we_vote_id_key)
            if positive_value_exists(office_held_we_vote_id) and \
                    office_held_we_vote_id not in office_held_we_vote_id_list:
                office_held_we_vote_id_list.append(office_held_we_vote_id)
            office_held_index_count += 1

        # Retrieve all the ContestOffice objects mentioned in office_held_we_vote_id_list
        contest_office_list = []
        try:
            queryset = ContestOffice.objects.using('readonly').all()
            queryset = queryset.filter(office_held_we_vote_id__in=office_held_we_vote_id_list)
            contest_office_list = list(queryset)
        except Exception as e:
            status += 'FAILED_CONTEST_OFFICE_QUERY: ' + str(e) + " "

        # # Retrieve all the office_held objects mentioned in office_held_we_vote_id_list
        # office_held_list = []
        # try:
        #     queryset = OfficeHeld.objects.using('readonly').filter(we_vote_id__in=office_held_we_vote_id_list)
        #     office_held_list = list(queryset)
        # except Exception as e:
        #     status += 'FAILED_OFFICE_HELD_QUERY: ' + str(e) + " "
        #
        # # Put them in a dict and get all of the
        # office_held_dict = {}
        # for office_held in office_held_list:
        #     office_held_dict[office_held.we_vote_id] = office_held

        # Sort contest_office_list first?
        # Here we need to create mock-ballot_item objects, generated from ContestOffice objects
        ballot_item_object_list = []
        possible_google_civic_election_id_list = []
        google_civic_election_id = convert_to_int(google_civic_election_id)
        for contest_office in contest_office_list:
            ballot_item_object = BallotItem()
            ballot_item_object.ballot_item_display_name = contest_office.office_name
            ballot_item_object.contest_office_id = contest_office.id
            ballot_item_object.contest_office_we_vote_id = contest_office.we_vote_id
            ballot_item_object.polling_location_we_vote_id = polling_location_we_vote_id
            # Now add to object list
            ballot_item_object_list.append(ballot_item_object)
            ballot_item_list_found = True
            # Find the soonest upcoming election related to these ballot items
            if positive_value_exists(contest_office.google_civic_election_id):
                incoming_id = convert_to_int(contest_office.google_civic_election_id)
                if incoming_id not in possible_google_civic_election_id_list:
                    possible_google_civic_election_id_list.append(incoming_id)
                # This is a hack, and should be replaced by looking at data in Election table
                if incoming_id > google_civic_election_id:
                    google_civic_election_id = incoming_id

    if success and ballot_item_list_found:
        from ballot.controllers import generate_ballot_item_list_from_object_list
        results = generate_ballot_item_list_from_object_list(
            ballot_item_object_list=ballot_item_object_list,
            google_civic_election_id=google_civic_election_id,
            # voter_device_id=voter_device_id,
        )
    else:
        results = {
            'status':                   status,
            'success':                  False,
            # 'voter_device_id':          voter_device_id,
            'ballot_item_list':         [],
            'ballot_item_list_found':   ballot_item_list_found,
            'google_civic_election_id': google_civic_election_id,
        }

    return results
