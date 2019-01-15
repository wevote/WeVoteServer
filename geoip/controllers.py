# geoip/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import geoip2.database
import wevote_functions.admin
from config.base import get_environment_variable
from wevote_functions.functions import get_ip_from_headers, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


def voter_location_retrieve_from_ip_for_api(request, ip_address=''):
    """
    Used by the api voterLocationRetrieveFromIP
    https://www.maxmind.com/en/geoip2-databases
    https://geoip2.readthedocs.io/en/latest/#city-database
    https://www.maxmind.com/en/geoip-demo
    :param request:
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

    if ip_address == '127.0.0.1':
        print("Running on a local dev server, so substituting an Oakland IP address 73.158.32.221 for 127.0.0.1")
        ip_address = '73.158.32.221'

    if not positive_value_exists(ip_address):
        # return HttpResponse('missing ip_address request parameter', status=400)
        response_content = {
            'success':              False,
            'status':               'LOCATION_RETRIEVE_IP_ADDRESS_REQUEST_PARAMETER_MISSING',
            'voter_location_found': False,
            'voter_location':       '',
            'city':                 '',
            'region':               '',
            'postal_code':          '',
            'ip_address':           ip_address,
            'x_forwarded_for':      x_forwarded_for,
            'http_x_forwarded_for': http_x_forwarded_for,
        }

        return response_content

    try:
        reader = geoip2.database.Reader(get_environment_variable('GEOLITE2_DATABASE_LOCATION'))
        response = reader.city(ip_address)

    except geoip2.errors.AddressNotFoundError as e:
        logger.error("voter_location_retrieve_from_ip_for_api ip " + ip_address + " not found: " + str(e))

        response_content = {
            'success':              True,
            'status':               'LOCATION_NOT_FOUND',
            'voter_location_found': False,
            'voter_location':       '',
            'city':                 '',
            'region':               '',
            'postal_code':          '',
            'ip_address':           ip_address,
            'x_forwarded_for':      x_forwarded_for,
            'http_x_forwarded_for': http_x_forwarded_for,
        }

        return response_content

    voter_location = ''
    city = ''
    region = ''  # could be state_code
    postal_code = ''
    success = True
    try:
        if response.city.name:
            city = response.city.name
            voter_location += city
            if response.subdivisions.most_specific.iso_code or response.postal.code:
                voter_location += ', '
        if response.subdivisions.most_specific.iso_code:
            region = response.subdivisions.most_specific.iso_code
            voter_location += region
            if response.postal.code:
                voter_location += ' '
        if response.postal.code:
            postal_code = response.postal.code
            voter_location += postal_code
        if positive_value_exists(voter_location):
            status = 'LOCATION_FOUND'
            voter_location_found = True
        else:
            status = 'IP_FOUND_BUT_LOCATION_NOT_RETURNED'
            voter_location_found = False

    except Exception as e:
        logger.error("voter_location_retrieve_from_ip_for_api ip " + ip_address + " parse error: " + str(e))
        status = str(e)
        success = False

    response_content = {
        'success':              success,
        'status':               status,
        'voter_location_found': voter_location_found,
        'voter_location':       voter_location,
        'city':                 city,
        'region':               region,
        'postal_code':          postal_code,
        'ip_address':           ip_address,
        'x_forwarded_for':      x_forwarded_for,
        'http_x_forwarded_for': http_x_forwarded_for,
    }

    return response_content
