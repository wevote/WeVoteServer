# -*- coding: UTF-8 -*-
import json
from functools import wraps

from django.contrib.gis import geoip
from django.core.urlresolvers import reverse
from django.test import Client, TestCase


def print_geoip_instructions_on_exc(unittest):
    @wraps(unittest)
    def wrapper(*args, **kwargs):
        try:
            unittest(*args, **kwargs)
        except geoip.base.GeoIPException:
            print('\nDid you setup GeoIP on your local machine? See '
                  'https://github.com/wevote/WeVoteServer/blob/master/README_API_INSTALL.md#set-up-geoip\n')
            raise
    return wrapper


class WeVoteAPIsV1TestsVoterAddressSave(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.voter_location_url = reverse('apis_v1:voterLocationRetrieveFromIPView')
        cls.client = Client()

    @print_geoip_instructions_on_exc
    def test_location_from_ip_success(self):
        response = self.client.get(self.voter_location_url, {'ip_address': '69.181.21.132'})

        json_data = json.loads(response.content.decode())
        self.assertEqual(json_data['success'], True)
        self.assertEqual(json_data['voter_location'], 'San Francisco, CA 94108')

    @print_geoip_instructions_on_exc
    def test_failure_no_ip_supplied(self):
        response = self.client.get(self.voter_location_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), 'missing ip_address request parameter')

    @print_geoip_instructions_on_exc
    def test_failure_invalid_ip(self):
        response = self.client.get(self.voter_location_url, {'ip_address': '0.2.1.1'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), 'no matching location for this IP address')
