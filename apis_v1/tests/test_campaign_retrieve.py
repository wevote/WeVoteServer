# apis_v1/test_campaign_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
 
import json

class WeVoteAPIsV1TestsCampaignRetrieve(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.campaign_retrieve_url = reverse("apis_v1:campaignRetrieveView")
        
#   campaignx = CampaignX.objects.create(
#                     campaign_description=update_values['campaign_description'],
#                     campaign_title=update_values['campaign_title'],
#                     in_draft_mode=True,
#                     started_by_voter_we_vote_id=voter_we_vote_id,
#                     supporters_count=1,
#                 )
#                 campaignx_we_vote_id = campaignx.we_vote_id


