# apis_v1/test_views_organization_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.test import TestCase
import json
from organization.models import Organization


class WeVoteAPIsV1TestsOrganizationRetrieve(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.organization_retrieve_url = reverse("apis_v1:organizationRetrieveView")
        self.organization_count_url = reverse("apis_v1:organizationCountView")
        self.voter_count_url = reverse("apis_v1:voterCountView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")

    def test_count_with_no_cookie(self):
        """
        This API should work even if person isn't signed in
        :return:
        """
        #######################################
        # Check to see if there are 0 organizations
        response = self.client.get(self.organization_count_url)
        json_data = json.loads(response.content.decode())

        self.assertEqual('success' in json_data, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_count' in json_data, True,
                         "'organization_count' expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data['organization_count'], 0,
            "success: {success} (organization_count '0' expected), organization_count: {organization_count}".format(
                success=json_data['success'], organization_count=json_data['organization_count']))

        #######################################
        # Add 3 organizations so we can check count again
        organization1 = Organization.objects.create_organization_simple(
            organization_name="Org1",
            organization_website="www.org1.org",
            organization_twitter_handle="org1",
        )
        organization2 = Organization.objects.create_organization_simple(
            organization_name="Org2",
            organization_website="www.org2.org",
            organization_twitter_handle="org2",
        )
        organization3 = Organization.objects.create_organization_simple(
            organization_name="Org3",
            organization_website="www.org3.org",
            organization_twitter_handle="org3",
        )

        #######################################
        # Check to see if there are 3 organizations
        response2 = self.client.get(self.organization_count_url)
        json_data2 = json.loads(response2.content.decode())

        self.assertEqual('success' in json_data2, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_count' in json_data2, True,
                         "'organization_count' expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data2['organization_count'], 3,
            "success: {success} (organization_count '3' expected), organization_count: {organization_count}".format(
                success=json_data2['success'], organization_count=json_data2['organization_count']))

        #######################################
        # Retrieve 1 organization without required variable
        response3 = self.client.get(self.organization_retrieve_url)
        json_data3 = json.loads(response3.content.decode())

        self.assertEqual('success' in json_data3, True,
                         "'success' variable expected in the organizationRetrieve json response, and not found")
        self.assertEqual('organization_id' in json_data3, True,
                         "'organization_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('organization_we_vote_id' in json_data3, True,
                         "'organization_we_vote_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('status' in json_data3, True,
                         "'status' variable expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data3['success'], False,
            "success: {success} (False expected)".format(
                success=json_data3['success']))
        self.assertEqual(
            json_data3['status'], 'ORGANIZATION_RETRIEVE_BOTH_IDS_MISSING',
            "success: {success} (status 'ORGANIZATION_RETRIEVE_BOTH_IDS_MISSING' expected, status={status})".format(
                success=json_data3['success'], status=json_data3['status']))

        #######################################
        # Retrieve 1 organization with required organization_id
        response4 = self.client.get(self.organization_retrieve_url, {'organization_id': organization1.id})
        json_data4 = json.loads(response4.content.decode())

        self.assertEqual('success' in json_data4, True,
                         "'success' variable expected in the organizationRetrieve json response, and not found")
        self.assertEqual('organization_id' in json_data4, True,
                         "'organization_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('organization_we_vote_id' in json_data4, True,
                         "'organization_we_vote_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('status' in json_data4, True,
                         "'status' variable expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data4['success'], True,
            "success: {success} (True expected)".format(
                success=json_data4['success']))
        self.assertEqual(
            json_data4['status'], 'ORGANIZATION_FOUND_WITH_ID',
            "success: {success} (status 'ORGANIZATION_FOUND_WITH_ID' expected, status={status})".format(
                success=json_data4['success'], status=json_data4['status']))

        #######################################
        # Retrieve 1 organization with required organization_we_vote_id
        response5 = self.client.get(self.organization_retrieve_url, {'organization_we_vote_id': organization1.we_vote_id})
        json_data5 = json.loads(response5.content.decode())

        self.assertEqual('success' in json_data5, True,
                         "'success' variable expected in the organizationRetrieve json response, and not found")
        self.assertEqual('organization_id' in json_data5, True,
                         "'organization_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('organization_we_vote_id' in json_data5, True,
                         "'organization_we_vote_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('status' in json_data5, True,
                         "'status' variable expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data5['success'], True,
            "success: {success} (True expected)".format(
                success=json_data5['success']))
        self.assertEqual(
            json_data5['status'], 'ORGANIZATION_FOUND_WITH_WE_VOTE_ID',
            "success: {success} (status 'ORGANIZATION_FOUND_WITH_WE_VOTE_ID' expected, status={status})".format(
                success=json_data5['success'], status=json_data5['status']))

        #######################################
        # Retrieve 1 organization with required organization_id even if organization_we_vote_id passed in
        response6 = self.client.get(self.organization_retrieve_url, {'organization_id': organization1.id,
                                                                     'organization_we_vote_id': organization1.we_vote_id})
        json_data6 = json.loads(response6.content.decode())

        self.assertEqual('success' in json_data6, True,
                         "'success' variable expected in the organizationRetrieve json response, and not found")
        self.assertEqual('organization_id' in json_data6, True,
                         "'organization_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('organization_we_vote_id' in json_data6, True,
                         "'organization_we_vote_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('status' in json_data6, True,
                         "'status' variable expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data6['success'], True,
            "success: {success} (True expected)".format(
                success=json_data6['success']))
        self.assertEqual(
            json_data6['status'], 'ORGANIZATION_FOUND_WITH_ID',
            "success: {success} (status 'ORGANIZATION_FOUND_WITH_ID' expected, status={status})".format(
                success=json_data6['success'], status=json_data6['status']))

        #######################################
        # FAIL: Try to retrieve 1 organization with required organization_id that is wrong
        response7 = self.client.get(self.organization_retrieve_url, {'organization_id': 888})
        json_data7 = json.loads(response7.content.decode())

        self.assertEqual('success' in json_data7, True,
                         "'success' variable expected in the organizationRetrieve json response, and not found")
        self.assertEqual('organization_id' in json_data7, True,
                         "'organization_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('organization_we_vote_id' in json_data7, True,
                         "'organization_we_vote_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('status' in json_data7, True,
                         "'status' variable expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data7['success'], False,
            "success: {success} (False expected)".format(
                success=json_data7['success']))
        self.assertEqual(
            json_data7['status'], 'ERROR_RETRIEVING_ORGANIZATION_WITH_ID, ORGANIZATION_NOT_FOUND',
            "success: {success} (status 'ERROR_RETRIEVING_ORGANIZATION_WITH_ID, ORGANIZATION_NOT_FOUND' expected, "
            "status={status})".format(
                success=json_data7['success'], status=json_data7['status']))

        #######################################
        # FAIL: Try to retrieve 1 organization with required organization_id that is wrong
        response8 = self.client.get(self.organization_retrieve_url, {'organization_we_vote_id': 'WV_Wrong'})
        json_data8 = json.loads(response8.content.decode())

        self.assertEqual('success' in json_data8, True,
                         "'success' variable expected in the organizationRetrieve json response, and not found")
        self.assertEqual('organization_id' in json_data8, True,
                         "'organization_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('organization_we_vote_id' in json_data8, True,
                         "'organization_we_vote_id' variable expected in the organizationRetrieve json response")
        self.assertEqual('status' in json_data8, True,
                         "'status' variable expected in the organizationRetrieve json response")
        self.assertEqual(
            json_data8['success'], False,
            "success: {success} (False expected)".format(
                success=json_data8['success']))
        self.assertEqual(
            json_data8['status'], 'ERROR_RETRIEVING_ORGANIZATION_WITH_WE_VOTE_ID, ORGANIZATION_NOT_FOUND',
            "success: {success} (status 'ERROR_RETRIEVING_ORGANIZATION_WITH_WE_VOTE_ID, ORGANIZATION_NOT_FOUND' "
            "expected, status={status})".format(
                success=json_data8['success'], status=json_data8['status']))

    # There shouldn't be any difference if there is a signed in voter or not
    # def test_count_with_cookie(self):
