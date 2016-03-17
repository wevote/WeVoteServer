# geoip/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# requires an installation of the C library at https://github.com/maxmind/geoip-api-c
from django.contrib.gis.geoip import GeoIP
import wevote_functions.admin
from wevote_functions.functions import get_ip_from_headers, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def voter_location_retrieve_from_ip_for_api(request, ip_address=''):
    """
    Used by the api
    :param ip_address:
    :return:
    """
    x_forwarded_for = request.META.get('X-Forwarded-For')
    http_x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if not positive_value_exists(ip_address):
        ip_address = get_ip_from_headers(request)

    if not positive_value_exists(ip_address):
        # return HttpResponse('missing ip_address request parameter', status=400)
        response_content = {
            'success': False,
            'status': 'LOCATION_RETRIEVE_IP_ADDRESS_REQUEST_PARAMETER_MISSING',
            'voter_location_found': False,
            'voter_location': '',
            'ip_address': ip_address,
            'x_forwarded_for': x_forwarded_for,
            'http_x_forwarded_for': http_x_forwarded_for,
        }

        return response_content

    g = GeoIP()
    location = g.city(ip_address)
    if location is None:
        # Consider this alternate way of responding to front end:
        # return HttpResponse('no matching location for IP address {}'.format(ip_address), status=400)
        response_content = {
            'success': True,
            'status': 'LOCATION_NOT_FOUND',
            'voter_location_found': False,
            'voter_location': '',
            'ip_address': ip_address,
            'x_forwarded_for': x_forwarded_for,
            'http_x_forwarded_for': http_x_forwarded_for,
        }
    else:
        response_content = {
            'success': True,
            'status': 'LOCATION_FOUND',
            'voter_location_found': True,
            'voter_location': '{0[city]}, {0[region]} {0[postal_code]}'.format(location),
            'ip_address': ip_address,
            'x_forwarded_for': x_forwarded_for,
            'http_x_forwarded_for': http_x_forwarded_for,
        }

    return response_content
