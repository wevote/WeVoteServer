# apis_v1/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import organization_count, organization_follow, organization_follow_ignore, \
    organization_stop_following, voter_count
from ballot.controllers import ballot_item_options_retrieve_for_api, choose_election_from_existing_data, \
    figure_out_google_civic_election_id_voter_is_watching, voter_ballot_items_retrieve_for_api
from candidate.controllers import candidate_retrieve_for_api, candidates_retrieve_for_api
from config.base import get_environment_variable
from django.http import HttpResponse, HttpResponseRedirect
from geoip.controllers import voter_location_retrieve_from_ip_for_api
from import_export_facebook.controllers import facebook_disconnect_for_api, facebook_sign_in_for_api
from import_export_google_civic.controllers import voter_ballot_items_retrieve_from_google_civic_for_api
from import_export_twitter.controllers import twitter_sign_in_start_for_api, \
    twitter_sign_in_request_access_token_for_api, twitter_sign_in_request_voter_info_for_api
import json
from measure.controllers import measure_retrieve_for_api
from office.controllers import office_retrieve_for_api
from organization.controllers import organization_retrieve_for_api, organization_save_for_api, \
    organization_search_for_api, organizations_followed_retrieve_for_api
from position.controllers import position_list_for_ballot_item_for_api, position_list_for_opinion_maker_for_api, \
    position_list_for_voter_for_api, \
    position_retrieve_for_api, position_save_for_api, voter_all_positions_retrieve_for_api, \
    voter_position_retrieve_for_api, voter_position_comment_save_for_api, voter_position_visibility_save_for_api
from position.models import ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING, \
    FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC
from position_like.controllers import position_like_count_for_api, voter_position_like_off_save_for_api, \
    voter_position_like_on_save_for_api, voter_position_like_status_retrieve_for_api
from quick_info.controllers import quick_info_retrieve_for_api
from ballot.controllers import choose_election_and_prepare_ballot_data
from ballot.models import OFFICE, CANDIDATE, MEASURE, VoterBallotSavedManager
from rest_framework.response import Response
from rest_framework.views import APIView
from search.controllers import search_all_for_api
from star.controllers import voter_all_stars_status_retrieve_for_api, voter_star_off_save_for_api, \
    voter_star_on_save_for_api, voter_star_status_retrieve_for_api
from support_oppose_deciding.controllers import position_oppose_count_for_ballot_item_for_api, \
    position_support_count_for_ballot_item_for_api, \
    position_public_oppose_count_for_ballot_item_for_api, \
    position_public_support_count_for_ballot_item_for_api, positions_count_for_all_ballot_items_for_api, \
    positions_count_for_one_ballot_item_for_api, \
    voter_opposing_save, voter_stop_opposing_save, voter_stop_supporting_save, voter_supporting_save_for_api
from twitter.controllers import twitter_identity_retrieve_for_api
from voter.controllers import voter_address_retrieve_for_api, voter_create_for_api, \
    voter_photo_save_for_api, voter_retrieve_for_api, voter_retrieve_list_for_api, voter_sign_out_for_api
from voter.models import BALLOT_ADDRESS, fetch_voter_id_from_voter_device_link, VoterAddress, VoterAddressManager, \
    VoterDeviceLink, VoterDeviceLinkManager, voter_has_authority, VoterManager
from voter.serializers import VoterSerializer
from voter_guide.controllers import voter_guide_possibility_retrieve_for_api, voter_guide_possibility_save_for_api, \
    voter_guides_followed_retrieve_for_api, voter_guides_to_follow_retrieve_for_api
from voter_guide.models import ORGANIZATION, PUBLIC_FIGURE
import wevote_functions.admin
from wevote_functions.functions import convert_to_bool, convert_to_int, generate_voter_device_id, get_voter_device_id, \
    is_voter_device_id_valid, positive_value_exists


logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def ballot_item_options_retrieve_view(request):  # ballotItemOptionsRetrieve
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    results = ballot_item_options_retrieve_for_api(google_civic_election_id)
    response = HttpResponse(json.dumps(results['json_data']), content_type='application/json')
    return response


def ballot_item_retrieve_view(request):  # ballotItemRetrieve
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


def candidate_retrieve_view(request):  # candidateRetrieve
    candidate_id = request.GET.get('candidate_id', 0)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', None)
    return candidate_retrieve_for_api(candidate_id, candidate_we_vote_id)


def candidates_retrieve_view(request):  # candidatesRetrieve
    office_id = request.GET.get('office_id', 0)
    office_we_vote_id = request.GET.get('office_we_vote_id', '')
    return candidates_retrieve_for_api(office_id, office_we_vote_id)


