# apis_v1/views/views_voter_guide.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.controllers import choose_election_from_existing_data
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from api_internal_cache.models import ApiInternalCacheManager
from position.models import FRIENDS_AND_PUBLIC, FRIENDS_ONLY, PUBLIC_ONLY
from voter.models import VoterAddress, VoterAddressManager, VoterDeviceLinkManager, VoterManager
from voter_guide.controllers import voter_guide_possibility_highlights_retrieve_for_api, \
    voter_guide_possibility_retrieve_for_api, \
    voter_guide_possibility_position_save_for_api, \
    voter_guide_possibility_positions_retrieve_for_api, voter_guide_possibility_save_for_api, \
    voter_guide_save_for_api, \
    voter_guides_followed_retrieve_for_api, voter_guides_ignored_retrieve_for_api, voter_guides_retrieve_for_api, \
    voter_guides_followed_by_organization_retrieve_for_api, \
    voter_guide_followers_retrieve_for_api, \
    voter_guides_to_follow_retrieve_for_api, voter_guides_upcoming_retrieve_for_api
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_maximum_number_to_retrieve_from_request, \
    get_voter_device_id, positive_value_exists, return_value_from_request

logger = wevote_functions.admin.get_logger(__name__)


@csrf_exempt
def voter_guide_possibility_retrieve_view(request):  # voterGuidePossibilityRetrieve
    """
    Retrieve a previously saved website that may contain a voter guide (voterGuidePossibilityRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    url_to_scan = request.GET.get('url_to_scan', '')
    voter_guide_possibility_id = request.GET.get('voter_guide_possibility_id', 0)
    limit_to_this_year = request.GET.get('limit_to_this_year', True)
    return voter_guide_possibility_retrieve_for_api(voter_device_id=voter_device_id,
                                                    voter_guide_possibility_id=voter_guide_possibility_id,
                                                    url_to_scan=url_to_scan,
                                                    limit_to_this_year=limit_to_this_year)


@csrf_exempt
def voter_guide_possibility_position_save_view(request):  # voterGuidePossibilityPositionSave
    """
    Update one possible position from one organization on one page.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    is_post = True if request.method == 'POST' else False

    voter_guide_possibility_id = return_value_from_request(request, 'voter_guide_possibility_id', is_post, 0)
    voter_guide_possibility_position_id = return_value_from_request(request, 'voter_guide_possibility_position_id', is_post, 0)
    ballot_item_name = return_value_from_request(request, 'ballot_item_name', is_post, None)
    ballot_item_state_code = return_value_from_request(request, 'ballot_item_state_code', is_post, None)
    candidate_twitter_handle = return_value_from_request(request, 'candidate_twitter_handle', is_post, None)
    candidate_we_vote_id = return_value_from_request(request, 'candidate_we_vote_id', is_post, None)
    measure_we_vote_id = return_value_from_request(request, 'measure_we_vote_id', is_post, None)
    more_info_url = return_value_from_request(request, 'more_info_url', is_post, None)
    organization_name = return_value_from_request(request, 'organization_name', is_post, None)
    organization_twitter_handle = return_value_from_request(request, 'organization_twitter_handle', is_post, None)
    organization_we_vote_id = return_value_from_request(request, 'organization_we_vote_id', is_post, None)
    position_should_be_removed = return_value_from_request(request, 'position_should_be_removed', is_post, None)
    position_stance = return_value_from_request(request, 'position_stance', is_post, None)
    possibility_should_be_deleted = return_value_from_request(request, 'possibility_should_be_deleted', is_post, None)
    possibility_should_be_ignored = return_value_from_request(request, 'possibility_should_be_ignored', is_post, None)
    statement_text = return_value_from_request(request, 'statement_text', is_post, None)

    google_civic_election_id_list = return_value_from_request(request, 'google_civic_election_id_list[]', is_post, None)

    try:
        if positive_value_exists(google_civic_election_id_list):
            if not positive_value_exists(len(google_civic_election_id_list)):
                google_civic_election_id_list = None
        else:
            google_civic_election_id_list = None
    except:
        google_civic_election_id_list = None

    json_data = voter_guide_possibility_position_save_for_api(
        voter_device_id=voter_device_id,
        voter_guide_possibility_id=voter_guide_possibility_id,
        voter_guide_possibility_position_id=voter_guide_possibility_position_id,
        ballot_item_name=ballot_item_name,
        ballot_item_state_code=ballot_item_state_code,
        position_stance=position_stance,
        statement_text=statement_text,
        more_info_url=more_info_url,
        possibility_should_be_deleted=possibility_should_be_deleted,
        possibility_should_be_ignored=possibility_should_be_ignored,
        candidate_twitter_handle=candidate_twitter_handle,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        organization_name=organization_name,
        organization_twitter_handle=organization_twitter_handle,
        organization_we_vote_id=organization_we_vote_id,
        position_should_be_removed=position_should_be_removed,
        google_civic_election_id_list=google_civic_election_id_list)
    return HttpResponse(json.dumps(json_data), content_type='application/json')


