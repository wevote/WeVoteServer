# apis_v1/test_views_voter_guides_to_follow_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
import json
from organization.models import Organization


class WeVoteAPIsV1TestsVoterGuidesToFollowRetrieve(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.organization_count_url = reverse("apis_v1:organizationCountView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_guides_to_follow_retrieve_url = reverse("apis_v1:voterGuidesToFollowRetrieveView")

    def test_retrieve_with_no_voter_device_id(self):
        #######################################
        # Without a cookie, we don't expect valid response
        response = self.client.get(self.voter_guides_to_follow_retrieve_url)
        json_data = json.loads(response.content.decode())

        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the voterGuidesToFollowRetrieveView json response, and not found")

        self.assertIn(
            'ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID', json_data['status'],
            "status: {status} (ERROR_GUIDES_TO_FOLLOW_NO_VOTER_DEVICE_ID expected), voter_device_id: {voter_device_id}"
            .format(status=json_data['status'], voter_device_id=json_data['voter_device_id']))

    def test_retrieve_with_voter_device_id(self):
        """
        Test the various cookie states
        :return:
        """

        #######################################
        # Generate the voter_device_id cookie
        response01 = self.client.get(self.generate_voter_device_id_url)
        json_data01 = json.loads(response01.content.decode())

        # Make sure we got back a voter_device_id we can use
        self.assertEqual('voter_device_id' in json_data01, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Now put the voter_device_id in a variable we can use below
        voter_device_id = json_data01['voter_device_id'] if 'voter_device_id' in json_data01 else ''

        #######################################
        # With a cookie, but without a voter_id in the database, we don't expect valid response
        response02 = self.client.get(self.voter_guides_to_follow_retrieve_url, {'voter_device_id': voter_device_id})
        json_data02 = json.loads(response02.content.decode())

        self.assertEqual('status' in json_data02, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data02, True,
                         "voter_device_id expected in the voterGuidesToFollowRetrieveView json response, and not found")
        self.assertIn(
            'ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID', json_data02['status'],
            "status: {status} (ERROR_GUIDES_TO_FOLLOW_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID expected), "
            "voter_device_id: {voter_device_id}"
            .format(status=json_data02['status'], voter_device_id=json_data02['voter_device_id']))

        #######################################
        # Create a voter so we can test retrieve
        response03 = self.client.get(self.voter_create_url, {'voter_device_id': voter_device_id})
        json_data03 = json.loads(response03.content.decode())

        self.assertEqual('status' in json_data03, True,
                         "status expected in the voterCreateView json response but not found")
        self.assertEqual('voter_device_id' in json_data03, True,
                         "voter_device_id expected in the voterCreateView json response but not found")

        # With a brand new voter_device_id, a new voter record should be created
        self.assertEqual(
            json_data03['status'], 'VOTER_CREATED',
            "status: {status} (VOTER_CREATED expected), voter_device_id: {voter_device_id}".format(
                status=json_data03['status'], voter_device_id=json_data03['voter_device_id']))

        #######################################
        # Test the response before any voter guides exist
        response04 = self.client.get(self.voter_guides_to_follow_retrieve_url, {'voter_device_id': voter_device_id})
        json_data04 = json.loads(response04.content.decode())

        self.assertEqual('status' in json_data04, True,
                         "status expected in the voterGuidesToFollowRetrieveView json response but not found")
        self.assertEqual('success' in json_data04, True,
                         "success expected in the voterGuidesToFollowRetrieveView json response but not found")
        self.assertEqual('voter_device_id' in json_data04, True,
                         "voter_device_id expected in the voterGuidesToFollowRetrieveView json response but not found")
        self.assertEqual('voter_guides' in json_data04, True,
                         "voter_guides expected in the voterGuidesToFollowRetrieveView json response but not found")
        self.assertEqual('NO_VOTER_GUIDES_FOUND' in json_data04['status'], True,
            "status: {status} ('NO_VOTER_GUIDES_FOUND' expected), voter_device_id: {voter_device_id}".format(
                status=json_data04['status'], voter_device_id=json_data04['voter_device_id']))

        #######################################
        # Create organization
        Organization.objects.create_organization_simple(
            organization_name="Org1",
            organization_website="www.org1.org",
            organization_twitter_handle="org1",
        )

        #######################################
        # Check to make sure there is 1 organization
        response10 = self.client.get(self.organization_count_url)
        json_data10 = json.loads(response10.content.decode())

        self.assertEqual('success' in json_data10, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_count' in json_data10, True,
                         "'organization_count' expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data10['organization_count'], 1,
            "success: {success} (organization_count '1' expected), organization_count: {organization_count}".format(
                success=json_data10['success'], organization_count=json_data10['organization_count']))

        #######################################
        # Create candidate

        #######################################
        # Create position where organization is supporting candidate

        #######################################
        # Test the response with one voter guide
        response40 = self.client.get(self.voter_guides_to_follow_retrieve_url, {'voter_device_id': voter_device_id})
        json_data40 = json.loads(response40.content.decode())

        self.assertEqual('status' in json_data40, True,
                         "status expected in the voterGuidesToFollowRetrieveView json response but not found")
        self.assertEqual('success' in json_data40, True,
                         "success expected in the voterGuidesToFollowRetrieveView json response but not found")
        self.assertEqual('voter_device_id' in json_data40, True,
                         "voter_device_id expected in the voterGuidesToFollowRetrieveView json response but not found")
        self.assertEqual('voter_guides' in json_data40, True,
                         "voter_guides expected in the voterGuidesToFollowRetrieveView json response but not found")
        # Make sure all voter guides returned have the expected array keys
        for one_voter_guide in json_data40['voter_guides']:
            self.assertEqual('google_civic_election_id' in one_voter_guide, True,
                             "google_civic_election_id expected in voterGuidesToFollowRetrieveView json but not found")
            self.assertEqual('voter_guide_owner_type' in one_voter_guide, True,
                             "voter_guide_owner_type expected in voterGuidesToFollowRetrieveView json but not found")
            self.assertEqual('organization_we_vote_id' in one_voter_guide, True,
                             "organization_we_vote_id expected in voterGuidesToFollowRetrieveView json but not found")
            self.assertEqual('public_figure_we_vote_id' in one_voter_guide, True,
                             "public_figure_we_vote_id expected in voterGuidesToFollowRetrieveView json but not found")
            self.assertEqual('owner_voter_id' in one_voter_guide, True,
                             "owner_voter_id expected in voterGuidesToFollowRetrieveView json but not found")
            self.assertEqual('last_updated' in one_voter_guide, True,
                             "last_updated expected in voterGuidesToFollowRetrieveView json but not found")
