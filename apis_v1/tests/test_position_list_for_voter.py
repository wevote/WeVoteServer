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
