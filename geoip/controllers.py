# geoip/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import sys
from ipaddress import IPv4Address
import geoip2.database
import wevote_functions.admin
from config.base import get_environment_variable_default
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

    valid_ip_address = None
    value = ip_address

    try:
        valid_ip_address = IPv4Address(value)
    except:
        value = get_ip_from_headers(request)
        try:
            valid_ip_address = IPv4Address(value)
        except:
            # None of the IP addresses are valid
            response_content = {
                'success':              False,
                'status':               'LOCATION_RETRIEVE_IP_ADDRESS_REQUEST_PARAMETER_MISSING',
                'voter_location_found': False,
                'voter_location':       '',
                'city':                 '',
                'region':               '',
                'postal_code':          '',
                'country_code':         '',
                'ip_address':           value,
                'x_forwarded_for':      x_forwarded_for,
                'http_x_forwarded_for': http_x_forwarded_for,
            }
            return response_content


    if valid_ip_address.is_private and 'test' not in sys.argv:
        value = '73.158.32.221'
        try:
            if 'only_log_ip_substitution_once' not in sys.argv:
                sys.argv.append('only_log_ip_substitution_once')
                print("Detected a private IP address, so we are providing a valid Oakland IP address 73.158.32.221 for geolocation purposes...")
        except Exception as e:
            pass

    try:
        database_location = get_environment_variable_default('GEOLITE2_DATABASE_LOCATION', 'geoip2/city-db/GeoLite2-City.mmdb')
        reader = geoip2.database.Reader(database_location)
        response = reader.city(value)

    except geoip2.errors.AddressNotFoundError as e:
        if 'test' not in sys.argv:
            logger.error("voter_location_retrieve_from_ip_for_api ip " + value + " not found: " + str(e))

        response_content = {
            'success':              True,
            'status':               'LOCATION_NOT_FOUND',
            'voter_location_found': False,
            'voter_location':       '',
            'city':                 '',
            'region':               '',
            'postal_code':          '',
            'country_code':         '',
            'ip_address':           value,
            'x_forwarded_for':      x_forwarded_for,
            'http_x_forwarded_for': http_x_forwarded_for,
        }

        return response_content

    voter_location = ''
    city = ''
    region = ''  # could be state_code
    postal_code = ''
    country_code = ''
    success = True
    voter_location_found = False
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
        if response.country.iso_code:
            country_code = response.country.iso_code
        if positive_value_exists(voter_location):
            status = 'LOCATION_FOUND'
            voter_location_found = True
        else:
            status = 'IP_FOUND_BUT_LOCATION_NOT_RETURNED'
            voter_location_found = False

    except Exception as e:
        logger.error("voter_location_retrieve_from_ip_for_api ip " + value + " parse error: " + str(e))
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
        'country_code':         country_code,
        'ip_address':           value,
        'x_forwarded_for':      x_forwarded_for,
        'http_x_forwarded_for': http_x_forwarded_for,
    }

    return response_content
