# apis_v1/test_views_voter_address_save.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import json

from django.urls import reverse
from django.test import TestCase


class WeVoteAPIsV1TestsVoterAddressSave(TestCase):
    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_address_save_url = reverse("apis_v1:voterAddressSaveView")
        self.voter_address_retrieve_url = reverse("apis_v1:voterAddressRetrieveView")

    def test_save_with_no_voter_device_id(self):
        response = self.client.post(self.voter_address_retrieve_url, {'text_for_map_search':
                                                                      '321 Main Street, Oakland CA 94602'})
        json_data = json.loads(response.content.decode())

        #######################################
        # Without a cookie, we don't expect valid response
        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the voterAddressSaveView json response, and not found")

        self.assertEqual(
            json_data['status'], 'VALID_VOTER_DEVICE_ID_MISSING, GUESS_IF_NO_ADDRESS_SAVED, '
                                 'VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_NOT_FOUND_FROM_IP: LOCATION_NOT_FOUND',
            "status: {status} ('VALID_VOTER_DEVICE_ID_MISSING, GUESS_IF_NO_ADDRESS_SAVED, "
            "VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_NOT_FOUND_FROM_IP: LOCATION_NOT_FOUND' expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data['status'], voter_device_id=json_data['voter_device_id']))

    def test_saves_with_voter_device_id(self):
        """
        Test the various cookie states
        :return:
        """

        #######################################
        # Generate the voter_device_id cookie
        response = self.client.get(self.generate_voter_device_id_url)
        json_data = json.loads(response.content.decode())

        # Make sure we got back a voter_device_id we can use
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Now put the voter_device_id in a variable we can use below
        voter_device_id = json_data['voter_device_id'] if 'voter_device_id' in json_data else ''

        #######################################
        # Create a voter so we can test retrieve
        response2 = self.client.get(self.voter_create_url, {'voter_device_id': voter_device_id})
        json_data2 = json.loads(response2.content.decode())

        self.assertEqual('status' in json_data2, True,
                         "status expected in the voterAddressSaveView json response but not found")
        self.assertEqual('voter_device_id' in json_data2, True,
                         "voter_device_id expected in the voterAddressSaveView json response but not found")

        # With a brand new voter_device_id, a new voter record should be created
        self.assertEqual(
            json_data2['status'], 'VOTER_CREATED',
            "status: {status} (VOTER_CREATED expected in voterAddressSaveView), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data2['status'], voter_device_id=json_data2['voter_device_id']))

        #######################################
        # Create a voter address so we can test retrieve
        response2 = self.client.get(self.voter_address_save_url, {'text_for_map_search':
                                                                  '123 Main Street, Oakland CA 94602',
                                                                  'voter_device_id': voter_device_id})
        json_data2 = json.loads(response2.content.decode())

        self.assertEqual('status' in json_data2, True,
                         "status expected in the voterAddressSaveView json response but not found")
        self.assertEqual('voter_device_id' in json_data2, True,
                         "voter_device_id expected in the voterAddressSaveView json response but not found")
        self.assertEqual('success' in json_data2, True,
                         "success expected in the voterAddressSaveView json response but not found")
        self.assertEqual('text_for_map_search' in json_data2, True,
                         "address expected in the voterAddressSaveView json response but not found")

        # First address save
        self.assertEqual('VOTER_BALLOT_SAVED_NOT_FOUND_FROM_EXISTING_DATA' in json_data2['status'], True,
            "status: {status} "
            "(VOTER_BALLOT_SAVED_NOT_FOUND_FROM_EXISTING_DATA expected in voterAddressSaveView), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data2['status'], voter_device_id=json_data2['voter_device_id']))

        #######################################
        # Try and save the voter address again
        response3 = self.client.get(self.voter_address_save_url, {'text_for_map_search':
                                                                  '321 Main Street, Oakland CA 94602',
                                                                  'voter_device_id': voter_device_id})
        json_data3 = json.loads(response3.content.decode())

        # First address update
        self.assertEqual('VOTER_BALLOT_SAVED_NOT_FOUND_FROM_EXISTING_DATA' in json_data3['status'], True,
            "status: {status} ('VOTER_BALLOT_SAVED_NOT_FOUND_FROM_EXISTING_DATA expected in voterAddressSaveView), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data3['status'], voter_device_id=json_data3['voter_device_id']))

        #######################################
        # Test to make sure the address has been saved in the database
        response4 = self.client.get(self.voter_address_retrieve_url, {'voter_device_id': voter_device_id})
        json_data4 = json.loads(response4.content.decode())

        # Are any expected fields missing?
        self.assertEqual('success' in json_data4, True,
                         "success expected in the voterAddressSaveView json response but not found")
        self.assertEqual('text_for_map_search' in json_data4, True,
                         "text_for_map_search expected in the voterAddressSaveView json response but not found")
        # A more thorough testing of expected variables is done in test_views_voter_address_retrieve.py

        # Does address match the value inserted last?
        self.assertEqual(
            json_data4['text_for_map_search'], '321 Main Street, Oakland CA 94602',
            "text_for_map_search:  {text_for_map_search} ('321 Main Street, Oakland CA 94602' expected "
            "in voterAddressSaveView), "
            "voter_device_id: {voter_device_id}".format(
                text_for_map_search=json_data4['text_for_map_search'], voter_device_id=json_data4['voter_device_id']))