def device_id_generate_view(request):  # deviceIdGenerate
    """
    This API call is used by clients to generate a transient unique identifier (device_id - stored on client)
    which ties the device to a persistent voter_id (mapped together and stored on the server).
    Note: This call does not create a voter account -- that must be done in voterCreate.

    :param request:
    :return: Unique device id that can be stored in a cookie
    """
    voter_device_id = generate_voter_device_id()  # Stored in cookie elsewhere
    logger.debug("apis_v1/views.py, device_id_generate-voter_device_id: {voter_device_id}".format(
        voter_device_id=voter_device_id
    ))

    if positive_value_exists(voter_device_id):
        success = True
        status = "DEVICE_ID_GENERATE_VALUE_DOES_NOT_EXIST"
    else:
        success = False
        status = "DEVICE_ID_GENERATE_VALUE_EXISTS"

    json_data = {
        'voter_device_id': voter_device_id,
        'success': success,
        'status': status,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def facebook_disconnect_view(request):
    """
    Disconnect this We Vote account from current Facebook account
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = facebook_disconnect_for_api(voter_device_id)
    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def facebook_sign_in_view(request):  # facebookSignIn
    """
    Saving the results of signing in with Facebook
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
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


def measure_retrieve_view(request):  # measureRetrieve
    measure_id = request.GET.get('measure_id', 0)
    measure_we_vote_id = request.GET.get('measure_we_vote_id', None)
    return measure_retrieve_for_api(measure_id, measure_we_vote_id)


def office_retrieve_view(request):  # officeRetrieve
    office_id = request.GET.get('office_id', 0)
    office_we_vote_id = request.GET.get('office_we_vote_id', None)
    return office_retrieve_for_api(office_id, office_we_vote_id)


def organization_count_view(request):
    return organization_count()


def organization_follow_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    return organization_follow(voter_device_id=voter_device_id, organization_id=organization_id,
                               organization_we_vote_id=organization_we_vote_id)


def organization_stop_following_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    return organization_stop_following(voter_device_id=voter_device_id, organization_id=organization_id,
                                       organization_we_vote_id=organization_we_vote_id)


def organization_follow_ignore_api_view(request):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    return organization_follow_ignore(voter_device_id=voter_device_id, organization_id=organization_id,
                                      organization_we_vote_id=organization_we_vote_id)


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


def organization_save_view(request):  # organizationSave
    """
    Save a single organization based on unique identifier
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    organization_id = request.GET.get('organization_id', 0)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', '')
    organization_name = request.GET.get('organization_name', False)
    organization_email = request.GET.get('organization_email', False)
    organization_website = request.GET.get('organization_website', False)
    organization_facebook = request.GET.get('organization_facebook', False)
    organization_image = request.GET.get('organization_image', False)

    # We only want to allow save if either this is your organization (i.e., you have the Twitter handle)
    voter_owns_twitter_handle = False
    voter_owns_facebook_id = False

    # Twitter specific
    organization_twitter_handle = request.GET.get('organization_twitter_handle', False)
    refresh_from_twitter = request.GET.get('refresh_from_twitter', False)

    # Facebook specific
    facebook_id = request.GET.get('facebook_id', False)
    if facebook_id is not False:
        facebook_id = convert_to_int(facebook_id)
    facebook_email = request.GET.get('facebook_email', False)
    facebook_profile_image_url_https = request.GET.get('facebook_profile_image_url_https', False)

    #  or if you are a verified volunteer or admin
    authority_required = {'admin', 'verified_volunteer'}  # admin, verified_volunteer
    voter_is_admin_or_verified_volunteer = False
    if voter_has_authority(request, authority_required):
        voter_is_admin_or_verified_volunteer = True
    else:
        voter_manager = VoterManager()
        voter_results = voter_manager.retrieve_voter_from_voter_device_id(voter_device_id)
        if voter_results['voter_found']:
            voter = voter_results['voter']

            # Does this voter have the same Twitter handle as this organization? If so, link this organization to
            #  this particular voter
            if positive_value_exists(voter.facebook_id) \
                    and voter.facebook_id == facebook_id:
                # This will fail if the organization's facebook_id isn't passed in as a variable
                voter_owns_facebook_id = True

            # Does this voter have the same Twitter handle as this organization? If so, link this organization to
            #  this particular voter
            if positive_value_exists(voter.twitter_screen_name) \
                    and voter.twitter_screen_name.lower() == organization_twitter_handle.lower():
                # This will fail if the organization's twitter handle isn't passed in as a variable
                voter_owns_twitter_handle = True

    if not voter_is_admin_or_verified_volunteer:
        if not voter_owns_twitter_handle and not voter_owns_facebook_id:
            # Only refuse entry if *both* conditions are not met
            results = {
                'status': "VOTER_LACKS_AUTHORITY_TO_SAVE_ORGANIZATION",
                'success': False,
                'organization_id': organization_id,
                'organization_we_vote_id': organization_we_vote_id,
                'new_organization_created': False,
                'organization_name': organization_name,
                'organization_email': organization_email,
                'organization_website': organization_website,
                'organization_facebook': organization_facebook,
                'organization_photo_url': organization_image,
                'organization_twitter_handle': organization_twitter_handle,
                'refresh_from_twitter': refresh_from_twitter,
                'twitter_followers_count': 0,
                'twitter_description': "",
                'facebook_id': facebook_id,
                'facebook_email': facebook_email,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
            }
            return HttpResponse(json.dumps(results), content_type='application/json')

    results = organization_save_for_api(
        voter_device_id=voter_device_id, organization_id=organization_id,
        organization_we_vote_id=organization_we_vote_id,
        organization_name=organization_name, organization_email=organization_email,
        organization_website=organization_website, organization_twitter_handle=organization_twitter_handle,
        organization_facebook=organization_facebook, organization_image=organization_image,
        refresh_from_twitter=refresh_from_twitter,
        facebook_id=facebook_id, facebook_email=facebook_email,
        facebook_profile_image_url_https=facebook_profile_image_url_https,
    )

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
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return organizations_followed_retrieve_for_api(voter_device_id=voter_device_id,
                                                   maximum_number_to_retrieve=maximum_number_to_retrieve)


def get_maximum_number_to_retrieve_from_request(request):
    if 'maximum_number_to_retrieve' in request.GET:
        maximum_number_to_retrieve = request.GET['maximum_number_to_retrieve']
    else:
        maximum_number_to_retrieve = 40
    if maximum_number_to_retrieve is "":
        maximum_number_to_retrieve = 40
    else:
        maximum_number_to_retrieve = convert_to_int(maximum_number_to_retrieve)

    return maximum_number_to_retrieve


def position_list_for_ballot_item_view(request):  # positionListForBallotItem
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    stance = request.GET.get('stance', ANY_STANCE)
    if stance in (ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
        stance_we_are_looking_for = stance
    else:
        stance_we_are_looking_for = ANY_STANCE

    friends_vs_public_incoming = request.GET.get('friends_vs_public', FRIENDS_AND_PUBLIC)
    if friends_vs_public_incoming in (FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC):
        friends_vs_public = friends_vs_public_incoming
    else:
        friends_vs_public = FRIENDS_AND_PUBLIC

    show_positions_this_voter_follows = request.GET.get('show_positions_this_voter_follows', True)
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', "")
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        office_we_vote_id = ballot_item_we_vote_id
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    return position_list_for_ballot_item_for_api(voter_device_id=voter_device_id,
                                                 friends_vs_public=friends_vs_public,
                                                 office_id=office_id,
                                                 office_we_vote_id=office_we_vote_id,
                                                 candidate_id=candidate_id,
                                                 candidate_we_vote_id=candidate_we_vote_id,
                                                 measure_id=measure_id,
                                                 measure_we_vote_id=measure_we_vote_id,
                                                 stance_we_are_looking_for=stance_we_are_looking_for,
                                                 show_positions_this_voter_follows=show_positions_this_voter_follows)


def position_list_for_opinion_maker_view(request):  # positionListForOpinionMaker
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    stance = request.GET.get('stance', ANY_STANCE)
    if stance in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
        stance_we_are_looking_for = stance
    else:
        stance_we_are_looking_for = ANY_STANCE
    friends_vs_public_incoming = request.GET.get('friends_vs_public', ANY_STANCE)
    if friends_vs_public_incoming in (FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC):
        friends_vs_public = friends_vs_public_incoming
    else:
        friends_vs_public = FRIENDS_AND_PUBLIC
    kind_of_opinion_maker = request.GET.get('kind_of_opinion_maker', "")
    opinion_maker_id = request.GET.get('opinion_maker_id', 0)
    opinion_maker_we_vote_id = request.GET.get('opinion_maker_we_vote_id', "")
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")
    filter_for_voter = request.GET.get('filter_for_voter', True)
    filter_for_voter = convert_to_bool(filter_for_voter)
    filter_out_voter = request.GET.get('filter_out_voter', False)
    filter_out_voter = convert_to_bool(filter_out_voter)
    # Make sure filter_for_voter is reset to False if filter_out_voter is true
    filter_for_voter = False if filter_out_voter else filter_for_voter
    if (kind_of_opinion_maker == ORGANIZATION) or (kind_of_opinion_maker == "ORGANIZATION"):
        organization_id = opinion_maker_id
        organization_we_vote_id = opinion_maker_we_vote_id
        public_figure_id = 0
        public_figure_we_vote_id = ''
    elif (kind_of_opinion_maker == PUBLIC_FIGURE) or (kind_of_opinion_maker == "PUBLIC_FIGURE"):
        organization_id = 0
        organization_we_vote_id = ''
        public_figure_id = opinion_maker_id
        public_figure_we_vote_id = opinion_maker_we_vote_id
    else:
        organization_id = 0
        organization_we_vote_id = ''
        public_figure_id = 0
        public_figure_we_vote_id = ''
    return position_list_for_opinion_maker_for_api(voter_device_id=voter_device_id,
                                                   organization_id=organization_id,
                                                   organization_we_vote_id=organization_we_vote_id,
                                                   public_figure_id=public_figure_id,
                                                   public_figure_we_vote_id=public_figure_we_vote_id,
                                                   friends_vs_public=friends_vs_public,
                                                   stance_we_are_looking_for=stance_we_are_looking_for,
                                                   filter_for_voter=filter_for_voter,
                                                   filter_out_voter=filter_out_voter,
                                                   google_civic_election_id=google_civic_election_id,
                                                   state_code=state_code)


def position_list_for_voter_view(request):  # positionListForVoter
    """
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    stance = request.GET.get('stance', ANY_STANCE)
    if stance in(ANY_STANCE, SUPPORT, STILL_DECIDING, INFORMATION_ONLY, NO_STANCE, OPPOSE, PERCENT_RATING):
        stance_we_are_looking_for = stance
    else:
        stance_we_are_looking_for = ANY_STANCE
    friends_vs_public_incoming = request.GET.get('friends_vs_public', ANY_STANCE)
    if friends_vs_public_incoming in (FRIENDS_ONLY, PUBLIC_ONLY, FRIENDS_AND_PUBLIC):
        friends_vs_public = friends_vs_public_incoming
    else:
        friends_vs_public = FRIENDS_AND_PUBLIC
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)
    state_code = request.GET.get('state_code', "")
    show_only_this_election = request.GET.get('show_only_this_election', True)
    show_only_this_election = convert_to_bool(show_only_this_election)
    show_all_other_elections = request.GET.get('show_all_other_elections', False)
    show_all_other_elections = convert_to_bool(show_all_other_elections)
    # Make sure show_only_this_election is reset to False if filter_out_voter is true
    show_only_this_election = False if show_all_other_elections else show_only_this_election
    if show_only_this_election or show_all_other_elections and not positive_value_exists(google_civic_election_id):
        results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
        google_civic_election_id = results['google_civic_election_id']
    return position_list_for_voter_for_api(voter_device_id=voter_device_id,
                                           friends_vs_public=friends_vs_public,
                                           stance_we_are_looking_for=stance_we_are_looking_for,
                                           show_only_this_election=show_only_this_election,
                                           show_all_other_elections=show_all_other_elections,
                                           google_civic_election_id=google_civic_election_id,
                                           state_code=state_code)


