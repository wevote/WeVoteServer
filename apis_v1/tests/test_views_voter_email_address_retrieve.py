# apis_v1/test_views_voter_email_address_save.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
from email_outbound.models import EmailAddress, EmailManager
import json

class WeVoteAPIsV1TestsVoterEmailAddressRetrieve(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_email_address_save_url = reverse("apis_v1:voterEmailAddressSaveView")
        self.voter_email_address_retrieve_url = reverse("apis_v1:voterEmailAddressRetrieveView")

    def test_retrieve_with_no_voter_device_id(self):
        response = self.client.get(self.voter_email_address_retrieve_url)
        json_data = json.loads(response.content.decode())


        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual(json_data['status'],
                         "VALID_VOTER_DEVICE_ID_MISSING",
                         "status = {status} Expected status VALID_VOTER_DEVICE_ID_MISSING"
                         "voter_device_id: {voter_device_id}".format(status=json_data['status'],
                                                                     voter_device_id=json_data['voter_device_id']))
        self.assertEqual(len(json_data["email_address_list"]), 0,
                         "Expected email_address_list to have length 0, "
                         "actual length = {length}".format(length=len(json_data['email_address_list'])))

    def test_retrieve_with_voter_device_id(self):
        response = self.client.get(self.generate_voter_device_id_url)
        json_data = json.loads(response.content.decode())
        voter_device_id = json_data['voter_device_id'] if 'voter_device_id' in json_data else ''

        # Create a voter so we can test retrieve
        response2 = self.client.get(self.voter_create_url, {'voter_device_id': voter_device_id})
        json_data2 = json.loads(response2.content.decode())

        self.assertEqual('status' in json_data2, True,
                         "status expected in the voterEmailAddressRetrieveView json response but not found")
        self.assertEqual('voter_device_id' in json_data2, True,
                         "voter_device_id expected in the voterEmailAddressRetrieveView json response but not found")
