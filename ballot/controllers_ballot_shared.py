# ballot/controllers_ballot_shared.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from candidate.models import CandidateListManager
from election.models import ElectionManager
from office.models import ContestOfficeListManager
from position.models import PositionListManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def shared_item_ballot_retrieve_for_api(  # sharedItemBallotRetrieve
        shared_by_voter_we_vote_id=''):
    status = ''
    ballot_item_list = []  # Contains the measures and offices, without candidates attached
    candidate_position_list = []  # Contains the candidate & position data
    link_lists_by_candidate_we_vote_id = {}
    election_day_text_by_election_id = {}
    position_list = []

    # We want all positions, and we will filter on the front-end
    position_list_manager = PositionListManager()
    from position.models import ALL_ELECTIONS
    results = position_list_manager.retrieve_all_positions_for_voter(
        this_election_vs_others=ALL_ELECTIONS,
        voter_we_vote_id=shared_by_voter_we_vote_id,
        read_only=True)
    status += results['status']
    if results['position_list_found']:
        # Convert position_list into ballot_item_list
        position_list = results['position_list']
        candidate_we_vote_id_list = []
        election_id_list = []
        office_we_vote_id_list = []

        # Loop through all positions first, so we can make a single retrieve from candidate table
        #  (and then election table) to augment with data we need.
        for one_position in position_list:
            if positive_value_exists(one_position.candidate_campaign_we_vote_id) \
                    and one_position.candidate_campaign_we_vote_id not in candidate_we_vote_id_list:
                candidate_we_vote_id_list.append(one_position.candidate_campaign_we_vote_id)
            if positive_value_exists(one_position.google_civic_election_id) \
                    and one_position.google_civic_election_id not in election_id_list:
                election_id_list.append(one_position.google_civic_election_id)

        # Get the elections, and figure out election_day_text.
        election_manager = ElectionManager()
        results = election_manager.retrieve_elections_by_google_civic_election_id_list(
            google_civic_election_id_list=election_id_list,
            read_only=True,
        )
        for one_election in results['election_list']:
            google_civic_election_id = one_election.google_civic_election_id \
                if positive_value_exists(one_election.google_civic_election_id) else 0
            google_civic_election_id = convert_to_int(google_civic_election_id)
            election_day_text_by_election_id[google_civic_election_id] = one_election.election_day_text

        # Since the same candidate can be viewed in either the primary or the general election, we provide the
        #  list of candidates independent of the Office. By linking CandidateToOfficeLink data to each candidate,
        #  we can know which candidates to show under each office shown on WebApp, as voters change their view.
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_to_office_link_list(
            candidate_we_vote_id_list=candidate_we_vote_id_list,
            read_only=True)
        link_lists_by_candidate_we_vote_id = {}
        for one_link in results['candidate_to_office_link_list']:
            if positive_value_exists(one_link.candidate_we_vote_id):
                if one_link.candidate_we_vote_id not in link_lists_by_candidate_we_vote_id:
                    link_lists_by_candidate_we_vote_id[one_link.candidate_we_vote_id] = []
                link_lists_by_candidate_we_vote_id[one_link.candidate_we_vote_id].append(one_link)
            if positive_value_exists(one_link.contest_office_we_vote_id) and \
                    one_link.contest_office_we_vote_id not in office_we_vote_id_list:
                office_we_vote_id_list.append(one_link.contest_office_we_vote_id)

        # Get all possible offices, so we can have a ballot_item entry per office (primaries and general)
        office_list_manager = ContestOfficeListManager()
        results = office_list_manager.retrieve_offices(
            retrieve_from_this_office_we_vote_id_list=office_we_vote_id_list,
            return_list_of_objects=True,
            read_only=True)
        for one_office in results['office_list_objects']:
            google_civic_election_id = one_office.google_civic_election_id \
                if positive_value_exists(one_office.google_civic_election_id) else 0
            google_civic_election_id = convert_to_int(google_civic_election_id)
            election_day_text = election_day_text_by_election_id[google_civic_election_id] \
                if google_civic_election_id in election_day_text_by_election_id else ''
            office_for_json = {
                'ballot_item_display_name': one_office.office_name,
                'election_day_text': election_day_text,
                'google_civic_election_id': google_civic_election_id,
                'kind_of_ballot_item': 'OFFICE',
                'race_office_level': one_office.ballotpedia_race_office_level,
                'we_vote_id': one_office.we_vote_id,
            }
            ballot_item_list.append(office_for_json)

    # Now loop through the positions and build the ballot_item_list and candidate_list
    for one_position in position_list:
        if positive_value_exists(one_position.candidate_campaign_we_vote_id):
            if one_position.candidate_campaign_we_vote_id in link_lists_by_candidate_we_vote_id:
                candidate_to_office_link_list = \
                    link_lists_by_candidate_we_vote_id[one_position.candidate_campaign_we_vote_id]
            else:
                candidate_to_office_link_list = []
            candidate_to_office_link_list_simple = []
            for candidate_to_office_link in candidate_to_office_link_list:
                google_civic_election_id = candidate_to_office_link.google_civic_election_id
                election_day_text = election_day_text_by_election_id[google_civic_election_id] \
                    if google_civic_election_id in election_day_text_by_election_id else ''
                candidate_to_office_link_dict = {
                    'candidate_we_vote_id': candidate_to_office_link.candidate_we_vote_id,
                    'contest_office_we_vote_id': candidate_to_office_link.contest_office_we_vote_id,
                    'election_day_text': election_day_text,
                    'google_civic_election_id': candidate_to_office_link.google_civic_election_id,
                }
                candidate_to_office_link_list_simple.append(candidate_to_office_link_dict)
            candidate_for_json = {
                'ballot_item_display_name': one_position.ballot_item_display_name,
                'candidate_photo_url_large': one_position.ballot_item_image_url_https_large,
                'candidate_photo_url_medium': one_position.ballot_item_image_url_https_medium,
                'candidate_photo_url_tiny': one_position.ballot_item_image_url_https_tiny,
                'candidate_to_office_link_list': candidate_to_office_link_list_simple,
                'is_oppose_or_negative_rating': one_position.is_oppose_or_negative_rating(),
                'is_support_or_positive_rating': one_position.is_support_or_positive_rating(),
                'kind_of_ballot_item': 'CANDIDATE',
                'party': one_position.political_party,
                'statement_text': one_position.statement_text,
                'we_vote_id': one_position.candidate_campaign_we_vote_id,
            }
            candidate_position_list.append(candidate_for_json)
        elif positive_value_exists(one_position.contest_measure_we_vote_id):
            # Add the measure positions
            google_civic_election_id = one_position.google_civic_election_id \
                if positive_value_exists(one_position.google_civic_election_id) else 0
            google_civic_election_id = convert_to_int(google_civic_election_id)
            election_day_text = election_day_text_by_election_id[google_civic_election_id] \
                if google_civic_election_id in election_day_text_by_election_id else ''
            statement_text = one_position.statement_text if one_position.statement_text is not None else ''
            measure_for_json = {
                'ballot_item_display_name': one_position.ballot_item_display_name,
                'election_day_text': election_day_text,
                'google_civic_election_id': google_civic_election_id,
                'is_oppose_or_negative_rating': one_position.is_oppose_or_negative_rating(),
                'is_support_or_positive_rating': one_position.is_support_or_positive_rating(),
                'kind_of_ballot_item': 'MEASURE',
                'race_office_level': 'Measure',
                'statement_text': statement_text,
                'we_vote_id': one_position.contest_measure_we_vote_id,
            }
            ballot_item_list.append(measure_for_json)

    json_data = {
        'status':                   status,
        'success':                  True,
        'ballot_item_list':         ballot_item_list,
        'ballot_item_list_found':   False,
        'candidate_position_list':  candidate_position_list,
        'google_civic_election_id': 0,
        'text_for_map_search':      '',
    }
    return json_data
