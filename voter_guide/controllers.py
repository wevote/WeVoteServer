# voter_guide/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import OFFICE, CANDIDATE, MEASURE
from django.http import HttpResponse
from follow.models import FollowOrganizationList
from itertools import chain
import json
from position.models import ANY_STANCE, PositionListManager
from voter.models import fetch_voter_id_from_voter_device_link
from voter_guide.models import VoterGuideList, VoterGuideManager, VoterGuidePossibilityManager
import wevote_functions.admin
from wevote_functions.functions import is_voter_device_id_valid, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def voter_guide_possibility_retrieve_for_api(voter_device_id, voter_guide_possibility_url):
    results = is_voter_device_id_valid(voter_device_id)
    voter_guide_possibility_url = voter_guide_possibility_url  # TODO Use scrapy here
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # TODO We will need the voter_id here so we can control volunteer actions

    voter_guide_possibility_manager = VoterGuidePossibilityManager()
    results = voter_guide_possibility_manager.retrieve_voter_guide_possibility_from_url(voter_guide_possibility_url)

    json_data = {
        'voter_device_id':              voter_device_id,
        'voter_guide_possibility_url':  results['voter_guide_possibility_url'],
        'voter_guide_possibility_id':   results['voter_guide_possibility_id'],
        'organization_we_vote_id':      results['organization_we_vote_id'],
        'public_figure_we_vote_id':     results['public_figure_we_vote_id'],
        'owner_we_vote_id':             results['owner_we_vote_id'],
        'status':                       results['status'],
        'success':                      results['success'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guide_possibility_save_for_api(voter_device_id, voter_guide_possibility_url):
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        return HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    if not voter_guide_possibility_url:
        json_data = {
                'status': "MISSING_POST_VARIABLE-URL",
                'success': False,
                'voter_device_id': voter_device_id,
            }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # At this point, we have a valid voter

    voter_guide_possibility_manager = VoterGuidePossibilityManager()

    # We wrap get_or_create because we want to centralize error handling
    results = voter_guide_possibility_manager.update_or_create_voter_guide_possibility(
        voter_guide_possibility_url.strip())
    if results['success']:
        json_data = {
                'status': "VOTER_GUIDE_POSSIBILITY_SAVED",
                'success': True,
                'voter_device_id': voter_device_id,
                'voter_guide_possibility_url': voter_guide_possibility_url,
            }

    # elif results['status'] == 'MULTIPLE_MATCHING_ADDRESSES_FOUND':
        # delete all currently matching addresses and save again?
    else:
        json_data = {
                'status': results['status'],
                'success': False,
                'voter_device_id': voter_device_id,
            }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guides_to_follow_retrieve_for_api(voter_device_id,  # voterGuidesToFollow
                                            kind_of_ballot_item='', ballot_item_we_vote_id='',
                                            google_civic_election_id=0, search_string='',
                                            maximum_number_to_retrieve=0):
    # Get voter_id from the voter_device_id so we can figure out which voter_guides to offer
    results = is_voter_device_id_valid(voter_device_id)
    if not results['success']:
        json_data = {
            'status': 'ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID',
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'google_civic_election_id': google_civic_election_id,
            'search_string': search_string,
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
        }
        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'json_data': json_data,
        }
        return results

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': "ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'google_civic_election_id': google_civic_election_id,
            'search_string': search_string,
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
        }
        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'json_data': json_data,
        }
        return results

    voter_guide_list = []
    voter_guides = []
    try:
        if positive_value_exists(kind_of_ballot_item) and positive_value_exists(ballot_item_we_vote_id):
            results = retrieve_voter_guides_to_follow_by_ballot_item(voter_id,
                                                                     kind_of_ballot_item, ballot_item_we_vote_id,
                                                                     search_string)
            success = results['success']
            status = results['status']
            voter_guide_list = results['voter_guide_list']
        elif positive_value_exists(google_civic_election_id):
            # This retrieve also does the reordering
            results = retrieve_voter_guides_to_follow_by_election_for_api(voter_id, google_civic_election_id,
                                                                          search_string,
                                                                          maximum_number_to_retrieve,
                                                                          'twitter_followers_count', 'desc')
            success = results['success']
            status = results['status']
            voter_guide_list = results['voter_guide_list']
        else:
            results = retrieve_voter_guides_to_follow_generic(voter_id, search_string,
                                                              maximum_number_to_retrieve,
                                                              'twitter_followers_count', 'desc')
            success = results['success']
            status = results['status']
            voter_guide_list = results['voter_guide_list']

    except Exception as e:
        status = 'FAILED voter_guides_to_follow_retrieve_for_api, retrieve_voter_guides_for_election ' \
                 '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
        success = False

    if success:
        number_added_to_list = 0
        for voter_guide in voter_guide_list:
            one_voter_guide = {
                'we_vote_id': voter_guide.we_vote_id,
                'google_civic_election_id': voter_guide.google_civic_election_id,
                'voter_guide_display_name': voter_guide.voter_guide_display_name(),
                'voter_guide_image_url': voter_guide.voter_guide_image_url(),
                'voter_guide_owner_type': voter_guide.voter_guide_owner_type,
                'organization_we_vote_id': voter_guide.organization_we_vote_id,
                'public_figure_we_vote_id': voter_guide.public_figure_we_vote_id,
                'twitter_followers_count': voter_guide.twitter_followers_count,
                'owner_voter_id': voter_guide.owner_voter_id,
                'last_updated': voter_guide.last_updated.strftime('%Y-%m-%d %H:%M'),
            }
            voter_guides.append(one_voter_guide.copy())
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(voter_guides):
            json_data = {
                'status': status + ' VOTER_GUIDES_TO_FOLLOW_RETRIEVED',
                'success': True,
                'voter_device_id': voter_device_id,
                'voter_guides': voter_guides,
                'google_civic_election_id': google_civic_election_id,
                'search_string': search_string,
                'ballot_item_we_vote_id': ballot_item_we_vote_id,
                'maximum_number_to_retrieve': maximum_number_to_retrieve,
            }
        else:
            json_data = {
                'status': status + ' NO_VOTER_GUIDES_FOUND',
                'success': True,
                'voter_device_id': voter_device_id,
                'voter_guides': voter_guides,
                'google_civic_election_id': google_civic_election_id,
                'search_string': search_string,
                'ballot_item_we_vote_id': ballot_item_we_vote_id,
                'maximum_number_to_retrieve': maximum_number_to_retrieve,
            }

        results = {
            'success': success,
            'google_civic_election_id': google_civic_election_id,
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'json_data': json_data,
        }
        return results
    else:
        json_data = {
            'status': status,
            'success': False,
            'voter_device_id': voter_device_id,
            'voter_guides': [],
            'google_civic_election_id': google_civic_election_id,
            'search_string': search_string,
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
        }

        results = {
            'success': False,
            'google_civic_election_id': 0,  # Force the reset of google_civic_election_id cookie
            'ballot_item_we_vote_id': ballot_item_we_vote_id,
            'json_data': json_data,
        }
        return results


