# apis_v1/test_views_device_id_generate.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
import json


class WeVoteAPIsV1TestsDeviceIdGenerate(TestCase):

    def setUp(self):
        self.read_url = reverse("apis_v1:deviceIdGenerateView")

    def test_key(self):
        response = self.client.get(self.read_url)
        json_data = json.loads(response.content.decode())

        # With this json, is one of the keys 'voter_device_id'?
        # {"voter_device_id": "WAijDN5AbGovLCCKXaIJTfTRBT745Wgk4tkNnoKXJvSDOiAPGHCesT6xcLvsRoWBZVUHGGnTLhRWtEoHEnOrzyj"}
        self.assertEqual('voter_device_id' in json_data, True, "voter_device_id expected as key in json")

    def test_value_length(self):
        response = self.client.get(self.read_url)
        json_data = json.loads(response.content.decode())

        # Is the value at least 88 characters long?
        self.assertGreaterEqual(
            len(json_data['voter_device_id']), 88,
            "The length of the voter_device_id value should be at least 88 and is {the_length}".format(
                the_length=len(json_data['voter_device_id'])))