@csrf_exempt
def voter_guide_possibility_highlights_retrieve_view(request):  # voterGuidePossibilityHighlightsRetrieve
    """
    Retrieve the possible highlights from one organization on one page.
    :param request:
    :return:
    """
    status = ''
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    is_post = True if request.method == 'POST' else False

    if is_post:
        url_to_scan = request.POST.get('url_to_scan', '')
        visible_text_to_scan = request.POST.get('visible_text_to_scan', '')
        pdf_url = request.POST.get('pdf_url', '')
        google_civic_election_id = request.POST.get('google_civic_election_id', 0)
        use_vertex_to_scan_url_if_no_visible_text_provided = \
            request.POST.get('use_vertex_to_scan_url_if_no_visible_text_provided', True)
    else:
        url_to_scan = request.GET.get('url_to_scan', '')
        pdf_url = request.GET.get('pdf_url', '')
        google_civic_election_id = request.GET.get('google_civic_election_id', 0)
        visible_text_to_scan = request.GET.get('visible_text_to_scan', '')
        use_vertex_to_scan_url_if_no_visible_text_provided = \
            request.GET.get('use_vertex_to_scan_url_if_no_visible_text_provided', True)

    names_list = []
    if positive_value_exists(visible_text_to_scan):
        from import_export_vertex.controllers import find_names_of_people_from_incoming_text
        results = find_names_of_people_from_incoming_text(text_to_scan=visible_text_to_scan)
        if results['names_list_found']:
            names_list = results['names_list']
        status += results['status']
    elif positive_value_exists(url_to_scan) \
            and positive_value_exists(use_vertex_to_scan_url_if_no_visible_text_provided):
        from import_export_vertex.controllers import find_names_of_people_on_one_web_page
        results = find_names_of_people_on_one_web_page(site_url=url_to_scan)
        if results['names_list_found']:
            names_list = results['names_list']
        status += results['status']

    json_data = voter_guide_possibility_highlights_retrieve_for_api(
        google_civic_election_id=google_civic_election_id,
        names_list=names_list,
        pdf_url=pdf_url,
        status=status,
        url_to_scan=url_to_scan,
        voter_device_id=voter_device_id,
    )
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guide_possibility_positions_retrieve_view(request):  # voterGuidePossibilityPositionsRetrieve
    """
    Retrieve the possible positions from one organization on one page.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_guide_possibility_id = request.GET.get('voter_guide_possibility_id', 0)
    # print("voter_guide_possibility_id: " + voter_guide_possibility_id)
    voter_guide_possibility_position_id = request.GET.get('voter_guide_possibility_position_id', 0)
    json_data = voter_guide_possibility_positions_retrieve_for_api(
        voter_device_id=voter_device_id,
        voter_guide_possibility_id=voter_guide_possibility_id,
        voter_guide_possibility_position_id=voter_guide_possibility_position_id)
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_guide_possibility_save_view(request):  # voterGuidePossibilitySave
    """
    Save a website that may contain a voter guide (voterGuidePossibilitySave)
    Note that this does not save positions -- we do that with voterGuidePossibilityPositionSave
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_guide_possibility_id = request.GET.get('voter_guide_possibility_id', 0)
    voter_guide_possibility_id = convert_to_int(voter_guide_possibility_id)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', None)
    clear_organization_options = request.GET.get('clear_organization_options', None)
    contributor_comments = request.GET.get('contributor_comments', None)
    contributor_email = request.GET.get('contributor_email', None)
    candidates_missing_from_we_vote = request.GET.get('candidates_missing_from_we_vote', None)
    capture_detailed_comments = request.GET.get('capture_detailed_comments', None)
    hide_from_active_review = request.GET.get('hide_from_active_review', None)
    ignore_this_source = request.GET.get('ignore_this_source', None)
    internal_notes = request.GET.get('internal_notes', None)
    limit_to_this_state_code = request.GET.get('limit_to_this_state_code', None)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', None)
    possible_candidate_name = request.GET.get('possible_candidate_name', None)
    possible_candidate_twitter_handle = request.GET.get('possible_candidate_twitter_handle', None)
    possible_organization_name = request.GET.get('possible_organization_name', None)
    possible_organization_twitter_handle = request.GET.get('possible_organization_twitter_handle', None)
    voter_guide_possibility_type = request.GET.get('voter_guide_possibility_type', None)
    return voter_guide_possibility_save_for_api(
        voter_device_id=voter_device_id,
        voter_guide_possibility_id=voter_guide_possibility_id,
        candidates_missing_from_we_vote=candidates_missing_from_we_vote,
        capture_detailed_comments=capture_detailed_comments,
        clear_organization_options=clear_organization_options,
        contributor_comments=contributor_comments,
        contributor_email=contributor_email,
        hide_from_active_review=hide_from_active_review,
        ignore_this_source=ignore_this_source,
        internal_notes=internal_notes,
        voter_guide_possibility_type=voter_guide_possibility_type,
        organization_we_vote_id=organization_we_vote_id,
        possible_organization_name=possible_organization_name,
        possible_organization_twitter_handle=possible_organization_twitter_handle,
        candidate_we_vote_id=candidate_we_vote_id,
        possible_candidate_name=possible_candidate_name,
        possible_candidate_twitter_handle=possible_candidate_twitter_handle,
        limit_to_this_state_code=limit_to_this_state_code)


