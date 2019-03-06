# apis_v1/test_views_voter_address_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
import json


class WeVoteAPIsV1TestsVoterAddressRetrieve(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_address_save_url = reverse("apis_v1:voterAddressSaveView")
        self.voter_address_retrieve_url = reverse("apis_v1:voterAddressRetrieveView")

    def test_retrieve_with_no_voter_device_id(self):
        response = self.client.get(self.voter_address_retrieve_url)
        json_data = json.loads(response.content.decode())

        #######################################
        # Without a cookie, we don't expect valid response
        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the voterAddressRetrieveView json response, and not found")

        self.assertEqual(
            json_data['status'], 'VALID_VOTER_DEVICE_ID_MISSING, GUESS_IF_NO_ADDRESS_SAVED, '
                                 'VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_NOT_FOUND_FROM_IP: LOCATION_NOT_FOUND',
            "status: {status} "
            "('VALID_VOTER_DEVICE_ID_MISSING, GUESS_IF_NO_ADDRESS_SAVED, "
            "VOTER_ADDRESS_RETRIEVE-VOTER_LOCATION_NOT_FOUND_FROM_IP: LOCATION_NOT_FOUND' expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data['status'], voter_device_id=json_data['voter_device_id']))

    def test_retrieve_with_voter_device_id(self):
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
                         "status expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('voter_device_id' in json_data2, True,
                         "voter_device_id expected in the voterAddressRetrieveView json response but not found")

        # With a brand new voter_device_id, a new voter record should be created
        self.assertEqual(
            json_data2['status'], 'VOTER_CREATED',
            "status: {status} (VOTER_CREATED expected in voterAddressRetrieveView), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data2['status'], voter_device_id=json_data2['voter_device_id']))

        #######################################
        # Create a voter address so we can test retrieve
        response3 = self.client.get(self.voter_address_save_url, {'text_for_map_search':
                                                                  '123 Main Street, Oakland CA 94602',
                                                                  'voter_device_id': voter_device_id})
        json_data3 = json.loads(response3.content.decode())

        self.assertEqual('status' in json_data3, True,
                         "status expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('voter_device_id' in json_data3, True,
                         "voter_device_id expected in the voterAddressRetrieveView json response but not found")

        # First address save
        self.assertEqual(
            json_data3['text_for_map_search'], '123 Main Street, Oakland CA 94602',
            "status: {status} ('123 Main Street, Oakland CA 94602'"
            " expected in voterAddressRetrieveView), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data3['status'], voter_device_id=json_data3['voter_device_id']))

        #######################################
        # Test for expected response variables
        response4 = self.client.get(self.voter_address_retrieve_url, {'voter_device_id': voter_device_id})
        json_data4 = json.loads(response4.content.decode())

        # Are any expected fields missing?
        self.assertEqual('success' in json_data4, True,
                         "success expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('text_for_map_search' in json_data4, True,
                         "text_for_map_search expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('address_type' in json_data4, True,
                         "address_type expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('latitude' in json_data4, True,
                         "latitude expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('longitude' in json_data4, True,
                         "longitude expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('normalized_line1' in json_data4, True,
                         "normalized_line1 expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('normalized_line2' in json_data4, True,
                         "normalized_line2 expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('normalized_city' in json_data4, True,
                         "normalized_city expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('normalized_state' in json_data4, True,
                         "normalized_state expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('normalized_zip' in json_data4, True,
                         "normalized_zip expected in the voterAddressRetrieveView json response but not found")

        # Does address match the value inserted last?
        self.assertEqual(
            json_data4['text_for_map_search'], '123 Main Street, Oakland CA 94602',
            "text_for_map_search:  {text_for_map_search} "
            "('123 Main Street, Oakland CA 94602' expected in voterAddressRetrieveView), "
            "voter_device_id: {voter_device_id}".format(
                text_for_map_search=json_data4['text_for_map_search'], voter_device_id=json_data4['voter_device_id']))
