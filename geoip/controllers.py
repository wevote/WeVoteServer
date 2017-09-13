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
    Used by the api voterLocationRetrieveFromIP
    :param ip_address:
    :return:
    """
    x_forwarded_for = request.META.get('X-Forwarded-For')
    http_x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')

    if not positive_value_exists(ip_address):
        ip_address = get_ip_from_headers(request)

    # For testing - NY IP Address
    # if not positive_value_exists(ip_address):
    #     ip_address = '108.46.177.24'

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
        voter_location = ''
        if 'city' in location and location['city']:
            voter_location += location['city']
            if ('region' in location and location['region']) or \
                    ('postal_code' in location and location['postal_code']):
                voter_location += ', '
        if 'region' in location and location['region']:
            voter_location += location['region']
            if 'postal_code' in location and location['postal_code']:
                voter_location += ' '
        if 'postal_code' in location and location['postal_code']:
            voter_location += location['postal_code']
        if positive_value_exists(voter_location):
            status = 'LOCATION_FOUND'
            voter_location_found = True
        else:
            status = 'IP_FOUND_BUT_LOCATION_NOT_RETURNED'
            voter_location_found = False
        response_content = {
            'success': True,
            'status': status,
            'voter_location_found': voter_location_found,
            'voter_location': voter_location,
            'ip_address': ip_address,
            'x_forwarded_for': x_forwarded_for,
            'http_x_forwarded_for': http_x_forwarded_for,
        }

    return response_content
