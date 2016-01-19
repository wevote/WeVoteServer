# apis_v1/test_views_voter_count.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.http import SimpleCookie
import json
from voter.models import VoterManager
from future.standard_library import install_aliases
# from urllib.parse import urlparse, urlencode
# from urllib.request import urlopen, Request, build_opener, ProxyHandler
# from urllib.error import HTTPError
install_aliases()


class WeVoteAPIsV1TestsVoterCount(TestCase):

    def setUp(self):
        # self.voter_count_url = "http://localhost:8000%s" % reverse("apis_v1:voterCountView")  # Python3?
        self.voter_count_url = reverse("apis_v1:voterCountView")
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        # self.voter_create_url = "http://localhost:8000%s" % reverse("apis_v1:voterCreateView")  # Python3?
        self.voter_create_url = reverse("apis_v1:voterCreateView")

    def test_count_with_no_cookie(self):
        """
        This API should work even if person isn't signed in
        :return:
        """
        #######################################
        # Check to see if there are 0 voters
        response = self.client.get(self.voter_count_url)
        json_data = json.loads(response.content.decode())

        # Python3 solution? Problem is refused connection
        # req = Request(self.voter_count_url)
        # response = urlopen(req)
        # json_data = response.read()

        self.assertEqual('success' in json_data, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_count' in json_data, True,
                         "'voter_count' expected in the voterCount json response")
        self.assertEqual(
            json_data['voter_count'], 0,
            "success: {success} (voter_count '0' expected), voter_count: {voter_count}".format(
                success=json_data['success'], voter_count=json_data['voter_count']))

        #######################################
        # Add 3 voters so we can check count again
        voter_manager = VoterManager()
        email1 = "test@wevoteusa.org"
        voter_manager.create_voter(
            email=email1,
            password="password123",
        )
        email2 = "test2@wevoteusa.org"
        voter_manager.create_voter(
            email=email2,
            password="password123",
        )
        email3 = "test3@wevoteusa.org"
        voter_manager.create_voter(
            email=email3,
            password="password123",
        )

        #######################################
        # Check to see if there are 3 voters
        response2 = self.client.get(self.voter_count_url)
        json_data2 = json.loads(response2.content.decode())

        self.assertEqual('success' in json_data2, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_count' in json_data2, True,
                         "'voter_count' expected in the voterCount json response")
        self.assertEqual(
            json_data2['voter_count'], 3,
            "success: {success} (voter_count '3' expected), voter_count: {voter_count}".format(
                success=json_data2['success'], voter_count=json_data2['voter_count']))

        #######################################
        # Remove data for 3 voters
        voter_manager.delete_voter(email1)
        voter_manager.delete_voter(email2)
        voter_manager.delete_voter(email3)

        #######################################
        # Check to see if there are 0 voters
        response3 = self.client.get(self.voter_count_url)
        json_data3 = json.loads(response3.content.decode())

        self.assertEqual('success' in json_data, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_count' in json_data3, True,
                         "'voter_count' expected in the voterCount json response")
        self.assertEqual(
            json_data3['voter_count'], 0,
            "success: {success} (voter_count '0' expected - 2nd pass), voter_count: {voter_count}".format(
                success=json_data3['success'], voter_count=json_data3['voter_count']))

    def test_count_with_cookie(self):
        """
        Test the various cookie states
        :return:
        """

        #######################################
        # Generate the voter_device_id cookie
        response0 = self.client.get(self.generate_voter_device_id_url)
        json_data0 = json.loads(response0.content.decode())

        # Make sure we got back a voter_device_id we can use
        self.assertEqual('voter_device_id' in json_data0, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Now save the retrieved voter_device_id in a mock cookie
        cookies = SimpleCookie()
        cookies["voter_device_id"] = json_data0['voter_device_id']
        self.client = Client(HTTP_COOKIE=cookies.output(header='', sep='; '))

        #######################################
        # Test for status: VOTER_CREATED
        response02 = self.client.get(self.voter_create_url)
        json_data02 = json.loads(response02.content.decode())

        self.assertEqual('status' in json_data02, True,
                         "status expected in the voterCreateView json response but not found")
        self.assertEqual('voter_device_id' in json_data02, True,
                         "voter_device_id expected in the voterCreateView json response but not found")

        # With a brand new voter_device_id, a new voter record should be created
        self.assertEqual(
            json_data02['status'], 'VOTER_CREATED',
            "status: {status} (VOTER_CREATED expected), voter_device_id: {voter_device_id}".format(
                status=json_data02['status'], voter_device_id=json_data02['voter_device_id']))

        #######################################
        # Check to see if there is 1 voter - i.e., the viewer
        response11 = self.client.get(self.voter_count_url)
        json_data11 = json.loads(response11.content.decode())

        self.assertEqual('success' in json_data11, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_count' in json_data11, True,
                         "'voter_count' expected in the voterCount json response")
        self.assertEqual(
            json_data11['voter_count'], 1,
            "success: {success} (voter_count '1' expected), voter_count: {voter_count}".format(
                success=json_data11['success'], voter_count=json_data11['voter_count']))

        #######################################
        # Add 3 voters so we can check count again
        voter_manager = VoterManager()
        email1 = "test@wevoteusa.org"
        voter_manager.create_voter(
            email=email1,
            password="password123",
        )
        email2 = "test2@wevoteusa.org"
        voter_manager.create_voter(
            email=email2,
            password="password123",
        )
        email3 = "test3@wevoteusa.org"
        voter_manager.create_voter(
            email=email3,
            password="password123",
        )

        #######################################
        # Check to see if there are 4 voters
        response12 = self.client.get(self.voter_count_url)
        json_data12 = json.loads(response12.content.decode())

        self.assertEqual('success' in json_data12, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_count' in json_data12, True,
                         "'voter_count' expected in the voterCount json response")
        self.assertEqual(
            json_data12['voter_count'], 4,
            "success: {success} (voter_count '4' expected), voter_count: {voter_count}".format(
                success=json_data12['success'], voter_count=json_data12['voter_count']))
