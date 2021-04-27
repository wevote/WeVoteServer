# apis_v1/test_position_list_for_voter.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
import json

class WeVoteAPIsV1TestsPositionListForVoter(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.position_list_for_voter_retrieve_url = reverse("apis_v1:positionListForVoterView")
        
    def test_retrieve_with_no_voter_device_id(self):
        response = self.client.get(self.position_list_for_voter_retrieve_url)
        json_data = json.loads(response.content.decode())
        
        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual(json_data['status'],
                         "VALID_VOTER_DEVICE_ID_MISSING_VOTER_POSITION_LIST",
                         "status = {status} Expected status VALID_VOTER_DEVICE_ID_MISSING_VOTER_POSITION_LIST".format(status=json_data['status']))
        
        self.assertEqual(json_data['success'],
                         False,
                         "success = {success} Expected success".format(success=json_data['success']))
        
        self.assertEqual(len(json_data["position_list"]), 0,
                         "Expected position_list to have length 0, "
                         "actual length = {length}".format(length=len(json_data['position_list'])))
