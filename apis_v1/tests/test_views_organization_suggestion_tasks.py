# apis_v1/test_views_organization_suggestion_tasks.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.urlresolvers import reverse
from django.test import TestCase
import json

from follow.models import UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW
from twitter.models import TwitterWhoIFollow, TwitterLinkToOrganization
from voter.models import Voter, VoterDeviceLink


class WeVoteAPIsV1TestsOrganizationSuggestionTasks(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.organization_suggestion_tasks_url = reverse("apis_v1:organizationSuggestionTasksView")

    def test_organization_suggestion_tasks_with_no_voter_device_id(self):
        #######################################
        # Make sure the correct errors are thrown when no one is signed in
        response01 = self.client.get(self.organization_suggestion_tasks_url)
        json_data01 = json.loads(response01.content.decode())

        self.assertEqual('status' in json_data01, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data01, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data01, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual('kind_of_suggestion_task' in json_data01, True,
                         "'kind_of_suggestion_task' expected in the json response, and not found")
        self.assertEqual('kind_of_follow_task' in json_data01, True,
                         "'kind_of_follow_task' expected in the json response, and not found")
        self.assertEqual('organization_suggestion_task_saved' in json_data01, True,
                         "'organization_suggestion_task_saved' expected in the json response, and not found")
        self.assertEqual('organization_suggestion_list' in json_data01, True,
                         "'organization_suggestion_list' expected in the json response, and not found")

        self.assertEqual(
            json_data01['status'], 'VALID_VOTER_DEVICE_ID_MISSING',
            "status: {status} (VALID_VOTER_DEVICE_ID_MISSING expected), voter_device_id: {voter_device_id}".format(
                status=json_data01['status'], voter_device_id=json_data01['voter_device_id']))
        self.assertEqual(json_data01['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data01['voter_device_id'], '',
                         "voter_device_id == '' expected, voter_device_id: {voter_device_id} returned".format(
                             voter_device_id=json_data01['voter_device_id']))
        self.assertEqual(json_data01['kind_of_suggestion_task'], UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW,
                         "kind_of_suggestion_task == UPDATE_SUGGESTIONS_FROM_TWITTER_IDS_I_FOLLOW expected, "
                         "kind_of_suggestion_task: {kind_of_suggestion_task} returned".format(
                             kind_of_suggestion_task=json_data01['kind_of_suggestion_task']))
        self.assertEqual(json_data01['kind_of_follow_task'], '',
                         "kind_of_follow_task == [] expected, "
                         "kind_of_follow_task: {kind_of_follow_task} returned".format(
                             kind_of_follow_task=json_data01['kind_of_follow_task']))
        self.assertEqual(json_data01['organization_suggestion_task_saved'], False,
                         "organization_suggestion_task_saved == False expected, organization_suggestion_task_saved: "
                         "{organization_suggestion_task_saved} returned".format(
                             organization_suggestion_task_saved=json_data01['organization_suggestion_task_saved']))
        self.assertEqual(json_data01['organization_suggestion_list'], [],
                         "organization_suggestion_list == [] expected, organization_suggestion_list: "
                         "{organization_suggestion_list} returned".format(
                             organization_suggestion_list=json_data01['organization_suggestion_list']))

    def test_organization_suggestion_tasks_with_voter_device_id(self):
        #######################################
        # Generate the voter_device_id cookie
        response10 = self.client.get(self.generate_voter_device_id_url)
        json_data10 = json.loads(response10.content.decode())

        # Make sure we got back a voter_device_id we can use
        self.assertEqual('voter_device_id' in json_data10, True,
                         "voter_device_id expected in the deviceIdGenerateView json response")

        # Now put the voter_device_id in a variable we can use below
        voter_device_id = json_data10['voter_device_id'] if 'voter_device_id' in json_data10 else ''

        #######################################
        # Make sure the correct errors are thrown when an kind_of_suggestion_task isn't passed in for a voter that
        # does not exist
        response11 = self.client.get(self.organization_suggestion_tasks_url, {'voter_device_id': voter_device_id})
        json_data11 = json.loads(response11.content.decode())

        self.assertEqual('status' in json_data11, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data11, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data11, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual('organization_suggestion_task_saved' in json_data11, True,
                         "'organization_suggestion_task_saved' expected in the json response, and not found")
        self.assertEqual('organization_suggestion_list' in json_data11, True,
                         "'organization_suggestion_list' expected in the json response, and not found")

        self.assertEqual(
            json_data11['status'], 'VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID',
            "status: {status} (VOTER_NOT_FOUND_FROM_VOTER_DEVICE_ID expected), "
            "voter_device_id: {voter_device_id}".format(
                status=json_data11['status'], voter_device_id=json_data11['voter_device_id']))
        self.assertEqual(json_data11['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data11['organization_suggestion_task_saved'], False,
                         "organization_suggestion_task_saved == False expected, organization_suggestion_task_saved: "
                         "{organization_suggestion_task_saved} returned".format(
                             organization_suggestion_task_saved=json_data11['organization_suggestion_task_saved']))
        self.assertEqual(json_data11['organization_suggestion_list'], [],
                         "organization_suggestion_list == [] expected, organization_suggestion_list: "
                         "{organization_suggestion_list} returned".format(
                             organization_suggestion_list=json_data11['organization_suggestion_list']))

        #######################################
        # Add a voter and twitter ids i follow but do not create twitter link to organization
        # so we can test no organization suggestions to follow
        voter, created = Voter.objects.update_or_create(we_vote_id='wvt3voter1',
                                                        linked_organization_we_vote_id='wvt3org1',
                                                        first_name='WeVote',
                                                        twitter_id=39868320, twitter_name='We Vote',
                                                        twitter_screen_name='wevote')

        VoterDeviceLink.objects.update_or_create(voter_device_id=voter_device_id, voter_id=voter.id)

        TwitterWhoIFollow.objects.update_or_create(twitter_id_of_me=39868320, twitter_id_i_follow=41521318)
        TwitterWhoIFollow.objects.update_or_create(twitter_id_of_me=39868320, twitter_id_i_follow=16535694)

        #######################################
        # Make sure the correct errors are thrown when twitter link to organization is not created
        # for twitter ids i follow
        response12 = self.client.get(self.organization_suggestion_tasks_url, {'voter_device_id': voter_device_id})
        json_data12 = json.loads(response12.content.decode())

        self.assertEqual('status' in json_data12, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data12, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data12, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual('organization_suggestion_task_saved' in json_data12, True,
                         "'organization_suggestion_task_saved' expected in the json response, and not found")
        self.assertEqual('organization_suggestion_list' in json_data12, True,
                         "'organization_suggestion_list' expected in the json response, and not found")

        self.assertEqual(
            json_data12['status'], ' TWITTER_WHO_I_FOLLOW_LIST_RETRIEVED  FAILED retrieve_twitter_link_to_organization'
                                   ' FAILED retrieve_twitter_link_to_organization',
            "status: {status} (TWITTER_WHO_I_FOLLOW_LIST_RETRIEVED  FAILED retrieve_twitter_link_to_organization FAILED"
            " retrieve_twitter_link_to_organization expected), voter_device_id: {voter_device_id}".format
            (status=json_data12['status'], voter_device_id=json_data12['voter_device_id']))
        self.assertEqual(json_data12['success'], False, "success 'False' expected, True returned")
        self.assertEqual(json_data12['organization_suggestion_task_saved'], False,
                         "organization_suggestion_task_saved == False expected, organization_suggestion_task_saved: "
                         "{organization_suggestion_task_saved} returned".format(
                             organization_suggestion_task_saved=json_data12['organization_suggestion_task_saved']))
        self.assertEqual(json_data12['organization_suggestion_list'], [],
                         "organization_suggestion_list == [] expected, organization_suggestion_list: "
                         "{organization_suggestion_list} returned".format(
                             organization_suggestion_list=json_data12['organization_suggestion_list']))

        #######################################
        # Create two twitter link to organization so we can test all suggestions of twitter organizations to follow
        TwitterLinkToOrganization.objects.create(twitter_id=41521318, organization_we_vote_id='wv02org1397')
        TwitterLinkToOrganization.objects.create(twitter_id=16535694, organization_we_vote_id='wv02org1456')

        #######################################
        # Make sure the correct results are given when voter and twitter link to organizations created successfully
        response13 = self.client.get(self.organization_suggestion_tasks_url, {'voter_device_id': voter_device_id})
        json_data13 = json.loads(response13.content.decode())

        self.assertEqual('status' in json_data13, True, "'status' expected in the json response, and not found")
        self.assertEqual('success' in json_data13, True, "'success' expected in the json response, and not found")
        self.assertEqual('voter_device_id' in json_data13, True,
                         "'voter_device_id' expected in the json response, and not found")
        self.assertEqual('organization_suggestion_task_saved' in json_data13, True,
                         "'organization_suggestion_task_saved' expected in the json response, and not found")
        self.assertEqual('organization_suggestion_list' in json_data13, True,
                         "'organization_suggestion_list' expected in the json response, and not found")
        self.assertEqual(
            json_data13['status'], ' TWITTER_WHO_I_FOLLOW_LIST_RETRIEVED  SUGGESTED_ORGANIZATION_TO_FOLLOW_UPDATED '
                                   'RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_TWITTER_USER_ID '
                                   'SUGGESTED_ORGANIZATION_TO_FOLLOW_UPDATED '
                                   'RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_TWITTER_USER_ID',
            "status: {status} ( TWITTER_WHO_I_FOLLOW_LIST_RETRIEVED  SUGGESTED_ORGANIZATION_TO_FOLLOW_UPDATED "
            "RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_TWITTER_USER_ID "
            "SUGGESTED_ORGANIZATION_TO_FOLLOW_UPDATED RETRIEVE_TWITTER_LINK_TO_ORGANIZATION_FOUND_BY_TWITTER_USER_ID "
            "expected), voter_device_id: {voter_device_id}".format
            (status=json_data13['status'], voter_device_id=json_data13['voter_device_id']))
        self.assertEqual(json_data13['success'], True, "success 'True' expected, True returned")
        self.assertEqual(json_data13['organization_suggestion_task_saved'], True,
                         "organization_suggestion_task_saved == True expected, organization_suggestion_task_saved: "
                         "{organization_suggestion_task_saved} returned".format(
                             organization_suggestion_task_saved=json_data13['organization_suggestion_task_saved']))
        self.assertEqual(json_data13['organization_suggestion_list'], [{'organization_we_vote_id': 'wv02org1397'},
                                                                       {'organization_we_vote_id': 'wv02org1456'}],
                         "organization_suggestion_list == [('organization_we_vote_id': 'wv02org1397'), "
                         "('organization_we_vote_id': 'wv02org1456')] expected, organization_suggestion_list:"
                         "{organization_suggestion_list} returned".format
                         (organization_suggestion_list=json_data13['organization_suggestion_list']))
