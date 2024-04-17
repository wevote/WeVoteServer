# apis_v1/test_views_organization_follow.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
from django.test import Client
import json
from organization.models import Organization
from wevote_functions.functions import convert_to_int


class WeVoteAPIsV1TestsOrganizationFollow(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.organization_follow_url = reverse("apis_v1:organizationFollowView")
        self.organization_follow_ignore_url = reverse("apis_v1:organizationFollowIgnoreView")
        self.organization_stop_following_url = reverse("apis_v1:organizationStopFollowingView")
        self.voter_count_url = reverse("apis_v1:voterCountView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.client2 = Client(headers={"user-agent": 'Mozilla/5.0'})


    def test_follow_with_no_voter_device_id(self):
        #######################################
        # Make sure the correct errors are thrown when no one is signed in
        response01 = self.client2.get(self.organization_follow_url)
        json_data01 = json.loads(response01.content.decode())

        self.assertEqual('status' in json_data01, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data01, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data01, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data01, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertIn('VALID_VOTER_DEVICE_ID_MISSING', json_data01['status'],
                      "status: {status} (VALID_VOTER_DEVICE_ID_MISSING expected), voter_device_id: {voter_device_id}"
                      .format(status=json_data01['status'], voter_device_id=json_data01['voter_device_id']))
        self.assertEqual(json_data01['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data01['organization_id'], 0,
                         "organization_id == 0 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data01['organization_id']))
        self.assertEqual(json_data01['voter_device_id'], '',
                         "voter_device_id == '' expected, voter_device_id: {voter_device_id} returned".format(
                             voter_device_id=json_data01['voter_device_id']))

        #######################################
        # Make sure the correct errors are thrown when no one is signed in
        response02 = self.client2.get(self.organization_follow_ignore_url)
        json_data02 = json.loads(response02.content.decode())

        self.assertEqual('status' in json_data02, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data02, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data02, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data02, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertIn('VALID_VOTER_DEVICE_ID_MISSING', json_data02['status'],
                      "status: {status} (VALID_VOTER_DEVICE_ID_MISSING expected), voter_device_id: {voter_device_id}"
                      .format(status=json_data02['status'], voter_device_id=json_data02['voter_device_id']))
        self.assertEqual(json_data02['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data02['organization_id'], 0,
                         "organization_id == 0 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data02['organization_id']))
        self.assertEqual(json_data02['voter_device_id'], '',
                         "voter_device_id == '' expected, voter_device_id: {voter_device_id} returned".format(
                             voter_device_id=json_data02['voter_device_id']))

        #######################################
        # Make sure the correct errors are thrown when no one is signed in
        response03 = self.client2.get(self.organization_stop_following_url)
        json_data03 = json.loads(response03.content.decode())

        self.assertEqual('status' in json_data03, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data03, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data03, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data03, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertIn('VALID_VOTER_DEVICE_ID_MISSING', json_data03['status'],
                      "status: {status} (VALID_VOTER_DEVICE_ID_MISSING expected), voter_device_id: {voter_device_id}"
                      .format(status=json_data03['status'], voter_device_id=json_data03['voter_device_id']))
        self.assertEqual(json_data03['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data03['organization_id'], 0,
                         "organization_id == 0 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data03['organization_id']))
        self.assertEqual(json_data03['voter_device_id'], '',
                         "voter_device_id == '' expected, voter_device_id: {voter_device_id} returned".format(
                             voter_device_id=json_data03['voter_device_id']))

    def test_follow_with_voter_device_id(self):
        #######################################
        # Generate the voter_device_id cookie
        response10 = self.client2.get(self.generate_voter_device_id_url)
        json_data10 = json.loads(response10.content.decode())

        # Make sure we got back a voter_device_id we can use
        self.assertEqual('voter_device_id' in json_data10, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Now put the voter_device_id in a variable we can use below
        voter_device_id = json_data10['voter_device_id'] if 'voter_device_id' in json_data10 else ''

        #######################################
        # Create a voter so we can test retrieve
        response11 = self.client2.get(self.voter_create_url, {'voter_device_id': voter_device_id})
        json_data11 = json.loads(response11.content.decode())

        self.assertEqual('status' in json_data11, True,
                         "status expected in the voterOrganizationFollowView json response but not found")
        self.assertEqual('voter_device_id' in json_data11, True,
                         "voter_device_id expected in the voterOrganizationFollowView json response but not found")

        # With a brand new voter_device_id, a new voter record should be created
        self.assertEqual(
            json_data11['status'], 'VOTER_CREATED',
            "status: {status} (VOTER_CREATED expected in voterOrganizationFollowView), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data11['status'], voter_device_id=json_data11['voter_device_id']))

        #######################################
        # Make sure the correct errors are thrown when an organization_id isn't passed in
        response12 = self.client2.get(self.organization_follow_url, {'voter_device_id': voter_device_id})
        json_data12 = json.loads(response12.content.decode())

        self.assertEqual('status' in json_data12, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data12, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data12, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data12, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual(
            json_data12['status'], 'VALID_ORGANIZATION_ID_MISSING',
            "status: {status} (VALID_ORGANIZATION_ID_MISSING expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data12['status'], voter_device_id=json_data12['voter_device_id']))
        self.assertEqual(json_data12['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data12['organization_id'], 0,
                         "organization_id == 0 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data12['organization_id']))

        #######################################
        # Make sure the correct errors are thrown when an organization_id isn't passed in
        response13 = self.client2.get(self.organization_follow_ignore_url, {'voter_device_id': voter_device_id})
        json_data13 = json.loads(response13.content.decode())

        self.assertEqual('status' in json_data13, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data13, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data13, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data13, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual(
            json_data13['status'], 'VALID_ORGANIZATION_ID_MISSING',
            "status: {status} (VALID_ORGANIZATION_ID_MISSING expected), voter_device_id: {voter_device_id}".format(
                status=json_data13['status'], voter_device_id=json_data13['voter_device_id']))
        self.assertEqual(json_data13['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data13['organization_id'], 0,
                         "organization_id == 0 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data13['organization_id']))

        #######################################
        # Make sure the correct errors are thrown when an organization_id isn't passed in
        response14 = self.client2.get(self.organization_stop_following_url, {'voter_device_id': voter_device_id})
        json_data14 = json.loads(response14.content.decode())

        self.assertEqual('status' in json_data14, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data14, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data14, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data14, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual(
            json_data14['status'], 'VALID_ORGANIZATION_ID_MISSING',
            "status: {status} (VALID_ORGANIZATION_ID_MISSING expected), voter_device_id: {voter_device_id}".format(
                status=json_data14['status'], voter_device_id=json_data14['voter_device_id']))
        self.assertEqual(json_data14['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data14['organization_id'], 0,
                         "organization_id == 0 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data14['organization_id']))

        #######################################
        # Make sure the correct errors are thrown when an organization_id is passed in for an org that doesn't exist
        response15 = self.client2.get(self.organization_follow_url, {'organization_id': 1,
                                                                    'voter_device_id': voter_device_id})
        json_data15 = json.loads(response15.content.decode())

        self.assertEqual('status' in json_data15, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data15, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data15, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data15, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertIn(
            'ORGANIZATION_NOT_FOUND_ON_CREATE FOLLOWING', json_data15['status'],
            "status: {status} (ORGANIZATION_NOT_FOUND_ON_CREATE FOLLOWING expected), voter_device_id: {voter_device_id}"
            .format(status=json_data15['status'], voter_device_id=json_data15['voter_device_id']))
        self.assertEqual(json_data15['success'], False, "success 'False' expected, True returned")
        self.assertEqual(convert_to_int(json_data15['organization_id']), 1,
                         "organization_id == 1 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data15['organization_id']))

        #######################################
        # Make sure the correct errors are thrown when an organization_id is passed in for an org that doesn't exist
        response16 = self.client2.get(self.organization_follow_ignore_url, {'organization_id': 1,
                                                                           'voter_device_id': voter_device_id})
        json_data16 = json.loads(response16.content.decode())

        self.assertEqual('status' in json_data16, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data16, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data16, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data16, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertIn(
            'ORGANIZATION_NOT_FOUND_ON_CREATE FOLLOW_IGNORE', json_data16['status'],
            "status: {status} (ORGANIZATION_NOT_FOUND_ON_CREATE FOLLOW_IGNORE expected), "
            "voter_device_id: {voter_device_id}"
            .format(status=json_data16['status'], voter_device_id=json_data16['voter_device_id']))
        self.assertEqual(json_data16['success'], False, "success 'False' expected, True returned")
        self.assertEqual(convert_to_int(json_data16['organization_id']), 1,
                         "organization_id == 1 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data16['organization_id']))

        #######################################
        # Make sure the correct errors are thrown when an organization_id is passed in for an org that doesn't exist
        response17 = self.client2.get(self.organization_stop_following_url, {'organization_id': 1,
                                                                            'voter_device_id': voter_device_id})
        json_data17 = json.loads(response17.content.decode())

        self.assertEqual('status' in json_data17, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data17, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data17, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data17, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertIn(
            'ORGANIZATION_NOT_FOUND_ON_CREATE STOP_FOLLOWING', json_data17['status'],
            "status: {status} (ORGANIZATION_NOT_FOUND_ON_CREATE STOP_FOLLOWING expected), "
            "voter_device_id: {voter_device_id}"
            .format(status=json_data17['status'], voter_device_id=json_data17['voter_device_id']))
        self.assertEqual(json_data17['success'], False, "success 'False' expected, True returned")
        self.assertEqual(convert_to_int(json_data17['organization_id']), 1,
                         "organization_id == 1 expected, organization_id: {organization_id} returned".format(
                             organization_id=json_data17['organization_id']))

        #######################################
        # Add an organization so we can test all the 'follow' states
        organization1 = Organization.objects.create_organization_simple(
            organization_name="Org1",
            organization_website="www.org1.org",
            organization_twitter_handle="org1",
        )

        #######################################
        # Make sure the correct results are given when saved successfully
        response18 = self.client2.get(self.organization_follow_url, {'organization_id': organization1.id,
                                                                    'voter_device_id': voter_device_id})
        json_data18 = json.loads(response18.content.decode())

        self.assertEqual('status' in json_data18, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data18, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data18, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data18, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual(
            json_data18['status'].startswith('FOLLOWING'), True,
            "status: {status} (FOLLOWING ADD_POSITION_NETWORK_COUNT_FOR_ONE_ORGANIZATION expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data18['status'], voter_device_id=json_data18['voter_device_id']))
        self.assertEqual(json_data18['success'], True, "success True expected, False returned")
        self.assertEqual(convert_to_int(json_data18['organization_id']), organization1.id,
                         "organization_id returned (organization_id: {organization_id}) didn't match"
                         "original passed in".format(
                             organization_id=json_data18['organization_id']))

        #######################################
        # Make sure the correct results are given when saved successfully
        response19 = self.client2.get(self.organization_follow_ignore_url, {'organization_id': organization1.id,
                                                                           'voter_device_id': voter_device_id})
        json_data19 = json.loads(response19.content.decode())

        self.assertEqual('status' in json_data19, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data19, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data19, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data19, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual(
            json_data19['status'].startswith('IGNORING'), True,
            "status: {status} (IGNORING expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data19['status'], voter_device_id=json_data19['voter_device_id']))
        self.assertEqual(json_data19['success'], True, "success 'True' expected, False returned")
        self.assertEqual(convert_to_int(json_data19['organization_id']), organization1.id,
                         "organization_id returned (organization_id: {organization_id}) didn't match"
                         "original passed in".format(
                             organization_id=json_data19['organization_id']))

        #######################################
        # Make sure the correct results are given when saved successfully
        response20 = self.client2.get(self.organization_stop_following_url, {'organization_id': organization1.id,
                                                                            'voter_device_id': voter_device_id})
        json_data20 = json.loads(response20.content.decode())

        self.assertEqual('status' in json_data20, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data20, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_id' in json_data20, True,
                         "'organization_id' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data20, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual(
            json_data20['status'].startswith('STOPPED_FOLLOWING'), True,
            "status: {status} (STOPPED_FOLLOWING expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data20['status'], voter_device_id=json_data20['voter_device_id']))
        self.assertEqual(json_data20['success'], True, "success 'True' expected, False returned")
        self.assertEqual(convert_to_int(json_data20['organization_id']), organization1.id,
                         "organization_id returned (organization_id: {organization_id}) didn't match"
                         "original passed in".format(
                             organization_id=json_data20['organization_id']))
