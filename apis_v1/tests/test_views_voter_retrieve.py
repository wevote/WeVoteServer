# apis_v1/test_views_voter_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.http import SimpleCookie
import json


class WeVoteAPIsV1TestsVoterRetrieve(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_retrieve_url = "%s?format=json" % reverse("apis_v1:voterRetrieveView")

    def test_retrieve_with_no_cookie(self):
        response = self.client.get(self.voter_retrieve_url)
        json_data = json.loads(response.content)

        #######################################
        # Without a cookie, we don't expect valid response
        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the voterRetrieveView json response, and not found")

        self.assertEqual(
            json_data['status'], 'VALID_VOTER_DEVICE_ID_MISSING',
            "status:  {status} (VALID_VOTER_DEVICE_ID_MISSING expected), voter_device_id: {voter_device_id}".format(
                status=json_data['status'], voter_device_id=json_data['voter_device_id']))

    def test_retrieve_with_cookie(self):
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
        # Create a voter so we can test retrieve
        response2 = self.client.get(self.voter_create_url)
        json_data2 = json.loads(response2.content)

        self.assertEqual('status' in json_data2, True,
                         "status expected in the voterCreateView json response but not found")
        self.assertEqual('voter_device_id' in json_data2, True,
                         "voter_device_id expected in the voterCreateView json response but not found")

        # With a brand new voter_device_id, a new voter record should be created
        self.assertEqual(
            json_data2['status'], 'VOTER_CREATED',
            "status:  {status} (VOTER_CREATED expected), voter_device_id: {voter_device_id}".format(
                status=json_data2['status'], voter_device_id=json_data2['voter_device_id']))

        #######################################
        # Test for id, first_name, last_name, email
        response3 = self.client.get(self.voter_retrieve_url)
        json_data3 = json.loads(response3.content)

        for one_voter in json_data3:
            self.assertEqual('id' in one_voter, True, "id expected in the voterRetrieveView json response but not found")
            self.assertEqual('first_name' in one_voter, True,
                             "first_name expected in the voterRetrieveView json response but not found")
            self.assertEqual('last_name' in one_voter, True,
                             "last_name expected in the voterRetrieveView json response but not found")
            self.assertEqual('email' in one_voter, True,
                             "email expected in the voterRetrieveView json response but not found")


