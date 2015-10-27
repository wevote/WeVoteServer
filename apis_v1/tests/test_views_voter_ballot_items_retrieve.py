# apis_v1/test_views_voter_guides_to_follow_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.http import SimpleCookie
import json
from organization.models import Organization


class WeVoteAPIsV1TestsVoterBallotItemsRetrieve(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.organization_count_url = reverse("apis_v1:organizationCountView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.voter_ballot_items_retrieve_url = reverse("apis_v1:voterBallotItemsRetrieveView")

    def test_retrieve_with_no_cookie(self):
        #######################################
        # Without a cookie, we don't expect valid response
        response = self.client.get(self.voter_ballot_items_retrieve_url)
        json_data = json.loads(response.content)

        self.assertEqual('status' in json_data, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data, True,
                         "voter_device_id expected in the voterBallotItemsRetrieve json response, and not found")

        self.assertEqual(
            json_data['status'], 'ERROR_BALLOT_ITEMS_RETRIEVE_NO_VOTER_DEVICE_ID',
            "status: {status} (ERROR_BALLOT_ITEMS_RETRIEVE_NO_VOTER_DEVICE_ID expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data['status'], voter_device_id=json_data['voter_device_id']))

    def test_retrieve_with_cookie(self):
        """
        Test the various cookie states
        :return:
        """

        #######################################
        # Generate the voter_device_id cookie
        response01 = self.client.get(self.generate_voter_device_id_url)
        json_data01 = json.loads(response01.content)

        # Make sure we got back a voter_device_id we can use
        self.assertEqual('voter_device_id' in json_data01, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Now save the retrieved voter_device_id in a mock cookie
        cookies = SimpleCookie()
        cookies["voter_device_id"] = json_data01['voter_device_id']
        self.client = Client(HTTP_COOKIE=cookies.output(header='', sep='; '))

        #######################################
        # With a cookie, but without a voter_id in the database, we don't expect valid response
        response02 = self.client.get(self.voter_ballot_items_retrieve_url)
        json_data02 = json.loads(response02.content)

        self.assertEqual('status' in json_data02, True, "status expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data02, True,
                         "voter_device_id expected in the voterBallotItemsRetrieve json response, and not found")

        self.assertEqual(
            json_data02['status'], 'ERROR_BALLOT_ITEMS_RETRIEVE_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID',
            "status: {status} (ERROR_BALLOT_ITEMS_RETRIEVE_VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data02['status'], voter_device_id=json_data02['voter_device_id']))

        #######################################
        # Create a voter so we can test retrieve
        response03 = self.client.get(self.voter_create_url)
        json_data03 = json.loads(response03.content)

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
        # Test the response before a google_civic_election_id has been specified
        response04 = self.client.get(self.voter_ballot_items_retrieve_url)
        json_data04 = json.loads(response04.content)

        self.assertEqual('status' in json_data04, True,
                         "status expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual('success' in json_data04, True,
                         "success expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual('voter_device_id' in json_data04, True,
                         "voter_device_id expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual('voter_id' in json_data04, True,
                         "voter_id expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual('ballot_item_list' in json_data04, True,
                         "ballot_item_list expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual(
            json_data04['status'], 'ERROR_BALLOT_ITEMS_RETRIEVE_GOOGLE_CIVIC_ELECTION_ID_MISSING',
            "status: {status} (ERROR_BALLOT_ITEMS_RETRIEVE_GOOGLE_CIVIC_ELECTION_ID_MISSING expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data04['status'], voter_device_id=json_data04['voter_device_id']))

        #######################################
        # Test the response with google_civic_election_id in cookie
        cookies["google_civic_election_id"] = 4162
        self.client = Client(HTTP_COOKIE=cookies.output(header='', sep='; '))

        #######################################
        # Test the response before any ballot_items exist
        response05 = self.client.get(self.voter_ballot_items_retrieve_url)
        json_data05 = json.loads(response05.content)

        self.assertEqual('status' in json_data05, True,
                         "status expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual('success' in json_data05, True,
                         "success expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual('voter_device_id' in json_data05, True,
                         "voter_device_id expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual('voter_id' in json_data05, True,
                         "voter_id expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual('ballot_item_list' in json_data05, True,
                         "ballot_item_list expected in the voterBallotItemsRetrieve json response but not found")
        self.assertEqual(
            json_data05['status'], 'NO_BALLOT_ITEMS_FOUND_0',
            "status: {status} (NO_BALLOT_ITEMS_FOUND_0 expected), voter_device_id: {voter_device_id}".format(
                status=json_data05['status'], voter_device_id=json_data05['voter_device_id']))

        # Test the response with google_civic_election_id in voter record  # TODO

        # Test the response with voter address set, but no google_civic_election_id set  # TODO

        # We don't want to really reach out to Google Civic with these tests because the data comes and goes (unless
        #  we test against the test election?) but we do want to place ballot data and test against that.
