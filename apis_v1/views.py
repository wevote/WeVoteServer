# apis_v1/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import organization_count, organization_follow, organization_follow_ignore, \
    organization_stop_following, voter_count, voter_create
from ballot.controllers import ballot_item_options_retrieve_for_api, voter_ballot_items_retrieve_for_api
from candidate.controllers import candidate_retrieve_for_api, candidates_retrieve_for_api
from django.http import HttpResponse
from election.controllers import elections_retrieve_list_for_api
from election.serializers import ElectionSerializer
from geoip.controllers import voter_location_retrieve_from_ip_for_api
from import_export_facebook.controllers import facebook_sign_in_for_api
from import_export_google_civic.controllers import voter_ballot_items_retrieve_from_google_civic_for_api
from import_export_twitter.controllers import twitter_sign_in_start_for_api
import json
from measure.controllers import measure_retrieve_for_api
from office.controllers import office_retrieve_for_api
from organization.controllers import organization_retrieve_for_api, organization_save_for_api, \
    organization_search_for_api, organizations_followed_retrieve_for_api
from position.controllers import position_list_for_ballot_item_for_api, position_retrieve_for_api, \
    position_save_for_api, voter_position_retrieve_for_api, voter_position_comment_save_for_api
from position.models import ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING
from position_like.controllers import position_like_count_for_api, voter_position_like_off_save_for_api, \
    voter_position_like_on_save_for_api, voter_position_like_status_retrieve_for_api
from quick_info.controllers import quick_info_retrieve_for_api
from ballot.models import OFFICE, CANDIDATE, MEASURE
from rest_framework.response import Response
from rest_framework.views import APIView
from star.controllers import voter_star_off_save_for_api, voter_star_on_save_for_api, voter_star_status_retrieve_for_api
from support_oppose_deciding.controllers import position_oppose_count_for_ballot_item_for_api, \
    position_support_count_for_ballot_item_for_api, \
    position_public_oppose_count_for_ballot_item_for_api, \
    position_public_support_count_for_ballot_item_for_api, \
    voter_opposing_save, voter_stop_opposing_save, voter_stop_supporting_save, voter_supporting_save_for_api
from voter.controllers import voter_retrieve_for_api, voter_address_retrieve_for_api, voter_address_save_for_api, \
    voter_photo_save_for_api, voter_retrieve_list_for_api
from voter.serializers import VoterSerializer
from voter_guide.controllers import voter_guide_possibility_retrieve_for_api, voter_guide_possibility_save_for_api, \
    voter_guides_followed_retrieve_for_api, voter_guides_to_follow_retrieve_for_api
from wevote_functions.functions import generate_voter_device_id, get_ip_from_headers, get_voter_device_id, \
    get_google_civic_election_id_from_cookie, set_google_civic_election_id_cookie, positive_value_exists, convert_to_int
import wevote_functions.admin


logger = wevote_functions.admin.get_logger(__name__)


def ballot_item_options_retrieve_view(request):
    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    results = ballot_item_options_retrieve_for_api(google_civic_election_id)
    response = HttpResponse(json.dumps(results['json_data']), content_type='application/json')
    return response


