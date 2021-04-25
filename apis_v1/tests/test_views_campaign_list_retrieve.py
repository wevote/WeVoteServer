# apis_v1/test_views_campaign_list_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from admin_tools.controllers import import_data_for_tests
from django.urls import reverse
from django.test import TestCase
import json
from office.models import ContestOffice, ContestOfficeManager


class WeVoteAPIsV1TestsCampaignListRetrieve(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.organization_count_url = reverse("apis_v1:organizationCountView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.campaign_list_retrieve_url = reverse("apis_v1:campaignListRetrieveView")

    def test_retrieve_with_no_voter_device_id(self):
        #######################################
        # Without a cookie or required variables, we don't expect valid response
        response = self.client.get(self.campaign_list_retrieve_url)
        json_data = json.loads(response.content.decode())
        # print(json_data)

        self.assertEqual('status' in json_data, True,
                         "status expected in the json response, and not found")
        self.assertEqual('success' in json_data, True,
                         "success expected in the json response, and not found")
        self.assertEqual(len(json_data['campaignx_list']), 0,
                         "Expected campaignx_list to have length 0, "
                         "actual length = {length}".format(length=len(json_data['campaignx_list'])))
        self.assertEqual(json_data['status'], 'VOTER_WE_VOTE_ID_COULD_NOT_BE_FETCHED ',
        "status: {status} (VOTER_WE_VOTE_ID_COULD_NOT_BE_FETCHED expected), ".format(
            status=json_data['status']))
        self.assertEqual(json_data['success'], False, "success: {success} (success 'False' expected), ".format(
                success=json_data['success']))
        self.assertListEqual(json_data['campaignx_list'], [],
                             "campaignx_list: {campaignx_list} (Empty list expected), ".format(
                campaignx_list=json_data['campaignx_list']))