def retrieve_voter_guides_to_follow_by_ballot_item(voter_id, kind_of_ballot_item, ballot_item_we_vote_id,
                                                   search_string):
    voter_guide_list_found = False

    position_list_manager = PositionListManager()
    if (kind_of_ballot_item == CANDIDATE) and positive_value_exists(ballot_item_we_vote_id):
        candidate_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_candidate_campaign(
                candidate_id, ballot_item_we_vote_id, ANY_STANCE)
    elif (kind_of_ballot_item == MEASURE) and positive_value_exists(ballot_item_we_vote_id):
        measure_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_measure(
                measure_id, ballot_item_we_vote_id, ANY_STANCE)
    elif (kind_of_ballot_item == OFFICE) and positive_value_exists(ballot_item_we_vote_id):
        office_id = 0
        all_positions_list = position_list_manager.retrieve_all_positions_for_contest_office(
                office_id, ballot_item_we_vote_id, ANY_STANCE)
    else:
        voter_guide_list = []
        results = {
            'success':                      False,
            'status':                       "VOTER_GUIDES_BALLOT_RELATED_VARIABLES_MISSING",
            'search_string':              search_string,
            'voter_guide_list_found':       False,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)

    positions_list = position_list_manager.calculate_positions_not_followed_by_voter(
        all_positions_list, organizations_followed_by_voter)

    voter_guide_list = []
    # Cycle through the positions held by groups that you don't currently follow
    voter_guide_manager = VoterGuideManager()
    for one_position in positions_list:
        if positive_value_exists(one_position.organization_we_vote_id):
            if one_position.google_civic_election_id:
                results = voter_guide_manager.retrieve_voter_guide(
                    voter_guide_id=0,
                    google_civic_election_id=one_position.google_civic_election_id,
                    vote_smart_time_span=None,
                    organization_we_vote_id=one_position.organization_we_vote_id)
            else:
                # vote_smart_time_span
                results = voter_guide_manager.retrieve_voter_guide(
                    voter_guide_id=0,
                    google_civic_election_id=0,
                    vote_smart_time_span=one_position.vote_smart_time_span,
                    organization_we_vote_id=one_position.organization_we_vote_id)

        elif positive_value_exists(one_position.public_figure_we_vote_id):
            results['voter_guide_found'] = False
        elif positive_value_exists(one_position.voter_we_vote_id):
            results['voter_guide_found'] = False
        else:
            results['voter_guide_found'] = False

        if results['voter_guide_found']:
            voter_guide = results['voter_guide']
            # If we passed in search_string, make sure they are in this entry.
            # If they aren't, don't return voter guide
            if positive_value_exists(search_string):
                search_string = str(search_string)  # Make sure search_string is a string
                twitter_handle = str(voter_guide.twitter_handle)
                display_name = str(voter_guide.display_name)

                if search_string.lower() in twitter_handle.lower() or search_string.lower() in display_name.lower():
                    voter_guide_list.append(voter_guide)
            else:
                voter_guide_list.append(voter_guide)

    status = 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_BY_BALLOT_ITEM'
    success = True

    if len(voter_guide_list):
        voter_guide_list_found = True

    results = {
        'success':                      success,
        'status':                       status,
        'search_string':              search_string,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def retrieve_voter_guides_to_follow_by_election_for_api(voter_id, google_civic_election_id, search_string,
                                                        maximum_number_to_retrieve=0, sort_by='', sort_order=''):
    voter_guide_list_found = False

    # Start with orgs followed and ignored by this voter
    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)
    organizations_ignored_by_voter = \
        follow_organization_list_manager.retrieve_ignore_organization_by_voter_id_simple_id_array(voter_id)

    position_list_manager = PositionListManager()
    if positive_value_exists(google_civic_election_id):
        # This method finds all ballot_items in this election, and then retrieves *all* positions by any org or person
        # about each ballot_item. This will pick up We Vote positions or Vote Smart ratings, regardless of what time
        # period they were entered for.
        all_positions_list_for_election = position_list_manager.retrieve_all_positions_for_election(
            google_civic_election_id, ANY_STANCE)
    else:
        voter_guide_list = []
        results = {
            'success':                      False,
            'status':                       "VOTER_GUIDES_BALLOT_RELATED_VARIABLES_MISSING",
            'voter_guide_list_found':       False,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    positions_list_minus_ignored = position_list_manager.remove_positions_ignored_by_voter(
        all_positions_list_for_election, organizations_ignored_by_voter)

    positions_list_minus_ignored_and_followed = position_list_manager.calculate_positions_not_followed_by_voter(
        positions_list_minus_ignored, organizations_followed_by_voter)

    if not len(positions_list_minus_ignored_and_followed):
        # If no positions are found, exit
        voter_guide_list = []
        results = {
            'success':                      True,
            'status':                       "NO_VOTER_GUIDES_FOUND_FOR_THIS_ELECTION",
            'voter_guide_list_found':       False,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    # We want to retrieve an ordered list of organization_we_vote_id's (not followed or ignored) that have a position
    # in this election. For speed we only retrieve full voter_guide data for the limited list that we need
    voter_guide_list_manager = VoterGuideList()
    # This is a list of orgs that the voter isn't following or ignoring
    org_list_found_by_google_civic_election_id = []
    for one_position in positions_list_minus_ignored_and_followed:
        # If the
        if positive_value_exists(one_position.organization_we_vote_id) and \
                positive_value_exists(one_position.google_civic_election_id):
            # Make sure we haven't already recorded that we want to retrieve the voter_guide for this org
            if one_position.organization_we_vote_id in org_list_found_by_google_civic_election_id:
                continue

            org_list_found_by_google_civic_election_id.append(one_position.organization_we_vote_id)

    # First, retrieve the voter_guides stored by org and google_civic_election_id
    if positive_value_exists(len(org_list_found_by_google_civic_election_id)):
        voter_guide_results = voter_guide_list_manager.retrieve_voter_guides_to_follow_by_election(
            google_civic_election_id, org_list_found_by_google_civic_election_id, search_string,
            maximum_number_to_retrieve, sort_by, sort_order)

        if voter_guide_results['voter_guide_list_found']:
            voter_guide_list_from_election_id = voter_guide_results['voter_guide_list']
        else:
            voter_guide_list_from_election_id = []
    else:
        voter_guide_list_from_election_id = []

    # Second, retrieve the voter_guides stored by org & vote_smart_time_span
    # All positions were found above with position_list_manager.retrieve_all_positions_for_election
    # We give precedence to full voter guides from above, where we have an actual position of an org (as opposed to
    # Vote Smart ratings)
    maximum_number_of_guides_to_retrieve_by_time_span = \
        maximum_number_to_retrieve - len(voter_guide_list_from_election_id)
    voter_guide_list = []
    if positive_value_exists(maximum_number_of_guides_to_retrieve_by_time_span):
        org_list_found_by_time_span = []
        orgs_we_need_found_by_position_and_time_span_list_of_dicts = []
        for one_position in positions_list_minus_ignored_and_followed:
            # If this was a position found that was based on vote_smart_time_span...
            #  (That is, ignore the positions already retrieved based on google_civic_election_id)
            if positive_value_exists(one_position.organization_we_vote_id) and \
                    positive_value_exists(one_position.vote_smart_time_span):
                # This shouldn't be possible, but we have it here for safety
                org_found_by_election_id_above = one_position.organization_we_vote_id in \
                    org_list_found_by_google_civic_election_id
                # If we already recorded that we want to look for this org under a different time span...
                org_found_by_different_time_span = one_position.organization_we_vote_id in \
                    org_list_found_by_time_span
                # Don't record that we want to look for a voter guide by this org we_vote_id or time span
                if org_found_by_election_id_above or org_found_by_different_time_span:
                    continue

                org_list_found_by_time_span.append(one_position.organization_we_vote_id)
                one_position_dict = {'organization_we_vote_id': one_position.organization_we_vote_id,
                                     'vote_smart_time_span': one_position.vote_smart_time_span}
                orgs_we_need_found_by_position_and_time_span_list_of_dicts.append(one_position_dict)

        voter_guide_time_span_results = voter_guide_list_manager.retrieve_voter_guides_to_follow_by_time_span(
            orgs_we_need_found_by_position_and_time_span_list_of_dicts,
            search_string,
            maximum_number_of_guides_to_retrieve_by_time_span, sort_by, sort_order)

        if voter_guide_time_span_results['voter_guide_list_found']:
            voter_guide_list_from_time_span = voter_guide_time_span_results['voter_guide_list']
        else:
            voter_guide_list_from_time_span = []

        # Merge these two lists
        # IFF we wanted to sort here:
        # voter_guide_list = sorted(
        #     chain(voter_guide_list_from_election_id, voter_guide_list_from_time_span),
        #     key=attrgetter(sort_by))
        # But we don't, we just want to combine them with existing order
        voter_guide_list = list(chain(voter_guide_list_from_election_id, voter_guide_list_from_time_span))

    status = 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_BY_ELECTION'
    success = True

    if len(voter_guide_list):
        voter_guide_list_found = True

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def retrieve_voter_guides_to_follow_generic(voter_id, search_string,
                                            maximum_number_to_retrieve=0, sort_by='', sort_order=''):
    """
    Separate from an election or a ballot item, return a list of voter_guides the voter has not already followed
    :param voter_id:
    :param search_string:
    :param maximum_number_to_retrieve:
    :param sort_by:
    :param sort_order:
    :return:
    """
    voter_guide_list_found = False

    # Start with orgs followed and ignored by this voter
    follow_organization_list_manager = FollowOrganizationList()
    organizations_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_id_array(voter_id)
    organizations_ignored_by_voter = \
        follow_organization_list_manager.retrieve_ignore_organization_by_voter_id_simple_id_array(voter_id)

    # This is a list of orgs that the voter is already following or ignoring
    organization_we_vote_ids_followed_or_ignored_by_voter = list(chain(organizations_followed_by_voter,
                                                                       organizations_ignored_by_voter))

    voter_guide_list_manager = VoterGuideList()

    # First, retrieve the voter_guides stored by org and google_civic_election_id
    voter_guide_results = voter_guide_list_manager.retrieve_voter_guides_to_follow_generic(
        organization_we_vote_ids_followed_or_ignored_by_voter, search_string,
        maximum_number_to_retrieve, sort_by, sort_order)

    if voter_guide_results['voter_guide_list_found']:
        voter_guide_list = voter_guide_results['voter_guide_list']
    else:
        voter_guide_list = []

    status = 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_GENERIC'
    success = True

    if len(voter_guide_list):
        voter_guide_list_found = True

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results


def voter_guides_followed_retrieve_for_api(voter_device_id, maximum_number_to_retrieve=0):
    """
    Start with the organizations followed and return a list of voter_guides. voterGuidesFollowedRetrieve
    See also organizations_followed_for_api, which returns a list of organizations.

    :param voter_device_id:
    :param maximum_number_to_retrieve:
    :return:
    """
    if not positive_value_exists(voter_device_id):
        json_data = {
            'status': 'VALID_VOTER_DEVICE_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if not positive_value_exists(voter_id):
        json_data = {
            'status': 'VALID_VOTER_ID_MISSING',
            'success': False,
            'voter_device_id': voter_device_id,
            'maximum_number_to_retrieve': maximum_number_to_retrieve,
            'voter_guides': [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = retrieve_voter_guides_followed(voter_id)
    status = results['status']
    voter_guide_list = results['voter_guide_list']
    voter_guides = []
    if results['voter_guide_list_found']:
        number_added_to_list = 0
        for voter_guide in voter_guide_list:
            one_voter_guide = {
                'we_vote_id': voter_guide.we_vote_id,
                'google_civic_election_id': voter_guide.google_civic_election_id,
                'voter_guide_display_name': voter_guide.voter_guide_display_name(),
                'voter_guide_image_url': voter_guide.voter_guide_image_url(),
                'voter_guide_owner_type': voter_guide.voter_guide_owner_type,
                'organization_we_vote_id': voter_guide.organization_we_vote_id,
                'public_figure_we_vote_id': voter_guide.public_figure_we_vote_id,
                'twitter_followers_count': voter_guide.twitter_followers_count,
                'owner_voter_id': voter_guide.owner_voter_id,
                'last_updated': voter_guide.last_updated.strftime('%Y-%m-%d %H:%M'),
            }
            voter_guides.append(one_voter_guide.copy())
            if positive_value_exists(maximum_number_to_retrieve):
                number_added_to_list += 1
                if number_added_to_list >= maximum_number_to_retrieve:
                    break

        if len(voter_guides):
            status = 'VOTER_GUIDES_FOLLOWED_RETRIEVED'
            success = True
        else:
            status = 'NO_VOTER_GUIDES_FOLLOWED_FOUND'
            success = True
    else:
        success = False

    json_data = {
        'status': status,
        'success': success,
        'voter_device_id': voter_device_id,
        'maximum_number_to_retrieve': maximum_number_to_retrieve,
        'voter_guides': voter_guides,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def retrieve_voter_guides_followed(voter_id):
    voter_guide_list_found = False

    follow_organization_list_manager = FollowOrganizationList()
    organization_we_vote_ids_followed_by_voter = \
        follow_organization_list_manager.retrieve_follow_organization_by_voter_id_simple_we_vote_id_array(voter_id)

    voter_guide_list_object = VoterGuideList()
    results = voter_guide_list_object.retrieve_voter_guides_by_organization_list(
        organization_we_vote_ids_followed_by_voter)

    voter_guide_list = []
    if results['voter_guide_list_found']:
        voter_guide_list = results['voter_guide_list']
        status = 'SUCCESSFUL_RETRIEVE_OF_VOTER_GUIDES_FOLLOWED'
        success = True
        if len(voter_guide_list):
            voter_guide_list_found = True
    else:
        status = results['status']
        success = False

    results = {
        'success':                      success,
        'status':                       status,
        'voter_guide_list_found':       voter_guide_list_found,
        'voter_guide_list':             voter_guide_list,
    }
    return results
