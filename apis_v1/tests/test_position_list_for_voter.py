# apis_v1/test_position_list_for_voter.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
from datetime import datetime
from position.models import PositionForFriends
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
        self.assertEqual(json_data['status'].strip(),
                         "VALID_VOTER_DEVICE_ID_MISSING_VOTER_POSITION_LIST",
                         "status = {status} Expected status VALID_VOTER_DEVICE_ID_MISSING_VOTER_POSITION_LIST".format(status=json_data['status']))
        
        self.assertEqual(json_data['success'],
                         False,
                         "success = {success} Expected success".format(success=json_data['success']))
        
        self.assertEqual(len(json_data["position_list"]), 0,
                         "Expected position_list to have length 0, "
                         "actual length = {length}".format(length=len(json_data['position_list'])))
                         
    
    def test_retrieve_for_unregistered_user(self):
        #Generate a voter_device_id
        response = self.client.get(self.generate_voter_device_id_url)
        json_data = json.loads(response.content.decode())
        
        self.assertEqual('voter_device_id' in json_data, True, "voter_device_id expected in the json response, and not found")
        voter_device_id = json_data['voter_device_id']
        
        response2 = self.client.get(self.position_list_for_voter_retrieve_url, {'voter_device_id': voter_device_id})
        json_data2 = json.loads(response2.content.decode())
        
        self.assertEqual(json_data2['status'].strip(),
                         "VALID_VOTER_ID_MISSING_VOTER_POSITION_LIST",
                         "status = {status} Expected status VALID_VOTER_ID_MISSING_VOTER_POSITION_LIST".format(status=json_data2['status']))
        
        self.assertEqual(json_data2['success'],
                         False,
                         "success = {success} Expected success".format(success=json_data2['success']))
       
        self.assertEqual(len(json_data2["position_list"]), 0,
                         "Expected position_list to have length 0, "
                         "actual length = {length}".format(length=len(json_data2['position_list'])))
        
    def test_retrieve_for_registered_user(self):
        #Generate a voter_device_id
        response = self.client.get(self.generate_voter_device_id_url)
        json_data = json.loads(response.content.decode())
        
        voter_device_id = json_data['voter_device_id']
        
        #Create a new registered user
        response2 = self.client.get(self.voter_create_url, {'voter_device_id': voter_device_id})
        json_data2 = json.loads(response2.content.decode())
        
        voter_id = json_data2['voter_id']
        voter_we_vote_id = json_data2['voter_we_vote_id']
        
        
        # print("***********************************")
        # print(json_data2)
        # print("***********************************")
        
        # Adds support for one candidate
        voter_position = PositionForFriends(
            date_entered=datetime.now(),
            voter_id=voter_id,
            voter_we_vote_id=voter_we_vote_id,
            candidate_campaign_id=5,
            candidate_campaign_we_vote_id=6,
            contest_measure_id=0,
            contest_measure_we_vote_id=None,
            contest_office_id=0,
            contest_office_we_vote_id=None,
            stance="SUPPORT",
            google_civic_election_id=0,
            state_code=None,
            organization_id=157,
            organization_we_vote_id="wvy9org3",
            politician_id=0,
            politician_we_vote_id=None,
            ballot_item_display_name=None,
            speaker_display_name=None
        )
        
        voter_position.save()
        
        response3 = self.client.get(self.position_list_for_voter_retrieve_url, {'voter_device_id': voter_device_id})
        json_data3 = json.loads(response3.content.decode())
        
        self.assertEqual(json_data3['status'].strip(),
                         "POSITION_LIST_FOR_VOTER_SUCCEEDED",
                         "status = {status} Expected status POSITION_LIST_FOR_VOTER_SUCCEEDED".format(status=json_data3['status']))
        
        self.assertEqual(json_data3['success'],
                         True,
                         "success = {success} Expected success".format(success=json_data3['success']))
                         
        self.assertEqual(len(json_data3["position_list"]), 1,
                         "Expected position_list to have length 1, "
                         "actual length = {length}".format(length=len(json_data3['position_list'])))