# apis_v1/test_views_voter_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from future.standard_library import install_aliases
from django.urls import reverse
from django.test import TestCase
from django.test import Client
import json
install_aliases()


class WeVoteAPIsV1TestsVoterRetrieve(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_retrieve_url = reverse("apis_v1:voterRetrieveView")
        self.client2 = Client(HTTP_USER_AGENT='Mozilla/5.0')

    def test_retrieve_with_no_voter_device_id(self):
        response = self.client2.get(self.voter_retrieve_url)
        json_data = json.loads(response.content.decode())

        # Without a cookie, we don't expect valid response
        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the voterRetrieveView json response, and not found")

        self.assertEqual(
            'VOTER_CREATED' in json_data['status'], True,
            "status: {status} (VOTER_CREATED expected), voter_device_id: {voter_device_id}".format(
                status=json_data['status'], voter_device_id=json_data['voter_device_id']))

    def test_retrieve_with_voter_device_id(self):
        """
        Test the various cookie states
        :return:
        """

        #######################################
        # Generate the voter_device_id cookie
        response = self.client2.get(self.generate_voter_device_id_url)
        json_data = json.loads(response.content.decode())

        # Make sure we got back a voter_device_id we can use
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Now put the voter_device_id in a variable we can use below
        voter_device_id = json_data['voter_device_id'] if 'voter_device_id' in json_data else ''

        #######################################
        # Create a voter so we can test retrieve
        response2 = self.client2.get(self.voter_create_url, {'voter_device_id': voter_device_id})
        json_data2 = json.loads(response2.content.decode())

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
        # Test for we_vote_id, first_name, last_name, email
        response3 = self.client2.get(self.voter_retrieve_url, {'voter_device_id': voter_device_id})
        json_data3 = json.loads(response3.content.decode())

        self.assertEqual('we_vote_id' in json_data3, True, "we_vote_id expected in the voterRetrieveView"
                                                           " response but not found")
        self.assertEqual('first_name' in json_data3, True,
                         "first_name expected in the voterRetrieveView json response but not found")
        self.assertEqual('last_name' in json_data3, True,
                         "last_name expected in the voterRetrieveView json response but not found")
        self.assertEqual('email' in json_data3, True,
                         "email expected in the voterRetrieveView json response but not found")
