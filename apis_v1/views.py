# apis_v1/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from django.http import HttpResponse
import json
from wevote_functions.models import generate_voter_device_id
import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def device_id_generate(request):
    """
    This API call is used by clients to generate a transient unique identifier (device_id - stored on client)
    which ties the device to a persistent voter_id (mapped together and stored on the server).

    :param request:
    :return: Unique device id that can be stored in a cookie
    """
    voter_device_id = generate_voter_device_id()  # Stored in cookie below
    logger.debug("apis_v1/views.py, device_id_generate-voter_device_id: {voter_device_id}".format(
        voter_device_id=voter_device_id
        ))

    data = {
        'voter_device_id': voter_device_id,
    }
    return HttpResponse(json.dumps(data), content_type='application/json')
