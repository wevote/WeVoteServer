
# -*- coding: UTF-8 -*-
import json

from django.core.urlresolvers import reverse
from django.test import Client, TestCase


class WeVoteAPIsV1TestsVoterAddressSave(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.voter_location_url = reverse('apis_v1:voterLocationRetrieveFromIPView')
        cls.client = Client()

    def test_location_from_ip_success(self):
        response = self.client.get(self.voter_location_url, {'ip_address': '69.181.21.132'})
        json_data = json.loads(response.content.decode())
        self.assertEqual(json_data['success'], True)
        self.assertEqual(json_data['voter_location'], 'San Francisco, CA 94108')

    def test_failure_no_ip_supplied(self):
        response = self.client.get(self.voter_location_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), 'missing ip_address request parameter')

    def test_failure_invalid_ip(self):
        response = self.client.get(self.voter_location_url, {'ip_address': '0.2.1.1'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), 'no matching location for this IP address')