def voter_guides_followed_retrieve_view(request):  # voterGuidesFollowedRetrieve
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_followed_retrieve_for_api(voter_device_id=voter_device_id,
                                                  maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guides_followed_by_organization_retrieve_view(request):  # voterGuidesFollowedByOrganizationRetrieve
    voter_linked_organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    filter_by_this_google_civic_election_id = request.GET.get('filter_by_this_google_civic_election_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_followed_by_organization_retrieve_for_api(
        voter_device_id,
        voter_linked_organization_we_vote_id=voter_linked_organization_we_vote_id,
        filter_by_this_google_civic_election_id=filter_by_this_google_civic_election_id,
        maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guide_followers_retrieve_view(request):  # voterGuideFollowersRetrieve
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guide_followers_retrieve_for_api(
        voter_device_id, organization_we_vote_id=organization_we_vote_id,
        maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guide_save_view(request):  # voterGuideSave
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_guide_we_vote_id = request.GET.get('voter_guide_we_vote_id', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    return voter_guide_save_for_api(voter_device_id=voter_device_id,
                                    voter_guide_we_vote_id=voter_guide_we_vote_id,
                                    google_civic_election_id=google_civic_election_id)


def voter_guides_ignored_retrieve_view(request):  # voterGuidesIgnoredRetrieve
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_ignored_retrieve_for_api(voter_device_id=voter_device_id,
                                                 maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guides_retrieve_view(request):  # voterGuidesRetrieve
    # voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    voter_we_vote_id = request.GET.get('voter_we_vote_id', '')
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_retrieve_for_api(organization_we_vote_id=organization_we_vote_id,
                                         voter_we_vote_id=voter_we_vote_id,
                                         maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guides_to_follow_retrieve_view(request):  # voterGuidesToFollowRetrieve
    """
    Retrieve a list of voter_guides that a voter might want to follow (voterGuidesToFollow)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', '')
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', '')
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    search_string = request.GET.get('search_string', '')
    use_test_election = positive_value_exists(request.GET.get('use_test_election', False))
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    start_retrieve_at_this_number = request.GET.get('start_retrieve_at_this_number', 0)
    filter_voter_guides_by_issue = positive_value_exists(request.GET.get('filter_voter_guides_by_issue', False))
    # If we want to show voter guides associated with election first, but then show more after those are exhausted,
    #  set add_voter_guides_not_from_election to True
    add_voter_guides_not_from_election = request.GET.get('add_voter_guides_not_from_election', False)
    add_voter_guides_not_from_election = positive_value_exists(add_voter_guides_not_from_election)

    if positive_value_exists(ballot_item_we_vote_id):
        # We don't need both ballot_item and google_civic_election_id
        google_civic_election_id = 0
    else:
        if positive_value_exists(use_test_election):
            google_civic_election_id = 2000  # The Google Civic API Test election
        elif positive_value_exists(google_civic_election_id) or google_civic_election_id == 0:  # Why "0" election?
            # If an election was specified, we can skip down to retrieving the voter_guides
            pass
        else:
            # If here we don't have either a ballot_item or a google_civic_election_id.
            # Look in the places we cache google_civic_election_id
            google_civic_election_id = 0
            voter_device_link_manager = VoterDeviceLinkManager()
            voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            voter_device_link = voter_device_link_results['voter_device_link']
            if voter_device_link_results['voter_device_link_found']:
                voter_id = voter_device_link.voter_id
                voter_address_manager = VoterAddressManager()
                voter_address_results = voter_address_manager.retrieve_address(0, voter_id)
                if voter_address_results['voter_address_found']:
                    voter_address = voter_address_results['voter_address']
                else:
                    voter_address = None
            else:
                voter_address = None
            results = choose_election_from_existing_data(voter_device_link, google_civic_election_id, voter_address)
            google_civic_election_id = results['google_civic_election_id']

        # In order to return voter_guides that are independent of an election or ballot_item, we need to pass in
        # google_civic_election_id as 0

    results = voter_guides_to_follow_retrieve_for_api(voter_device_id, kind_of_ballot_item, ballot_item_we_vote_id,
                                                      google_civic_election_id, search_string,
                                                      start_retrieve_at_this_number, maximum_number_to_retrieve,
                                                      filter_voter_guides_by_issue,
                                                      add_voter_guides_not_from_election)
    return HttpResponse(json.dumps(results['json_data']), content_type='application/json')


def voter_guides_from_friends_upcoming_retrieve_view(request):  # voterGuidesFromFriendsUpcomingRetrieve
    """
    Retrieve a list of voter_guides from voter's friends
    :param request:
    :return:
    """
    status = ""
    voter_we_vote_id = ''
    google_civic_election_id_list = request.GET.getlist('google_civic_election_id_list[]')

    if positive_value_exists(google_civic_election_id_list):
        if not positive_value_exists(len(google_civic_election_id_list)):
            google_civic_election_id_list = []
    else:
        google_civic_election_id_list = []

    voter_device_id = get_voter_device_id(request)
    voter_manager = VoterManager()
    voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id, read_only=True)
    if positive_value_exists(voter_results['voter_found']):
        voter_we_vote_id = voter_results['voter'].we_vote_id
    else:
        status += "VOTER_GUIDES_FROM_FRIENDS-MISSING_VOTER_WE_VOTE_ID "
        results = {
            'status':           status,
            'success':          False,
            'voter_guides':     [],
            'number_retrieved': 0,
        }
        return HttpResponse(json.dumps(results), content_type='application/json')

    results = voter_guides_upcoming_retrieve_for_api(
        google_civic_election_id_list=google_civic_election_id_list,
        friends_vs_public=FRIENDS_AND_PUBLIC,
        voter_we_vote_id=voter_we_vote_id)
    status += results['status']

    return HttpResponse(json.dumps(results['json_data']), content_type='application/json')


def voter_guides_upcoming_retrieve_view(request):  # voterGuidesUpcomingRetrieve
    """
    Retrieve a list of voter_guides that a voter might want to follow (voterGuidesUpcoming)
    :param request:
    :return:
    """
    status = ""
    api_internal_cache = None
    api_internal_cache_found = False
    json_data = {}

    google_civic_election_id_list = request.GET.getlist('google_civic_election_id_list[]')

    if positive_value_exists(google_civic_election_id_list):
        if not positive_value_exists(len(google_civic_election_id_list)):
            google_civic_election_id_list = []
    else:
        google_civic_election_id_list = []

    # Since this API assembles a lot of data, we pre-cache it. Get the data cached most recently.
    api_internal_cache_manager = ApiInternalCacheManager()
    election_id_list_serialized = json.dumps(google_civic_election_id_list)
    results = api_internal_cache_manager.retrieve_latest_api_internal_cache(
        api_name='voterGuidesUpcoming',
        election_id_list_serialized=election_id_list_serialized)
    if results['api_internal_cache_found']:
        api_internal_cache_found = True
        api_internal_cache = results['api_internal_cache']
        json_data = results['cached_api_response_json_data']

    # Schedule the next retrieve. It is possible for the first retrieve
    # of the day (above) to be using data from a few days ago.
    results = api_internal_cache_manager.schedule_refresh_of_api_internal_cache(
        api_name='voterGuidesUpcoming',
        election_id_list_serialized=election_id_list_serialized,
        api_internal_cache=api_internal_cache,
    )
    # Add a log entry here

    if not api_internal_cache_found:
        results = voter_guides_upcoming_retrieve_for_api(google_civic_election_id_list=google_civic_election_id_list)
        status += results['status']
        json_data = results['json_data']

    return HttpResponse(json.dumps(json_data), content_type='application/json')
