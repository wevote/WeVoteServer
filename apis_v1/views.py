# apis_v1/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .controllers import organization_count, organization_follow, organization_follow_ignore, organization_retrieve, \
    organization_save_for_api, \
    organization_stop_following, voter_address_save, voter_address_retrieve, voter_count, voter_create, \
    voter_guides_to_follow_retrieve, voter_retrieve_list
from ballot.controllers import voter_ballot_items_retrieve
from candidate.controllers import candidates_retrieve
from django.http import HttpResponse
import json
from organization.controllers import organization_search_controller
from rest_framework.response import Response
from rest_framework.views import APIView
from support_oppose_deciding.controllers import oppose_count_for_api, support_count_for_api, \
    voter_opposing_save, voter_stop_opposing_save, voter_stop_supporting_save, voter_supporting_save
from voter.serializers import VoterSerializer
from wevote_functions.models import generate_voter_device_id, get_voter_device_id, \
    get_google_civic_election_id_from_cookie, set_google_civic_election_id_cookie
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def candidates_retrieve_view(request):
    office_id = request.GET.get('office_id', 0)
    office_we_vote_id = request.GET.get('office_we_vote_id', '')
    return candidates_retrieve(office_id, office_we_vote_id)


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
    return organization_retrieve(organization_id=organization_id, organization_we_vote_id=organization_we_vote_id)


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
    return organization_search_controller(organization_name=organization_name,
                                          organization_twitter_handle=organization_twitter_handle,
                                          organization_website=organization_website,
                                          organization_email=organization_email)


def oppose_count_view(request):
    """
    Retrieve the number of orgs and friends that oppose this (opposeCount)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    candidate_id = request.GET.get('candidate_id', 0)
    measure_id = request.GET.get('measure_id', 0)
    return oppose_count_for_api(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


def support_count_view(request):
    """
    Retrieve the number of orgs and friends that support this (supportCount)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    candidate_id = request.GET.get('candidate_id', 0)
    measure_id = request.GET.get('measure_id', 0)
    return support_count_for_api(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


def voter_address_retrieve_view(request):
    """
    Retrieve an address for this voter so we can figure out which ballot to display
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    return voter_address_retrieve(voter_device_id)


def voter_address_save_view(request):
    """
    Save or update an address for this voter
    :param request:
    :return:
    """

    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    try:
        address = request.POST['address']
        address_variable_exists = True
    except KeyError:
        address = ''
        address_variable_exists = False

    response = voter_address_save(voter_device_id, address, address_variable_exists)

    # Reset google_civic_election_id whenever we save a new address
    google_civic_election_id = 0
    set_google_civic_election_id_cookie(request, response, google_civic_election_id)

    return response


def voter_ballot_items_retrieve_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    # We look in the cookies for google_civic_election_id
    google_civic_election_id = get_google_civic_election_id_from_cookie(request)
    # This 'voter_ballot_items_retrieve' lives in ballot/controllers.py
    results = voter_ballot_items_retrieve(voter_device_id, google_civic_election_id)
    response = HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    # Save google_civic_election_id whenever we retrieve a new ballot
    set_google_civic_election_id_cookie(request, response, results['google_civic_election_id'])

    return response


def voter_count_view(request):
    return voter_count()


def voter_create_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    return voter_create(voter_device_id)


def voter_guides_to_follow_retrieve_view(request):
    """
    Retrieve a list of voter_guides that a voter might want to follow
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    # We look in the cookies for google_civic_election_id
    google_civic_election_id = get_google_civic_election_id_from_cookie(request)
    results = voter_guides_to_follow_retrieve(voter_device_id, google_civic_election_id)
    response = HttpResponse(json.dumps(results['json_data']), content_type='application/json')

    # Save google_civic_election_id with fresh version that we retrieved from BallotItem table (if not passed in)
    set_google_civic_election_id_cookie(request, response, results['google_civic_election_id'])

    return response


def voter_opposing_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterOpposingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    candidate_id = request.GET.get('candidate_id', 0)
    measure_id = request.GET.get('measure_id', 0)
    return voter_opposing_save(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


class VoterRetrieveView(APIView):
    """
    Export raw voter data to JSON format
    """
    def get(self, request):  # Removed: , format=None
        voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
        results = voter_retrieve_list(voter_device_id)

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


def voter_stop_opposing_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterStopOpposingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    candidate_id = request.GET.get('candidate_id', 0)
    measure_id = request.GET.get('measure_id', 0)
    return voter_stop_opposing_save(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


def voter_stop_supporting_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterStopSupportingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    candidate_id = request.GET.get('candidate_id', 0)
    measure_id = request.GET.get('measure_id', 0)
    return voter_stop_supporting_save(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)


def voter_supporting_save_view(request):
    """
    Save support for a single measure or candidate for one voter (voterSupportingSave)
    :param request:
    :return:
    """
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    candidate_id = request.GET.get('candidate_id', 0)
    measure_id = request.GET.get('measure_id', 0)
    return voter_supporting_save(voter_device_id=voter_device_id, candidate_id=candidate_id, measure_id=measure_id)
