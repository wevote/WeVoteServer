# apis_v1/test_views_voter_address_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.http import SimpleCookie
import json


class WeVoteAPIsV1TestsVoterAddressRetrieve(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_address_save_url = reverse("apis_v1:voterAddressSaveView")
        self.voter_address_retrieve_url = reverse("apis_v1:voterAddressRetrieveView")

    def test_retrieve_with_no_cookie(self):
        response = self.client.get(self.voter_address_retrieve_url)
        json_data = json.loads(response.content)

        #######################################
        # Without a cookie, we don't expect valid response
        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the voterAddressRetrieveView json response, and not found")

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
                         "status expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('voter_device_id' in json_data2, True,
                         "voter_device_id expected in the voterAddressRetrieveView json response but not found")

        # With a brand new voter_device_id, a new voter record should be created
        self.assertEqual(
            json_data2['status'], 'VOTER_CREATED',
            "status:  {status} (VOTER_CREATED expected in voterAddressRetrieveView), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data2['status'], voter_device_id=json_data2['voter_device_id']))

        #######################################
        # Create a voter address so we can test retrieve
        response3 = self.client.post(self.voter_address_save_url, {'address': '123 Main Street, Oakland CA 94602'})
        json_data3 = json.loads(response3.content)

        self.assertEqual('status' in json_data3, True,
                         "status expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('voter_device_id' in json_data3, True,
                         "voter_device_id expected in the voterAddressRetrieveView json response but not found")

        # First address save
        self.assertEqual(
            json_data3['status'], 'VOTER_ADDRESS_SAVED',
            "status:  {status} (VOTER_ADDRESS_SAVED expected in voterAddressRetrieveView), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data3['status'], voter_device_id=json_data3['voter_device_id']))

        #######################################
        # Test for expected response variables
        response4 = self.client.get(self.voter_address_retrieve_url)
        json_data4 = json.loads(response4.content)

        # Are any expected fields missing?
        self.assertEqual('success' in json_data4, True,
                         "success expected in the voterAddressRetrieveView json response but not found")
        self.assertEqual('address' in json_data4, True,
                         "address expected in the voterAddressRetrieveView json response but not found")
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
            json_data4['address'], '123 Main Street, Oakland CA 94602',
            "address:  {address} ('123 Main Street, Oakland CA 94602' expected in voterAddressRetrieveView), "
            "voter_device_id: {voter_device_id}".format(
                address=json_data4['address'], voter_device_id=json_data4['voter_device_id']))
