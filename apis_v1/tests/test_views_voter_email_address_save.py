# apis_v1/test_views_voter_email_address_save.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
import json


class WeVoteAPIsV1TestsVoterEmailAddressSave(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_email_address_save_url = reverse("apis_v1:voterEmailAddressSaveView")
        self.voter_email_address_retrieve_url = reverse("apis_v1:voterEmailAddressRetrieveView")
        
    def test_save_with_no_voter_device_id(self):
        response = self.client.post(self.voter_email_address_save_url)
        json_data = json.loads(response.content.decode())
        print("Inside test_views_voter_email_address_save****************")
        #######################################
        # Without a cookie, we don't expect valid response
        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the voterAddressSaveView json response, and not found")