def ballot_item_retrieve_view(request):
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)

    if not positive_value_exists(kind_of_ballot_item) or kind_of_ballot_item not in(OFFICE, CANDIDATE, MEASURE):
        status = 'VALID_BALLOT_ITEM_TYPE_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':         kind_of_ballot_item,
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if kind_of_ballot_item == OFFICE:
        return office_retrieve_for_api(ballot_item_id, ballot_item_we_vote_id)
    elif kind_of_ballot_item == CANDIDATE:
        return candidate_retrieve_for_api(ballot_item_id, ballot_item_we_vote_id)
    elif kind_of_ballot_item == MEASURE:
        return measure_retrieve_for_api(ballot_item_id, ballot_item_we_vote_id)
    else:
        status = 'BALLOT_ITEM_RETRIEVE_UNKNOWN_ERROR'
        json_data = {
            'status':                   status,
            'success':                  False,
            'kind_of_ballot_item':      kind_of_ballot_item,
            'ballot_item_id':           ballot_item_id,
            'ballot_item_we_vote_id':   ballot_item_we_vote_id,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')


def candidate_retrieve_view(request):
    candidate_id = request.GET.get('candidate_id', 0)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', None)
    return candidate_retrieve_for_api(candidate_id, candidate_we_vote_id)


def candidates_retrieve_view(request):
    office_id = request.GET.get('office_id', 0)
    office_we_vote_id = request.GET.get('office_we_vote_id', '')
    return candidates_retrieve_for_api(office_id, office_we_vote_id)


def device_id_generate_view(request):
    """
    This API call is used by clients to generate a transient unique identifier (device_id - stored on client)
    which ties the device to a persistent voter_id (mapped together and stored on the server).

    :param request:
    :return: Unique device id that can be stored in a cookie
    """
    voter_device_id = generate_voter_device_id()  # Stored in cookie elsewhere
    logger.debug("apis_v1/views.py, device_id_generate-voter_device_id: {voter_device_id}".format(
        voter_device_id=voter_device_id
    ))

    json_data = {
        'voter_device_id': voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


class ElectionsRetrieveView(APIView):
    """
    Export raw voter data to JSON format
    """
    def get(self, request):  # Removed: , format=None
        voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
        results = elections_retrieve_list_for_api(voter_device_id)

        if 'success' not in results:
            json_data = results['json_data']
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        elif not results['success']:
            json_data = results['json_data']
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        else:
            election_list = results['election_list']
            serializer = ElectionSerializer(election_list, many=True)
            return Response(serializer.data)


def facebook_sign_in_view(request):
    """
    Saving the results of signing in with Facebook
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    facebook_id = request.GET.get('facebook_id', None)
    facebook_email = request.GET.get('facebook_email', None)
    results = facebook_sign_in_for_api(voter_device_id, facebook_id, facebook_email)
    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'facebook_id': results['facebook_id'],
        'facebook_email': results['facebook_email'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def measure_retrieve_view(request):
    measure_id = request.GET.get('measure_id', 0)
    measure_we_vote_id = request.GET.get('measure_we_vote_id', None)
    return measure_retrieve_for_api(measure_id, measure_we_vote_id)


def office_retrieve_view(request):
    office_id = request.GET.get('office_id', 0)
    office_we_vote_id = request.GET.get('office_we_vote_id', None)
    return office_retrieve_for_api(office_id, office_we_vote_id)


def organization_count_view(request):
    return organization_count()


def organization_follow_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    return organization_follow(voter_device_id=voter_device_id, organization_id=organization_id)


def organization_stop_following_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    return organization_stop_following(voter_device_id=voter_device_id, organization_id=organization_id)


def organization_follow_ignore_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    return organization_follow_ignore(voter_device_id=voter_device_id, organization_id=organization_id)


def organization_retrieve_view(request):
    """
    Retrieve a single organization based on unique identifier
    :param request:
    :return:
    """
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    return organization_retrieve_for_api(
        organization_id=organization_id, organization_we_vote_id=organization_we_vote_id)


def organization_save_view(request):
    """
    Retrieve a single organization based on unique identifier
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    organization_id = request.POST.get('organization_id', 0)
    organization_we_vote_id = request.POST.get('organization_we_vote_id', '')
    organization_name = request.POST.get('organization_name', False)
    organization_email = request.POST.get('organization_email', False)
    organization_website = request.POST.get('organization_website', False)
    organization_twitter_handle = request.POST.get('organization_twitter_handle', False)
    organization_facebook = request.POST.get('organization_facebook', False)
    organization_image = request.POST.get('organization_image', False)

    results = organization_save_for_api(
        voter_device_id=voter_device_id, organization_id=organization_id,
        organization_we_vote_id=organization_we_vote_id,
        organization_name=organization_name, organization_email=organization_email,
        organization_website=organization_website, organization_twitter_handle=organization_twitter_handle,
        organization_facebook=organization_facebook, organization_image=organization_image)

    return HttpResponse(json.dumps(results), content_type='application/json')


def organization_search_view(request):
    """
    Search for organizations based on a few search terms
    :param request:
    :return:
    """
    organization_name = request.GET.get('organization_name', '')
    organization_twitter_handle = request.GET.get('organization_twitter_handle', '')
    organization_website = request.GET.get('organization_website', '')
    organization_email = request.GET.get('organization_email', '')
    return organization_search_for_api(organization_name=organization_name,
                                       organization_twitter_handle=organization_twitter_handle,
                                       organization_website=organization_website,
                                       organization_email=organization_email)


def organizations_followed_retrieve_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return organizations_followed_retrieve_for_api(voter_device_id=voter_device_id,
                                                   maximum_number_to_retrieve=maximum_number_to_retrieve)


def get_maximum_number_to_retrieve_from_request(request):
    if 'maximum_number_to_retrieve' in request.GET:
        maximum_number_to_retrieve = request.GET['maximum_number_to_retrieve']
    else:
        maximum_number_to_retrieve = 20
    if maximum_number_to_retrieve is "":
        maximum_number_to_retrieve = 20
    else:
        maximum_number_to_retrieve = convert_to_int(maximum_number_to_retrieve)

    return maximum_number_to_retrieve


def position_list_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and friends that support this (positionSupportCountForBallotItem)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    stance = request.GET.get('stance', ANY_STANCE)
    if stance in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
        stance_we_are_looking_for = stance
    else:
        stance_we_are_looking_for = ANY_STANCE
    show_positions_this_voter_follows = request.GET.get('show_positions_this_voter_follows', True)
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        candidate_id = 0
        measure_id = 0
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        office_id = 0
        candidate_id = 0
        measure_id = 0
    return position_list_for_ballot_item_for_api(voter_device_id=voter_device_id,
                                                 office_id=office_id,
                                                 candidate_id=candidate_id,
                                                 measure_id=measure_id,
                                                 stance_we_are_looking_for=stance_we_are_looking_for,
                                                 show_positions_this_voter_follows=show_positions_this_voter_follows)


def position_retrieve_view(request):
    """
    Retrieve all of the details about a single position based on unique identifier
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    position_id = request.GET.get('position_id', 0)
    position_we_vote_id = request.GET.get('position_we_vote_id', '')
    return position_retrieve_for_api(
        position_id=position_id,
        position_we_vote_id=position_we_vote_id,
        voter_device_id=voter_device_id
    )


def position_save_view(request):
    """
    Save a single position
    :param request:
    :return:
    """
    # We set values that aren't passed in, to False so we know to treat them as null or unchanged. This allows us to
    #  only change the values we want to
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    position_id = request.POST.get('position_id', False)
    position_we_vote_id = request.POST.get('position_we_vote_id', False)
    organization_we_vote_id = request.POST.get('organization_we_vote_id', False)
    public_figure_we_vote_id = request.POST.get('public_figure_we_vote_id', False)
    voter_we_vote_id = request.POST.get('voter_we_vote_id', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', False)
    ballot_item_display_name = request.POST.get('ballot_item_display_name', False)
    office_we_vote_id = request.POST.get('office_we_vote_id', False)
    candidate_we_vote_id = request.POST.get('candidate_we_vote_id', False)
    measure_we_vote_id = request.POST.get('measure_we_vote_id', False)
    stance = request.POST.get('stance', False)
    statement_text = request.POST.get('statement_text', False)
    statement_html = request.POST.get('statement_html', False)
    more_info_url = request.POST.get('more_info_url', False)

    results = position_save_for_api(
        voter_device_id=voter_device_id,
        position_id=position_id,
        position_we_vote_id=position_we_vote_id,
        organization_we_vote_id=organization_we_vote_id,
        public_figure_we_vote_id=public_figure_we_vote_id,
        voter_we_vote_id=voter_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        ballot_item_display_name=ballot_item_display_name,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        stance=stance,
        statement_text=statement_text,
        statement_html=statement_html,
        more_info_url=more_info_url,
    )

    return HttpResponse(json.dumps(results), content_type='application/json')


def position_oppose_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and friends that oppose this (positionOpposeCountForBallotItem)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        candidate_id = 0
        measure_id = 0
    return position_oppose_count_for_ballot_item_for_api(voter_device_id=voter_device_id, candidate_id=candidate_id,
                                                         measure_id=measure_id)


def position_support_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and friends that support this (positionSupportCountForBallotItem)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        candidate_id = 0
        measure_id = 0
    return position_support_count_for_ballot_item_for_api(voter_device_id=voter_device_id, candidate_id=candidate_id,
                                                          measure_id=measure_id)


def position_public_oppose_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and friends that oppose this (positionOpposeCountForBallotItem)
    :param request:
    :return:
    """
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        candidate_id = 0
        measure_id = 0
    return position_public_oppose_count_for_ballot_item_for_api(candidate_id=candidate_id,
                                                                measure_id=measure_id)


def position_public_support_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and friends that support this (positionSupportCountForBallotItem)
    :param request:
    :return:
    """
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        candidate_id = 0
        measure_id = 0
    return position_public_support_count_for_ballot_item_for_api(candidate_id=candidate_id,
                                                                 measure_id=measure_id)


def quick_info_retrieve_view(request):
    """
    Retrieve the information necessary to populate a bubble next to a ballot item.
    :param request:
    :return:
    """
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', "")
    return quick_info_retrieve_for_api(kind_of_ballot_item=kind_of_ballot_item,
                                       ballot_item_we_vote_id=ballot_item_we_vote_id)


def twitter_sign_in_start_view(request):
    """
    Start off the process of signing in with Twitter
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    results = twitter_sign_in_start_for_api(voter_device_id)
    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'twitter_redirect_url': results['twitter_redirect_url'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_address_retrieve_view(request):
    """
    Retrieve an address for this voter so we can figure out which ballot to display
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    return voter_address_retrieve_for_api(voter_device_id)


def voter_address_save_view(request):
    """
    Save or update an address for this voter
    :param request:
    :return:
    """

    status = ''

    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    try:
        text_for_map_search = request.POST['text_for_map_search']
        text_for_map_search = text_for_map_search.strip()
        address_variable_exists = True
    except KeyError:
        text_for_map_search = ''
        address_variable_exists = False

    results = voter_address_save_for_api(voter_device_id, text_for_map_search, address_variable_exists)
    voter_address_saved = True if results['success'] else False

    if not positive_value_exists(text_for_map_search):
        json_data = {
            'status': results['status'],
            'success': results['success'],
            'voter_device_id': voter_device_id,
            'text_for_map_search': text_for_map_search,
            'voter_address_saved': voter_address_saved,
            'google_civic_election_id': 0,
        }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')

        # Reset google_civic_election_id to 0 whenever we save an empty address
        google_civic_election_id = 0
        set_google_civic_election_id_cookie(request, response, google_civic_election_id)

        return response

    status += results['status'] + ", "
    # If here, we saved a valid address

    google_civic_election_id = get_google_civic_election_id_from_cookie(request)

    if positive_value_exists(google_civic_election_id):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        if google_civic_election_id == 2000:
            use_test_election = True
        else:
            use_test_election = False
    else:
        use_test_election = False

    results = voter_ballot_items_retrieve_from_google_civic_for_api(voter_device_id, text_for_map_search,
                                                                    use_test_election)

    status += results['status']
    google_civic_election_id = results['google_civic_election_id']

    json_data = {
        'status': status,
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'text_for_map_search': text_for_map_search,
        'voter_address_saved': voter_address_saved,
        'google_civic_election_id': google_civic_election_id,
    }

    response = HttpResponse(json.dumps(json_data), content_type='application/json')

    # Reset google_civic_election_id to the new election whenever we save a new address
    set_google_civic_election_id_cookie(request, response, google_civic_election_id)

    return response


def voter_ballot_items_retrieve_view(request):
    """
    (voterBallotItemsRetrieve) Request a skeleton of ballot data for this voter location,
    so that the web_app has all of the ids it needs to make more requests for data about each ballot item.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    # If passed in, we want to look at
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    use_test_election = request.GET.get('use_test_election', False)
    use_test_election = False if use_test_election == 'false' else use_test_election
    use_test_election = False if use_test_election == 'False' else use_test_election

    if positive_value_exists(use_test_election):
        google_civic_election_id = 2000  # The Google Civic API Test election
    elif not positive_value_exists(google_civic_election_id):
        # We look in the cookies for google_civic_election_id
        google_civic_election_id = get_google_civic_election_id_from_cookie(request)

    # This 'voter_ballot_items_retrieve_for_api' lives in apis_v1/controllers.py
    results = voter_ballot_items_retrieve_for_api(voter_device_id, google_civic_election_id)
    response = HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    # Save google_civic_election_id in the cookie so the interface knows
    google_civic_election_id_from_ballot_retrieve = results['google_civic_election_id']
    if positive_value_exists(google_civic_election_id_from_ballot_retrieve):
        set_google_civic_election_id_cookie(request, response, results['google_civic_election_id'])

    return response


def voter_ballot_items_retrieve_from_google_civic_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    text_for_map_search = request.GET.get('text_for_map_search', '')
    use_test_election = request.GET.get('use_test_election', False)
    use_test_election = False if use_test_election == 'false' else use_test_election
    use_test_election = False if use_test_election == 'False' else use_test_election

    results = voter_ballot_items_retrieve_from_google_civic_for_api(
        voter_device_id, text_for_map_search, use_test_election)

    response = HttpResponse(json.dumps(results), content_type='application/json')

    # Save google_civic_election_id in the cookie so the interface knows
    google_civic_election_id_from_ballot_retrieve = results['google_civic_election_id']
    if positive_value_exists(google_civic_election_id_from_ballot_retrieve):
        set_google_civic_election_id_cookie(request, response, results['google_civic_election_id'])

    return response


def voter_count_view(request):
    return voter_count()


def voter_create_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    return voter_create(voter_device_id)


def voter_guide_possibility_retrieve_view(request):
    """
    Retrieve a previously saved website that may contain a voter guide (voterGuidePossibilityRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    voter_guide_possibility_url = request.GET.get('voter_guide_possibility_url', '')
    return voter_guide_possibility_retrieve_for_api(voter_device_id=voter_device_id,
                                                    voter_guide_possibility_url=voter_guide_possibility_url)


def voter_guide_possibility_save_view(request):
    """
    Save a website that may contain a voter guide (voterGuidePossibilitySave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    voter_guide_possibility_url = request.POST.get('voter_guide_possibility_url', '')
    return voter_guide_possibility_save_for_api(voter_device_id=voter_device_id,
                                                voter_guide_possibility_url=voter_guide_possibility_url)


def voter_guides_followed_retrieve_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_followed_retrieve_for_api(voter_device_id=voter_device_id,
                                                  maximum_number_to_retrieve=maximum_number_to_retrieve)


def voter_guides_to_follow_retrieve_view(request):  # voterGuidesToFollowRetrieve
    """
    Retrieve a list of voter_guides that a voter might want to follow (voterGuidesToFollow)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', '')
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', '')
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    use_test_election = request.GET.get('use_test_election', False)
    use_test_election = False if use_test_election == 'false' else use_test_election
    use_test_election = False if use_test_election == 'False' else use_test_election
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)

    if positive_value_exists(ballot_item_we_vote_id):
        google_civic_election_id = 0
    if positive_value_exists(use_test_election):
        google_civic_election_id = 2000  # The Google Civic API Test election
    elif not positive_value_exists(google_civic_election_id):
        # We look in the cookies for google_civic_election_id
        google_civic_election_id = get_google_civic_election_id_from_cookie(request)
        # TODO DALE Consider getting this to work
        # # If the google_civic_election_id was found cached in a cookie and passed in, use that
        # # If not, fetch it for this voter by looking in the BallotItem table
        # if not positive_value_exists(google_civic_election_id):
        #     google_civic_election_id = fetch_google_civic_election_id_for_voter_id(voter_id)

    results = voter_guides_to_follow_retrieve_for_api(voter_device_id, kind_of_ballot_item, ballot_item_we_vote_id,
                                                      google_civic_election_id, maximum_number_to_retrieve)
    response = HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    # Save google_civic_election_id with fresh version that we retrieved from BallotItem table (if not passed in)
    set_google_civic_election_id_cookie(request, response, results['google_civic_election_id'])

    return response


def voter_location_retrieve_from_ip_view(request):  # GeoIP geo location
    """
    Take the IP address and return a location (voterLocationRetrieveFromIP)
    :param request:
    :return:
    """
    ip_address = request.GET.get('ip_address') or get_ip_from_headers(request)
    if ip_address is None:
        # return HttpResponse('missing ip_address request parameter', status=400)
        response_content = {
            'success': False,
            'status': 'missing ip_address request parameter',
            'voter_location_found': False,
            'voter_location': '',
            'ip_address': ip_address,
        }

        return HttpResponse(json.dumps(response_content), content_type='application/json')

    return voter_location_retrieve_from_ip_for_api(ip_address=ip_address)


def voter_photo_save_view(request):
    """
    Save or update a photo for this voter
    :param request:
    :return:
    """

    status = ''

    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    try:
        facebook_profile_image_url_https = request.GET['facebook_profile_image_url_https']
        facebook_profile_image_url_https = facebook_profile_image_url_https.strip()
        facebook_photo_variable_exists = True
    except KeyError:
        facebook_profile_image_url_https = ''
        facebook_photo_variable_exists = False

    results = voter_photo_save_for_api(voter_device_id,
                                       facebook_profile_image_url_https, facebook_photo_variable_exists)
    voter_photo_saved = True if results['success'] else False

    if not positive_value_exists(facebook_profile_image_url_https):
        json_data = {
            'status': results['status'],
            'success': results['success'],
            'voter_device_id': voter_device_id,
            'facebook_profile_image_url_https': facebook_profile_image_url_https,
            'voter_photo_saved': voter_photo_saved,
        }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')

        return response

    status += results['status'] + ", "
    # If here, we saved a valid photo

    json_data = {
        'status': status,
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'facebook_profile_image_url_https': facebook_profile_image_url_https,
        'voter_photo_saved': voter_photo_saved,
    }

    response = HttpResponse(json.dumps(json_data), content_type='application/json')

    return response


def voter_position_retrieve_view(request):
    """
    Retrieve all of the details about a single position based on unique identifier. voterPositionRetrieve
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    # ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_we_vote_id = ballot_item_we_vote_id
        candidate_we_vote_id = ''
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_we_vote_id = ''
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_we_vote_id = ''
        candidate_we_vote_id = ''
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_we_vote_id = ''
        candidate_we_vote_id = ''
        measure_we_vote_id = ''
    return voter_position_retrieve_for_api(
        voter_device_id=voter_device_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id
    )


def voter_position_like_off_save_view(request):
    """
    Un-mark the position_like for a single position for one voter (voterPositionLikeOffSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    position_like_id = request.GET.get('position_like_id', 0)
    position_entered_id = request.GET.get('position_entered_id', 0)
    return voter_position_like_off_save_for_api(
        voter_device_id=voter_device_id, position_like_id=position_like_id, position_entered_id=position_entered_id)


def voter_position_like_on_save_view(request):
    """
    Mark the position_like for a single position for one voter (voterPositionLikeOnSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    position_entered_id = request.GET.get('position_entered_id', 0)
    return voter_position_like_on_save_for_api(
        voter_device_id=voter_device_id, position_entered_id=position_entered_id)


def voter_position_like_status_retrieve_view(request):
    """
    Retrieve whether or not a position_like is marked for position (voterPositionLikeStatusRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    position_entered_id = request.GET.get('position_entered_id', 0)
    return voter_position_like_status_retrieve_for_api(
        voter_device_id=voter_device_id, position_entered_id=position_entered_id)


def position_like_count_view(request):
    """
    Retrieve the total number of Likes that a position has received, either from the perspective of the voter's
    network of friends, or the entire network. (positionLikeCount)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    position_entered_id = request.GET.get('position_entered_id', 0)
    limit_to_voters_network = request.GET.get('limit_to_voters_network', False)
    return position_like_count_for_api(voter_device_id=voter_device_id, position_entered_id=position_entered_id,
                                       limit_to_voters_network=limit_to_voters_network)


def voter_position_comment_save_view(request):
    """
    Save a single position
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    position_id = request.POST.get('position_id', False)
    position_we_vote_id = request.POST.get('position_we_vote_id', False)
    google_civic_election_id = request.POST.get('google_civic_election_id', False)
    office_we_vote_id = request.POST.get('office_we_vote_id', False)
    candidate_we_vote_id = request.POST.get('candidate_we_vote_id', False)
    measure_we_vote_id = request.POST.get('measure_we_vote_id', False)
    statement_text = request.POST.get('statement_text', False)
    statement_html = request.POST.get('statement_html', False)

    results = voter_position_comment_save_for_api(
        voter_device_id=voter_device_id,
        position_id=position_id,
        position_we_vote_id=position_we_vote_id,
        google_civic_election_id=google_civic_election_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        statement_text=statement_text,
        statement_html=statement_html,
    )

    return HttpResponse(json.dumps(results), content_type='application/json')


def voter_opposing_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterOpposingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        candidate_id = 0
        measure_id = 0
    return voter_opposing_save(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


class VoterExportView(APIView):
    """
    Export raw voter data to JSON format
    """
    def get(self, request):  # Removed: , format=None
        voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
        results = voter_retrieve_list_for_api(voter_device_id)

        if 'success' not in results:
            json_data = results['json_data']
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        elif not results['success']:
            json_data = results['json_data']
            return HttpResponse(json.dumps(json_data), content_type='application/json')
        else:
            voter_list = results['voter_list']
            serializer = VoterSerializer(voter_list, many=True)
            return Response(serializer.data)


def voter_retrieve_view(request):
    """
    Retrieve a single voter based on voter_device
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    results = voter_retrieve_for_api(voter_device_id=voter_device_id)
    return HttpResponse(json.dumps(results), content_type='application/json')


def voter_stop_opposing_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterStopOpposingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        candidate_id = 0
        measure_id = 0
    return voter_stop_opposing_save(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


def voter_stop_supporting_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterStopSupportingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        candidate_id = 0
        measure_id = 0
    return voter_stop_supporting_save(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


def voter_supporting_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterSupportingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        candidate_id = 0
        measure_id = 0
    return voter_supporting_save_for_api(
        voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


def voter_star_off_save_view(request):
    """
    Un-mark the star for a single measure, office or candidate for one voter (voterStarOffSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        candidate_id = 0
        measure_id = 0
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        office_id = 0
        candidate_id = 0
        measure_id = 0
    return voter_star_off_save_for_api(
        voter_device_id=voter_device_id, office_id=office_id, candidate_id=candidate_id, measure_id=measure_id)


def voter_star_on_save_view(request):
    """
    Mark the star for a single measure, office or candidate for one voter (voterStarOnSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        candidate_id = 0
        measure_id = 0
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        office_id = 0
        candidate_id = 0
        measure_id = 0
    return voter_star_on_save_for_api(
        voter_device_id=voter_device_id, office_id=office_id, candidate_id=candidate_id, measure_id=measure_id)


def voter_star_status_retrieve_view(request):
    """
    Retrieve whether or not a star is marked for an office, candidate or measure based on unique identifier
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    # ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        candidate_id = 0
        measure_id = 0
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        candidate_id = ballot_item_id
        measure_id = 0
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        candidate_id = 0
        measure_id = ballot_item_id
    else:
        office_id = 0
        candidate_id = 0
        measure_id = 0
    return voter_star_status_retrieve_for_api(
        voter_device_id=voter_device_id,
        office_id=office_id,
        candidate_id=candidate_id,
        measure_id=measure_id,
    )
