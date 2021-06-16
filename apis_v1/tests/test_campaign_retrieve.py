# apis_v1/test_campaign_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
 
import json

class WeVoteAPIsV1TestsCampaignRetrieve(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.campaign_save_url = reverse("apis_v1:campaignSaveView")
        self.campaign_retrieve_url = reverse("apis_v1:campaignRetrieveView")
        self.campaign_retrieve_as_owner = reverse("apis_v1:campaignRetrieveAsOwnerView")
        
    
    def test_campaign_retrieve_with_no_voter_device_id(self):
        voter = self.client
        
        campaign = self.client.get(self.campaign_save_url)
        json001 = json.loads(campaign.content.decode())
        print("\ncampaign_save_url:" + "\n")
        print(json001)
        
        campaign02 = self.client.get(self.campaign_retrieve_url)
        json002 = json.loads(campaign02.content.decode())
        print("\ncampaign_retrieve_url:" + "\n")
        print(json002)
        
    
    def test_campaign_retrieve_with_no_voter_device_id(self):
        response = self.client.get(self.campaign_retrieve_url)
        json_data = json.loads(response.content.decode())
        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        # self.assertEqual(json_data['status'],
        #                  "CAMPAIGNX_NOT_FOUND-MISSING_VARIABLES CAMPAIGNX_RETRIEVE_ERROR ",
        #                  "status = {status} Expected status VALID_VOTER_ID_MISSING".format(status=json_data['status']))
        self.assertEqual(json_data['status'],
                         "VALID_VOTER_ID_MISSING",
                         "status = {status} Expected status VALID_VOTER_ID_MISSING".format(status=json_data['status']))
        self.assertEqual(json_data['success'], False, "success = {success} Expected success FALSE".format(success=json_data['success']))
        

        # self.assertEqual(len(json_data["email_address_list"]), 0,
        #                  "Expected email_address_list to have length 0, "
        #                  "actual length = {length}".format(length=len(json_data['email_address_list'])))
                         
#   campaignx = CampaignX.objects.create(
#                     campaign_description=update_values['campaign_description'],
#                     campaign_title=update_values['campaign_title'],
#                     in_draft_mode=True,
#                     started_by_voter_we_vote_id=voter_we_vote_id,
#                     supporters_count=1,
#                 )
#                 campaignx_we_vote_id = campaignx.we_vote_id


