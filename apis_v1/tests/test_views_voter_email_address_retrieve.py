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
