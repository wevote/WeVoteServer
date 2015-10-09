# apis_v1/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from django.http import HttpResponse
import json
from rest_framework.response import Response
from rest_framework.views import APIView

from .controllers import voter_address_save, voter_address_retrieve, voter_count, voter_create, voter_retrieve_list
from .serializers import VoterSerializer
from wevote_functions.models import generate_voter_device_id, get_voter_device_id
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


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
    return voter_address_save(voter_device_id, address, address_variable_exists)


def voter_count_view(request):
    return voter_count()


def voter_create_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    return voter_create(voter_device_id)


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
