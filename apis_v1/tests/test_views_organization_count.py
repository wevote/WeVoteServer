# apis_v1/test_views_organization_count.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.urls import reverse
from django.test import TestCase
import json
from organization.models import Organization


class WeVoteAPIsV1TestsOrganizationCount(TestCase):

    def setUp(self):
        self.organization_count_url = reverse("apis_v1:organizationCountView")
        self.voter_count_url = reverse("apis_v1:voterCountView")
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")

    def test_count_with_no_voter_device_id(self):
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
                         "'organization_count' expected in the organizationCount json response")
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
                         "'organization_count' expected in the organizationCount json response")
        self.assertEqual(
            json_data2['organization_count'], 3,
            "success: {success} (organization_count '3' expected), organization_count: {organization_count}".format(
                success=json_data2['success'], organization_count=json_data2['organization_count']))

        #######################################
        # Remove data for 3 organizations
        Organization.objects.delete_organization(organization_id=organization1.id)
        Organization.objects.delete_organization(organization_id=organization2.id)
        Organization.objects.delete_organization(organization_id=organization3.id)

        #######################################
        # Check to see if there are 0 organizations
        response3 = self.client.get(self.organization_count_url)
        json_data3 = json.loads(response3.content.decode())

        self.assertEqual('success' in json_data3, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_count' in json_data3, True,
                         "'organization_count' expected in the organizationCount json response")
        self.assertEqual(
            json_data3['organization_count'], 0,
            "success: {success} (organization_count '0' expected - 2nd pass), "
            "organization_count: {organization_count}".format(
                success=json_data3['success'], organization_count=json_data3['organization_count']))

    def test_count_with_voter_device_id(self):
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

        # Now put the voter_device_id in a variable we can use below
        voter_device_id = json_data0['voter_device_id'] if 'voter_device_id' in json_data0 else ''

        #######################################
        # Test for status: VOTER_CREATED
        response02 = self.client.get(self.voter_create_url, {'voter_device_id': voter_device_id})
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
                         "'voter_count' expected in the organizationCount json response")
        self.assertEqual(
            json_data11['voter_count'], 1,
            "success: {success} (voter_count '1' expected), voter_count: {voter_count}".format(
                success=json_data11['success'], voter_count=json_data11['voter_count']))

        #######################################
        # Check to see if there are 0 organizations
        response12 = self.client.get(self.organization_count_url)
        json_data12 = json.loads(response12.content.decode())

        self.assertEqual('success' in json_data12, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_count' in json_data12, True,
                         "'organization_count' expected in the organizationCount json response")
        self.assertEqual(
            json_data12['organization_count'], 0,
            "success: {success} (organization_count '0' expected), organization_count: {organization_count}".format(
                success=json_data12['success'], organization_count=json_data12['organization_count']))

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
        response22 = self.client.get(self.organization_count_url)
        json_data22 = json.loads(response22.content.decode())

        self.assertEqual('success' in json_data22, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_count' in json_data22, True,
                         "'organization_count' expected in the organizationCount json response")
        self.assertEqual(
            json_data22['organization_count'], 3,
            "success: {success} (organization_count '3' expected), organization_count: {organization_count}".format(
                success=json_data22['success'], organization_count=json_data22['organization_count']))

        #######################################
        # Remove data for 3 organizations
        Organization.objects.delete_organization(organization_id=organization1.id)
        Organization.objects.delete_organization(organization_id=organization2.id)
        Organization.objects.delete_organization(organization_id=organization3.id)

        #######################################
        # Check to see if there are 0 organizations
        response23 = self.client.get(self.organization_count_url)
        json_data23 = json.loads(response23.content.decode())

        self.assertEqual('success' in json_data23, True, "'success' expected in the json response, and not found")
        self.assertEqual('organization_count' in json_data23, True,
                         "'organization_count' expected in the organizationCount json response")
        self.assertEqual(
            json_data23['organization_count'], 0,
            "success: {success} (organization_count '0' expected - 2nd pass), "
            "organization_count: {organization_count}".format(
                success=json_data23['success'], organization_count=json_data23['organization_count']))
