# apis_v1/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from django.http import HttpResponse
import json
from rest_framework.response import Response
from rest_framework.views import APIView

from .controllers import voter_count, voter_create, voter_retrieve_list
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

    data = {
        'voter_device_id': voter_device_id,
    }
    return HttpResponse(json.dumps(data), content_type='application/json')


class VoterRetrieveView(APIView):
    """
    Export raw voter data to JSON format
    """
    def get(self, request):  # Removed: , format=None
        voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
        results = voter_retrieve_list(voter_device_id)

        if results['success']:
            voter_list = results['voter_list']
            serializer = VoterSerializer(voter_list, many=True)
            return Response(serializer.data)
        else:
            data = results['json_data']
            return HttpResponse(json.dumps(data), content_type='application/json')


def voter_count_view(request):
    return voter_count()


def voter_create_view(request):
    voter_device_id = get_voter_device_id(request)  # We look in the cookies for voter_device_id
    return voter_create(voter_device_id)
