# apis_v1/test_views_voter_create.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.http import SimpleCookie
import json


class WeVoteAPIsV1TestsVoterCreate(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")

    def test_create_with_no_cookie(self):
        """
        If there isn't a voter_device_id cookie, do we get the expected error?
        :return:
        """
        response = self.client.get(self.voter_create_url)
        json_data = json.loads(response.content)

        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Since we didn't pass the voter_device_id in,
        self.assertEqual(
            json_data['status'], 'VALID_VOTER_DEVICE_ID_MISSING',
            "A valid voter_device_id was not found ({voter_device_id}). "
            "Instead, this status was returned: {status}".format(
                status=json_data['status'], voter_device_id=json_data['voter_device_id']))

    def test_create_with_cookie(self):
        """
        Test the various cookie states
        :return:
        """

        #######################################
        # Generate the voter_device_id cookie
        response = self.client.get(self.generate_voter_device_id_url)
        json_data = json.loads(response.content)

        # Make sure we got back a voter_device_id we can use
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Now save the retrieved voter_device_id in a mock cookie
        cookies = SimpleCookie()
        cookies["voter_device_id"] = json_data['voter_device_id']
        self.client = Client(HTTP_COOKIE=cookies.output(header='', sep='; '))

        #######################################
        # Test for status: VOTER_CREATED
        response2 = self.client.get(self.voter_create_url)
        json_data2 = json.loads(response2.content)

        self.assertEqual('status' in json_data2, True,
                         "status expected in the voterCreateView json response but not found")
        self.assertEqual('voter_device_id' in json_data2, True,
                         "voter_device_id expected in the voterCreateView json response but not found")

        # With a brand new voter_device_id, a new voter record should be created
        self.assertEqual(
            json_data2['status'], 'VOTER_CREATED',
            "status: {status} (VOTER_CREATED expected), voter_device_id: {voter_device_id}".format(
                status=json_data2['status'], voter_device_id=json_data2['voter_device_id']))

        #######################################
        # Test for status: VOTER_ALREADY_EXISTS
        response3 = self.client.get(self.voter_create_url)
        json_data3 = json.loads(response3.content)

        self.assertEqual('status' in json_data3, True,
                         "status expected in the voterCreateView json response but not found")
        self.assertEqual('voter_device_id' in json_data3, True,
                         "voter_device_id expected in the voterCreateView json response but not found")

        # Try reusing the same voter_device_id
        self.assertEqual(
            json_data3['status'], 'VOTER_ALREADY_EXISTS',
            "status: {status} (VOTER_ALREADY_EXISTS expected), voter_device_id: {voter_device_id}".format(
                status=json_data3['status'], voter_device_id=json_data3['voter_device_id']))
