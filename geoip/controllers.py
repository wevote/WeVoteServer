# geoip/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json

from django.http import HttpResponse
# requires an installation of the C library at https://github.com/maxmind/geoip-api-c
from django.contrib.gis.geoip import GeoIP

import wevote_functions.admin

logger = wevote_functions.admin.get_logger(__name__)


def voter_location_retrieve_from_ip_for_api(ip_address):
    """
    Used by the api
    :param ip_address:
    :return:
    """
    g = GeoIP()
    json_data = g.city(ip_address)

    return HttpResponse(json.dumps(json_data), content_type='application/json')