def position_retrieve_view(request):
    """
    Retrieve all of the details about a single position based on unique identifier (positionRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_we_vote_id = request.GET.get('position_we_vote_id', '')
    return position_retrieve_for_api(
        position_we_vote_id=position_we_vote_id,
        voter_device_id=voter_device_id
    )


def position_save_view(request):  # positionSave
    """
    Save a single position
    :param request:
    :return:
    """
    # We set values that aren't passed in, to False so we know to treat them as null or unchanged. This allows us to
    #  only change the values we want to
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_we_vote_id = request.GET.get('position_we_vote_id', False)
    organization_we_vote_id = request.GET.get('organization_we_vote_id', False)
    public_figure_we_vote_id = request.GET.get('public_figure_we_vote_id', False)
    voter_we_vote_id = request.GET.get('voter_we_vote_id', False)
    google_civic_election_id = request.GET.get('google_civic_election_id', False)
    ballot_item_display_name = request.GET.get('ballot_item_display_name', False)
    office_we_vote_id = request.GET.get('office_we_vote_id', False)
    candidate_we_vote_id = request.GET.get('candidate_we_vote_id', False)
    measure_we_vote_id = request.GET.get('measure_we_vote_id', False)
    stance = request.GET.get('stance', False)
    set_as_public_position = request.GET.get('set_as_public_position', True)
    statement_text = request.GET.get('statement_text', False)
    statement_html = request.GET.get('statement_html', False)
    more_info_url = request.GET.get('more_info_url', False)

    results = position_save_for_api(
        voter_device_id=voter_device_id,
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
        set_as_public_position=set_as_public_position,
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
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return position_oppose_count_for_ballot_item_for_api(
        voter_device_id=voter_device_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def position_support_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and friends that support this (positionSupportCountForBallotItem)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return position_support_count_for_ballot_item_for_api(
        voter_device_id=voter_device_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def position_public_oppose_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and public figures that publicly oppose this (positionPublicOpposeCountForBallotItem)
    :param request:
    :return:
    """
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return position_public_oppose_count_for_ballot_item_for_api(
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def position_public_support_count_for_ballot_item_view(request):
    """
    Retrieve the number of orgs and public figures that publicly support this (positionPublicSupportCountForBallotItem)
    :param request:
    :return:
    """
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return position_public_support_count_for_ballot_item_for_api(
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def positions_count_for_all_ballot_items_view(request):  # positionsCountForAllBallotItems
    """
    Retrieve the number of support/oppose positions from the voter's network
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    results = positions_count_for_all_ballot_items_for_api(
        voter_device_id=voter_device_id,
        google_civic_election_id=google_civic_election_id)
    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'position_counts_list': results['position_counts_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def positions_count_for_one_ballot_item_view(request):  # positionsCountForOneBallotItem
    """
    Retrieve the number of support/oppose positions from the voter's network for one ballot item
    We return results in the same format as positions_count_for_all_ballot_items_view
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', "")

    results = positions_count_for_one_ballot_item_for_api(
        voter_device_id=voter_device_id,
        ballot_item_we_vote_id=ballot_item_we_vote_id)
    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'position_counts_list': results['position_counts_list'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


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


def search_all_view(request):
    """
    Find information anywhere in the We Vote universe.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    text_from_search_field = request.GET.get('text_from_search_field', '')

    if not positive_value_exists(text_from_search_field):
        status = 'MISSING_TEXT_FROM_SEARCH_FIELD'
        json_data = {
            'status':                   status,
            'success':                  False,
            'text_from_search_field':   text_from_search_field,
            'voter_device_id':          voter_device_id,
            'search_results':           [],
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = search_all_for_api(text_from_search_field, voter_device_id)
    status = "UNABLE_TO_FIND_ANY_SEARCH_RESULTS "
    search_results = []
    if results['search_results_found']:
        search_results = results['search_results']
        status = results['status']
    else:
        status += results['status']

    json_data = {
        'status':                   status,
        'success':                  True,
        'text_from_search_field':   text_from_search_field,
        'voter_device_id':          voter_device_id,
        'search_results':           search_results,
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_identity_retrieve_view(request):
    """
    Find the kind of owner and unique id of this twitter handle. We use this to take an incoming URI like
    https://wevote.guide/RepBarbaraLee and return the owner of 'RepBarbaraLee'. (twitterIdentityRetrieve)
    :param request:
    :return:
    """
    twitter_handle = request.GET.get('twitter_handle', '')

    if not positive_value_exists(twitter_handle):
        status = 'VALID_TWITTER_HANDLE_MISSING'
        json_data = {
            'status':                   status,
            'success':                  False,
            'twitter_handle':           twitter_handle,
            'owner_found':              False,
            'kind_of_owner':            '',
            'owner_we_vote_id':         '',
            'owner_id':                 0,
            'google_civic_election_id': 0,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = twitter_identity_retrieve_for_api(twitter_handle, voter_device_id)
    json_data = {
        'status':                   results['status'],
        'success':                  results['success'],
        'twitter_handle':           results['twitter_handle'],
        'owner_found':              results['owner_found'],
        'kind_of_owner':            results['kind_of_owner'],
        'owner_we_vote_id':         results['owner_we_vote_id'],
        'owner_id':                 results['owner_id'],
        'google_civic_election_id': results['google_civic_election_id'],
        # These values only returned if kind_of_owner == TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE
        'twitter_description':      results['twitter_description'],
        'twitter_followers_count':  results['twitter_followers_count'],
        'twitter_photo_url':        results['twitter_photo_url'],
        'twitter_user_website':     results['twitter_user_website'],
        'twitter_name':             results['twitter_name'],
        }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_start_view(request):
    """
    Start off the process of signing in with Twitter (twitterSignInStart)
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return_url = request.GET.get('return_url', '')

    results = twitter_sign_in_start_for_api(voter_device_id, return_url)
    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'voter_device_id':      voter_device_id,
        'twitter_redirect_url': results['twitter_redirect_url'],
        'voter_info_retrieved': results['voter_info_retrieved'],
        'switch_accounts':      results['switch_accounts'],  # If true, new voter_device_id returned
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_request_access_token_view(request):
    """
    Step 2 of the Twitter Sign In Process (twitterSignInRequestAccessToken)
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    incoming_request_token = request.GET.get('oauth_token', '')
    incoming_oauth_verifier = request.GET.get('oauth_verifier', '')
    return_url = request.GET.get('return_url', '')

    results = twitter_sign_in_request_access_token_for_api(voter_device_id,
                                                           incoming_request_token, incoming_oauth_verifier,
                                                           return_url)

    if positive_value_exists(results['return_url']):
        next_step_url = WE_VOTE_SERVER_ROOT_URL + "/apis/v1/twitterSignInRequestVoterInfo/"
        next_step_url += "?voter_device_id=" + voter_device_id
        next_step_url += "&return_url=" + results['return_url']
        return HttpResponseRedirect(next_step_url)

    json_data = {
        'status': results['status'],
        'success': results['success'],
        'voter_device_id': voter_device_id,
        'access_token_and_secret_returned': results['access_token_and_secret_returned'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def twitter_sign_in_request_voter_info_view(request):
    """
    Step 3 of the Twitter Sign In Process (twitterSignInRequestVoterInfo)
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return_url = request.GET.get('return_url', '')

    results = twitter_sign_in_request_voter_info_for_api(voter_device_id, return_url)

    if positive_value_exists(results['return_url']):
        modified_return_url = results['return_url']
        if results['twitter_handle_found']:
            modified_return_url = modified_return_url.replace("signinswitchend", "signinswitchend/" +
                                                              results['twitter_handle'])
        return HttpResponseRedirect(modified_return_url)

    json_data = {
        'status':               results['status'],
        'success':              results['success'],
        'voter_device_id':      results['voter_device_id'],
        'twitter_handle':       results['twitter_handle'],
        'twitter_handle_found': results['twitter_handle_found'],
        'voter_info_retrieved': results['voter_info_retrieved'],
        'switch_accounts':      results['switch_accounts'],
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_address_retrieve_view(request):  # voterAddressRetrieveView
    """
    Retrieve an address for this voter so we can figure out which ballot to display
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    guess_if_no_address_saved = request.GET.get('guess_if_no_address_saved', True)
    if guess_if_no_address_saved == 'false':
        guess_if_no_address_saved = False
    elif guess_if_no_address_saved == 'False':
        guess_if_no_address_saved = False
    elif guess_if_no_address_saved == '0':
        guess_if_no_address_saved = False
    status = ''

    voter_address_manager = VoterAddressManager()
    voter_device_link_manager = VoterDeviceLinkManager()

    voter_address_retrieve_results = voter_address_retrieve_for_api(voter_device_id)

    if voter_address_retrieve_results['address_found']:
        status += voter_address_retrieve_results['status']
        if positive_value_exists(voter_address_retrieve_results['google_civic_election_id']):
            google_civic_election_id = voter_address_retrieve_results['google_civic_election_id']
        else:
            # This block of code helps us if the google_civic_election_id hasn't been saved in the voter_address table
            # We retrieve voter_device_link
            google_civic_election_id = 0

        voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
        if voter_device_link_results['voter_device_link_found']:
            voter_device_link = voter_device_link_results['voter_device_link']
        else:
            voter_device_link = VoterDeviceLink()

        # Retrieve the voter_address
        voter_address_results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
        if voter_address_results['voter_address_found']:
            voter_address = voter_address_results['voter_address']
        else:
            voter_address = VoterAddress()

        results = choose_election_and_prepare_ballot_data(voter_device_link, google_civic_election_id,
                                                          voter_address)
        status += results['status']
        if results['voter_ballot_saved_found']:
            google_civic_election_id = results['google_civic_election_id']

        json_data = {
            'voter_device_id': voter_address_retrieve_results['voter_device_id'],
            'address_type': voter_address_retrieve_results['address_type'],
            'text_for_map_search': voter_address_retrieve_results['text_for_map_search'],
            'google_civic_election_id': google_civic_election_id,
            'latitude': voter_address_retrieve_results['latitude'],
            'longitude': voter_address_retrieve_results['longitude'],
            'normalized_line1': voter_address_retrieve_results['normalized_line1'],
            'normalized_line2': voter_address_retrieve_results['normalized_line2'],
            'normalized_city': voter_address_retrieve_results['normalized_city'],
            'normalized_state': voter_address_retrieve_results['normalized_state'],
            'normalized_zip': voter_address_retrieve_results['normalized_zip'],
            'success': voter_address_retrieve_results['success'],
            'status': voter_address_retrieve_results['status'],
            'address_found': voter_address_retrieve_results['address_found'],
            'guess_if_no_address_saved': guess_if_no_address_saved,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    status += voter_address_retrieve_results['status'] + ", "

    # If we are here, then an address wasn't found, and we either want to return that info, or take a guess
    #  at the voter's location by looking it up by IP address
    if not positive_value_exists(guess_if_no_address_saved):
        # Do not guess at an address
        status += 'DO_NOT_GUESS_IF_NO_ADDRESS_SAVED'
        json_data = {
            'voter_device_id': voter_device_id,
            'address_type': '',
            'text_for_map_search': '',
            'google_civic_election_id': 0,
            'latitude': '',
            'longitude': '',
            'normalized_line1': '',
            'normalized_line2': '',
            'normalized_city': '',
            'normalized_state': '',
            'normalized_zip': '',
            'success': voter_address_retrieve_results['success'],
            'status': voter_address_retrieve_results['status'],
            'address_found': voter_address_retrieve_results['address_found'],
            'guess_if_no_address_saved': guess_if_no_address_saved,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    else:
        status += 'GUESS_IF_NO_ADDRESS_SAVED' + ", "
        # If here, we are going to guess at the voter's location based on IP address
        voter_location_results = voter_location_retrieve_from_ip_for_api(request)

        if voter_location_results['voter_location_found']:
            status += 'VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_FOUND_FROM_IP '
            # Since a new location was found, we need to save the address and then reach out to Google Civic
            text_for_map_search = voter_location_results['voter_location']
            status += '*** ' + text_for_map_search + ' ***, '

            google_civic_election_id = 0

            voter_address_save_results = voter_address_manager.update_or_create_voter_address(
                voter_id, BALLOT_ADDRESS, text_for_map_search)
            status += voter_address_save_results['status'] + ", "

            if voter_address_save_results['success'] and voter_address_save_results['voter_address_found']:
                voter_address = voter_address_save_results['voter_address']
                use_test_election = False
                # Reach out to Google and populate ballot items in the database with fresh ballot data
                # NOTE: 2016-05-26 Google civic NEVER returns a ballot for City, State ZIP, so we could change this
                google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
                    voter_device_id, text_for_map_search, use_test_election)
                status += google_retrieve_results['status'] + ", "

                if positive_value_exists(google_retrieve_results['google_civic_election_id']):
                    # Update voter_address with the google_civic_election_id retrieved from Google Civic
                    # and clear out ballot_saved information
                    google_civic_election_id = google_retrieve_results['google_civic_election_id']

                    voter_address.google_civic_election_id = google_civic_election_id
                    voter_address_update_results = voter_address_manager.update_existing_voter_address_object(
                        voter_address)

                    if voter_address_update_results['success']:
                        # Replace the former google_civic_election_id from this voter_device_link
                        voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(
                            voter_device_id)
                        if voter_device_link_results['voter_device_link_found']:
                            voter_device_link = voter_device_link_results['voter_device_link']
                            voter_device_link_manager.update_voter_device_link_with_election_id(
                                voter_device_link, google_retrieve_results['google_civic_election_id'])

                else:
                    # This block of code helps us if the google_civic_election_id wasn't found when we reached out
                    # to the Google Civic API, following finding the voter's location from IP address.
                    google_civic_election_id = 0

            # We retrieve voter_device_link
            voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            if voter_device_link_results['voter_device_link_found']:
                voter_device_link = voter_device_link_results['voter_device_link']
            else:
                voter_device_link = VoterDeviceLink()

            # Retrieve the voter_address
            voter_address_results = voter_address_manager.retrieve_ballot_address_from_voter_id(voter_id)
            if voter_address_results['voter_address_found']:
                voter_address = voter_address_results['voter_address']
            else:
                voter_address = VoterAddress()

            results = choose_election_and_prepare_ballot_data(voter_device_link, google_civic_election_id,
                                                              voter_address)
            status += results['status']

            if results['voter_ballot_saved_found']:
                google_civic_election_id = results['google_civic_election_id']

            voter_address_retrieve_results = voter_address_retrieve_for_api(voter_device_id)

            status += voter_address_retrieve_results['status']
            if voter_address_retrieve_results['address_found']:
                json_data = {
                    'voter_device_id': voter_device_id,
                    'address_type': voter_address_retrieve_results['address_type'],
                    'text_for_map_search': voter_address_retrieve_results['text_for_map_search'],
                    'google_civic_election_id': google_civic_election_id,
                    'latitude': voter_address_retrieve_results['latitude'],
                    'longitude': voter_address_retrieve_results['longitude'],
                    'normalized_line1': voter_address_retrieve_results['normalized_line1'],
                    'normalized_line2': voter_address_retrieve_results['normalized_line2'],
                    'normalized_city': voter_address_retrieve_results['normalized_city'],
                    'normalized_state': voter_address_retrieve_results['normalized_state'],
                    'normalized_zip': voter_address_retrieve_results['normalized_zip'],
                    'success': voter_address_retrieve_results['success'],
                    'status': status,
                    'address_found': voter_address_retrieve_results['address_found'],
                    'guess_if_no_address_saved': guess_if_no_address_saved,
                }
            else:
                # Address not found from IP address
                status += 'VOTER_ADDRESS_RETRIEVE_PART2_NO_ADDRESS'
                json_data = {
                    'voter_device_id': voter_device_id,
                    'address_type': '',
                    'text_for_map_search': '',
                    'google_civic_election_id': 0,
                    'latitude': '',
                    'longitude': '',
                    'normalized_line1': '',
                    'normalized_line2': '',
                    'normalized_city': '',
                    'normalized_state': '',
                    'normalized_zip': '',
                    'success': voter_address_retrieve_results['success'],
                    'status': voter_address_retrieve_results['status'],
                    'address_found': voter_address_retrieve_results['address_found'],
                    'guess_if_no_address_saved': guess_if_no_address_saved,
                }

            return HttpResponse(json.dumps(json_data), content_type='application/json')
        else:
            status += 'VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_NOT_FOUND_FROM_IP: '
            status += voter_location_results['status']

            json_data = {
                'voter_device_id': voter_device_id,
                'address_type': '',
                'text_for_map_search': '',
                'google_civic_election_id': 0,
                'latitude': '',
                'longitude': '',
                'normalized_line1': '',
                'normalized_line2': '',
                'normalized_city': '',
                'normalized_state': '',
                'normalized_zip': '',
                'success': False,
                'status': status,
                'address_found': False,
                'guess_if_no_address_saved': guess_if_no_address_saved,
            }
            return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_address_save_view(request):  # voterAddressSave
    """
    Save or update an address for this voter. Once the address is saved, update the ballot information.
    :param request:
    :return:
    """
    google_civic_election_id = 0

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    try:
        text_for_map_search = request.GET['text_for_map_search']
        text_for_map_search = text_for_map_search.strip()
        address_variable_exists = True
    except KeyError:
        text_for_map_search = ''
        address_variable_exists = False

    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
                'status': device_id_results['status'],
                'success': False,
                'voter_device_id': voter_device_id,
                'text_for_map_search': text_for_map_search,
            }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not address_variable_exists:
        json_data = {
                'status': "MISSING_GET_VARIABLE-ADDRESS",
                'success': False,
                'voter_device_id': voter_device_id,
                'text_for_map_search': text_for_map_search,
            }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # We retrieve voter_device_link
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
    if voter_device_link_results['voter_device_link_found']:
        voter_device_link = voter_device_link_results['voter_device_link']
        voter_id = voter_device_link.voter_id
    else:
        json_data = {
            'status': "VOTER_DEVICE_LINK_NOT_FOUND_FROM_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
            'text_for_map_search': text_for_map_search,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    if not positive_value_exists(voter_id):
        json_data = {
            'status': "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success': False,
            'voter_device_id': voter_device_id,
            'text_for_map_search': text_for_map_search,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    # Save the address value, and clear out ballot_saved information
    voter_address_manager = VoterAddressManager()
    voter_address_save_results = voter_address_manager.update_or_create_voter_address(
        voter_id, BALLOT_ADDRESS, text_for_map_search)

    if voter_address_save_results['success'] and voter_address_save_results['voter_address_found']:
        # # Remove the former google_civic_election_id from this voter_device_id
        # voter_device_link_manager.update_voter_device_link_with_election_id(voter_device_link, 0)
        voter_address = voter_address_save_results['voter_address']
        use_test_election = False

        # Reach out to Google and populate ballot items in the database with fresh ballot data
        google_retrieve_results = voter_ballot_items_retrieve_from_google_civic_for_api(
            voter_device_id, text_for_map_search, use_test_election)

        # Update voter_address with the google_civic_election_id retrieved from Google Civic
        # and clear out ballot_saved information IFF we got a valid google_civic_election_id back
        google_civic_election_id = convert_to_int(google_retrieve_results['google_civic_election_id'])

        # At this point proceed to update google_civic_election_id whether it is a positive integer or zero
        voter_address.google_civic_election_id = google_civic_election_id
        voter_address_update_results = voter_address_manager.update_existing_voter_address_object(voter_address)

        if voter_address_update_results['success']:
            # Replace the former google_civic_election_id from this voter_device_link
            voter_device_link_manager = VoterDeviceLinkManager()
            voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            if voter_device_link_results['voter_device_link_found']:
                voter_device_link = voter_device_link_results['voter_device_link']
                voter_device_link_manager.update_voter_device_link_with_election_id(
                    voter_device_link, google_civic_election_id)

    json_data = voter_ballot_items_retrieve_for_api(voter_device_id, google_civic_election_id)

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_ballot_items_retrieve_view(request):
    """
    (voterBallotItemsRetrieve) Request a skeleton of ballot data for this voter location,
    so that the web_app has all of the ids it needs to make more requests for data about each ballot item.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    # If passed in, we want to look at
    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))

    use_test_election = request.GET.get('use_test_election', False)
    use_test_election = False if use_test_election == 'false' else use_test_election
    use_test_election = False if use_test_election == 'False' else use_test_election

    if use_test_election:
        google_civic_election_id = 2000  # The Google Civic test election

    json_data = voter_ballot_items_retrieve_for_api(voter_device_id, google_civic_election_id)

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_ballot_items_retrieve_from_google_civic_view(request):
    voter_device_id = get_voter_device_id(request)
    text_for_map_search = request.GET.get('text_for_map_search', '')
    use_test_election = request.GET.get('use_test_election', False)
    use_test_election = False if use_test_election == 'false' else use_test_election
    use_test_election = False if use_test_election == 'False' else use_test_election

    voter_id = 0

    results = voter_ballot_items_retrieve_from_google_civic_for_api(
        voter_device_id, text_for_map_search, use_test_election)

    if results['google_civic_election_id'] and not use_test_election:
        # After the ballot is retrieved from google we want to save some info about it for the voter
        if positive_value_exists(voter_device_id):
            voter_device_link_manager = VoterDeviceLinkManager()
            voter_device_link_results = voter_device_link_manager.retrieve_voter_device_link(voter_device_id)
            if voter_device_link_results['voter_device_link_found']:
                voter_device_link = voter_device_link_results['voter_device_link']
                voter_id = voter_device_link.voter_id

        if positive_value_exists(voter_id):
            voter_ballot_saved_manager = VoterBallotSavedManager()
            is_from_substituted_address = False
            substituted_address_nearby = ''
            is_from_test_address = False

            # We don't update the voter_address because this view might be used independent of the voter_address

            # Save the meta information for this ballot data. If it fails, ignore the failure
            voter_ballot_saved_manager.create_voter_ballot_saved(
                voter_id,
                results['google_civic_election_id'],
                results['election_date_text'],
                results['election_description_text'],
                results['text_for_map_search'],
                substituted_address_nearby,
                is_from_substituted_address,
                is_from_test_address
            )

    return HttpResponse(json.dumps(results), content_type='application/json')


def voter_count_view(request):
    return voter_count()


def voter_create_view(request):  # voterCreate
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return voter_create_for_api(voter_device_id)


def voter_guide_possibility_retrieve_view(request):
    """
    Retrieve a previously saved website that may contain a voter guide (voterGuidePossibilityRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_guide_possibility_url = request.GET.get('voter_guide_possibility_url', '')
    return voter_guide_possibility_retrieve_for_api(voter_device_id=voter_device_id,
                                                    voter_guide_possibility_url=voter_guide_possibility_url)


def voter_guide_possibility_save_view(request):
    """
    Save a website that may contain a voter guide (voterGuidePossibilitySave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    voter_guide_possibility_url = request.GET.get('voter_guide_possibility_url', '')
    return voter_guide_possibility_save_for_api(voter_device_id=voter_device_id,
                                                voter_guide_possibility_url=voter_guide_possibility_url)


def voter_guides_followed_retrieve_view(request):
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)
    return voter_guides_followed_retrieve_for_api(voter_device_id=voter_device_id,
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
    use_test_election = request.GET.get('use_test_election', False)
    use_test_election = False if use_test_election == 'false' else use_test_election
    use_test_election = False if use_test_election == 'False' else use_test_election
    maximum_number_to_retrieve = get_maximum_number_to_retrieve_from_request(request)

    if positive_value_exists(ballot_item_we_vote_id):
        # We don't need both ballot_item and google_civic_election_id
        google_civic_election_id = 0
    else:
        if positive_value_exists(use_test_election):
            google_civic_election_id = 2000  # The Google Civic API Test election
        elif positive_value_exists(google_civic_election_id) or google_civic_election_id == 0:
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
                    voter_address = VoterAddress()
            else:
                voter_address = VoterAddress()
            results = choose_election_from_existing_data(voter_device_link, google_civic_election_id, voter_address)
            google_civic_election_id = results['google_civic_election_id']

        # In order to return voter_guides that are independent of an election or ballot_item, we need to pass in
        # google_civic_election_id as 0

    results = voter_guides_to_follow_retrieve_for_api(voter_device_id, kind_of_ballot_item, ballot_item_we_vote_id,
                                                      google_civic_election_id, search_string,
                                                      maximum_number_to_retrieve)
    return HttpResponse(json.dumps(results['json_data']), content_type='application/json')


def voter_location_retrieve_from_ip_view(request):  # GeoIP geo location
    """
    Take the IP address and return a location (voterLocationRetrieveFromIP)
    :param request:
    :return:
    """
    ip_address = request.GET.get('ip_address', '')
    voter_location_results = voter_location_retrieve_from_ip_for_api(request, ip_address)

    json_data = {
        'success': voter_location_results['success'],
        'status': voter_location_results['status'],
        'voter_location_found': voter_location_results['voter_location_found'],
        'voter_location': voter_location_results['voter_location'],
        'ip_address': voter_location_results['ip_address'],
        'x_forwarded_for': voter_location_results['x_forwarded_for'],
        'http_x_forwarded_for': voter_location_results['http_x_forwarded_for'],
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_photo_save_view(request):
    """
    Save or update a photo for this voter
    :param request:
    :return:
    """

    status = ''

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
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
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
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


def voter_position_visibility_save_view(request):  # voterPositionVisibilitySave
    """
    Change the visibility (between public vs. friends-only) for a single measure or candidate for one voter
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    visibility_setting = request.GET.get('visibility_setting', False)

    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)

    if kind_of_ballot_item == CANDIDATE:
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_we_vote_id = None
        office_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_we_vote_id = None
        measure_we_vote_id = ballot_item_we_vote_id
        office_we_vote_id = None
    elif kind_of_ballot_item == OFFICE:
        candidate_we_vote_id = None
        measure_we_vote_id = None
        office_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_we_vote_id = None
        measure_we_vote_id = None
        office_we_vote_id = None

    results = voter_position_visibility_save_for_api(
        voter_device_id=voter_device_id,
        office_we_vote_id=office_we_vote_id,
        candidate_we_vote_id=candidate_we_vote_id,
        measure_we_vote_id=measure_we_vote_id,
        visibility_setting=visibility_setting,
    )

    return HttpResponse(json.dumps(results), content_type='application/json')


def voter_all_positions_retrieve_view(request):  # voterAllPositionsRetrieve
    """
    Retrieve a list of all positions for one voter, including "is_support", "is_oppose" and "statement_text".
    Note that these can either be public positions or private positions.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    google_civic_election_id = request.GET.get('google_civic_election_id', 0)

    return voter_all_positions_retrieve_for_api(
        voter_device_id=voter_device_id,
        google_civic_election_id=google_civic_election_id
    )


def voter_position_like_off_save_view(request):
    """
    Un-mark the position_like for a single position for one voter (voterPositionLikeOffSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
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
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_entered_id = request.GET.get('position_entered_id', 0)
    return voter_position_like_on_save_for_api(
        voter_device_id=voter_device_id, position_entered_id=position_entered_id)


def voter_position_like_status_retrieve_view(request):
    """
    Retrieve whether or not a position_like is marked for position (voterPositionLikeStatusRetrieve)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
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
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_entered_id = request.GET.get('position_entered_id', 0)
    limit_to_voters_network = request.GET.get('limit_to_voters_network', False)
    return position_like_count_for_api(voter_device_id=voter_device_id, position_entered_id=position_entered_id,
                                       limit_to_voters_network=limit_to_voters_network)


def voter_position_comment_save_view(request):  # voterPositionCommentSave
    """
    Save comment for a single measure or candidate for one voter
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    position_we_vote_id = request.GET.get('position_we_vote_id', "")

    statement_text = request.GET.get('statement_text', False)
    statement_html = request.GET.get('statement_html', False)

    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)

    if kind_of_ballot_item == CANDIDATE:
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_we_vote_id = None
        office_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_we_vote_id = None
        measure_we_vote_id = ballot_item_we_vote_id
        office_we_vote_id = None
    elif kind_of_ballot_item == OFFICE:
        candidate_we_vote_id = None
        measure_we_vote_id = None
        office_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_we_vote_id = None
        measure_we_vote_id = None
        office_we_vote_id = None

    results = voter_position_comment_save_for_api(
        voter_device_id=voter_device_id,
        position_we_vote_id=position_we_vote_id,
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
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return voter_opposing_save(voter_device_id=voter_device_id,
                               candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
                               measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


class VoterExportView(APIView):
    """
    Export raw voter data to JSON format
    """
    def get(self, request):  # Removed: , format=None
        voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
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


def voter_retrieve_view(request):  # voterRetrieve
    """
    Retrieve a single voter based on voter_device
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    results = voter_retrieve_for_api(voter_device_id=voter_device_id)
    return HttpResponse(json.dumps(results), content_type='application/json')


def voter_sign_out_view(request):  # voterSignOut
    """
    Sign out from this device. (Delete this voter_device_id from the database, OR if sign_out_all_devices is True,
    sign out from all devices.)
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    sign_out_all_devices = request.GET.get('sign_out_all_devices', 0)

    if not positive_value_exists(voter_device_id):
        success = False
        status = "VOTER_SIGN_OUT_VOTER_DEVICE_ID_DOES_NOT_EXIST"
        json_data = {
            'voter_device_id':      voter_device_id,
            'sign_out_all_devices': sign_out_all_devices,
            'success':              success,
            'status':               status,
        }
        return HttpResponse(json.dumps(json_data), content_type='application/json')

    results = voter_sign_out_for_api(voter_device_id=voter_device_id, sign_out_all_devices=sign_out_all_devices)

    json_data = {
        'voter_device_id':      voter_device_id,
        'sign_out_all_devices': sign_out_all_devices,
        'success':              results['success'],
        'status':               results['status'],
    }
    return HttpResponse(json.dumps(json_data), content_type='application/json')


def voter_stop_opposing_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterStopOpposingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return voter_stop_opposing_save(voter_device_id=voter_device_id,
                                    candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
                                    measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_stop_supporting_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterStopSupportingSave)
    Default to set this as a position for your friends only.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return voter_stop_supporting_save(voter_device_id=voter_device_id,
                                      candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
                                      measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_supporting_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterSupportingSave)
    Default to set this as a position for your friends only.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == CANDIDATE:
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = None
    elif kind_of_ballot_item == MEASURE:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        candidate_id = 0
        candidate_we_vote_id = None
        measure_id = 0
        measure_we_vote_id = None
    return voter_supporting_save_for_api(voter_device_id=voter_device_id,
                                         candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
                                         measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_star_off_save_view(request):
    """
    Un-mark the star for a single measure, office or candidate for one voter (voterStarOffSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        office_we_vote_id = ballot_item_we_vote_id
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    return voter_star_off_save_for_api(
        voter_device_id=voter_device_id,
        office_id=office_id, office_we_vote_id=office_we_vote_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_star_on_save_view(request):
    """
    Mark the star for a single measure, office or candidate for one voter (voterStarOnSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        office_we_vote_id = ballot_item_we_vote_id
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    return voter_star_on_save_for_api(
        voter_device_id=voter_device_id,
        office_id=office_id, office_we_vote_id=office_we_vote_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_star_status_retrieve_view(request):
    """
    Retrieve whether or not a star is marked for an office, candidate or measure based on unique identifier
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    kind_of_ballot_item = request.GET.get('kind_of_ballot_item', "")
    ballot_item_id = request.GET.get('ballot_item_id', 0)
    ballot_item_we_vote_id = request.GET.get('ballot_item_we_vote_id', None)
    if kind_of_ballot_item == OFFICE:
        office_id = ballot_item_id
        office_we_vote_id = ballot_item_we_vote_id
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == CANDIDATE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = ballot_item_id
        candidate_we_vote_id = ballot_item_we_vote_id
        measure_id = 0
        measure_we_vote_id = ''
    elif kind_of_ballot_item == MEASURE:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = ballot_item_id
        measure_we_vote_id = ballot_item_we_vote_id
    else:
        office_id = 0
        office_we_vote_id = ''
        candidate_id = 0
        candidate_we_vote_id = ''
        measure_id = 0
        measure_we_vote_id = ''
    return voter_star_status_retrieve_for_api(
        voter_device_id=voter_device_id,
        office_id=office_id, office_we_vote_id=office_we_vote_id,
        candidate_id=candidate_id, candidate_we_vote_id=candidate_we_vote_id,
        measure_id=measure_id, measure_we_vote_id=measure_we_vote_id)


def voter_all_stars_status_retrieve_view(request):  # voterAllStarsStatusRetrieve
    """
    A list of all of the stars that the voter has marked.
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    return voter_all_stars_status_retrieve_for_api(
        voter_device_id=voter_device_id)


def voter_update_view(request):  # voterUpdate
    """
    Update profile-related information for this voter
    :param request:
    :return:
    """

    voter_updated = False

    voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id

    # If we have an incoming GET value for a variable, use it. If we don't pass "False" into voter_update_for_api
    # as a signal to not change the variable. (To set variables to False, pass in the string "False".)
    try:
        facebook_email = request.GET['facebook_email']
        facebook_email = facebook_email.strip()
        if facebook_email.lower() == 'false':
            facebook_email = False
    except KeyError:
        facebook_email = False

    try:
        facebook_profile_image_url_https = request.GET['facebook_profile_image_url_https']
        facebook_profile_image_url_https = facebook_profile_image_url_https.strip()
        if facebook_profile_image_url_https.lower() == 'false':
            facebook_profile_image_url_https = False
    except KeyError:
        facebook_profile_image_url_https = False

    try:
        first_name = request.GET['first_name']
        first_name = first_name.strip()
        if first_name.lower() == 'false':
            first_name = False
    except KeyError:
        first_name = False

    try:
        middle_name = request.GET['middle_name']
        middle_name = middle_name.strip()
        if middle_name.lower() == 'false':
            middle_name = False
    except KeyError:
        middle_name = False

    try:
        last_name = request.GET['last_name']
        last_name = last_name.strip()
        if last_name.lower() == 'false':
            last_name = False
    except KeyError:
        last_name = False

    try:
        twitter_profile_image_url_https = request.GET['twitter_profile_image_url_https']
        twitter_profile_image_url_https = twitter_profile_image_url_https.strip()
        if twitter_profile_image_url_https.lower() == 'false':
            twitter_profile_image_url_https = False
    except KeyError:
        twitter_profile_image_url_https = False

    device_id_results = is_voter_device_id_valid(voter_device_id)
    if not device_id_results['success']:
        json_data = {
                'status':                           device_id_results['status'],
                'success':                          False,
                'voter_device_id':                  voter_device_id,
                'facebook_email':                   facebook_email,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
                'first_name':                       first_name,
                'middle_name':                      middle_name,
                'last_name':                        last_name,
                'twitter_profile_image_url_https':  twitter_profile_image_url_https,
                'voter_updated':                    voter_updated,
            }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    at_least_one_variable_has_changed = True if \
        facebook_email or facebook_profile_image_url_https \
        or first_name or middle_name or last_name \
        else False

    if not at_least_one_variable_has_changed:
        json_data = {
                'status':                           "MISSING_VARIABLE-NO_VARIABLES_PASSED_IN_TO_CHANGE",
                'success':                          True,
                'voter_device_id':                  voter_device_id,
                'facebook_email':                   facebook_email,
                'facebook_profile_image_url_https': facebook_profile_image_url_https,
                'first_name':                       first_name,
                'middle_name':                      middle_name,
                'last_name':                        last_name,
                'twitter_profile_image_url_https':  twitter_profile_image_url_https,
                'voter_updated':                    voter_updated,
            }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    voter_id = fetch_voter_id_from_voter_device_link(voter_device_id)
    if voter_id < 0:
        json_data = {
            'status':                           "VOTER_NOT_FOUND_FROM_DEVICE_ID",
            'success':                          False,
            'voter_device_id':                  voter_device_id,
            'facebook_email':                   facebook_email,
            'facebook_profile_image_url_https': facebook_profile_image_url_https,
            'first_name':                       first_name,
            'middle_name':                      middle_name,
            'last_name':                        last_name,
            'twitter_profile_image_url_https':  twitter_profile_image_url_https,
            'voter_updated':                    voter_updated,
        }
        response = HttpResponse(json.dumps(json_data), content_type='application/json')
        return response

    # At this point, we have a valid voter
    voter_manager = VoterManager()
    results = voter_manager.update_voter(voter_id, facebook_email, facebook_profile_image_url_https,
                                         first_name, middle_name, last_name, twitter_profile_image_url_https)

    json_data = {
        'status':                           results['status'],
        'success':                          results['success'],
        'voter_device_id':                  voter_device_id,
        'facebook_email':                   facebook_email,
        'facebook_profile_image_url_https': facebook_profile_image_url_https,
        'first_name':                       first_name,
        'middle_name':                      middle_name,
        'last_name':                        last_name,
        'twitter_profile_image_url_https':  twitter_profile_image_url_https,
        'voter_updated':                    results['voter_updated'],
    }

    response = HttpResponse(json.dumps(json_data), content_type='application/json')
    return response
