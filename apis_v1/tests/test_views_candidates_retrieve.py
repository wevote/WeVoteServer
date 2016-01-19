# apis_v1/test_views_candidates_retrieve.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from admin_tools.controllers import import_data_for_tests
from django.core.urlresolvers import reverse
from django.test import TestCase
import json
from office.models import ContestOffice, ContestOfficeManager


class WeVoteAPIsV1TestsCandidatesRetrieve(TestCase):

    def setUp(self):
        self.generate_voter_device_id_url = reverse("apis_v1:deviceIdGenerateView")
        self.organization_count_url = reverse("apis_v1:organizationCountView")
        self.voter_create_url = reverse("apis_v1:voterCreateView")
        self.candidates_retrieve_url = reverse("apis_v1:candidatesRetrieveView")

    def test_retrieve_with_no_cookie(self):
        #######################################
        # Without a cookie or required variables, we don't expect valid response
        response01 = self.client.get(self.candidates_retrieve_url)
        json_data01 = json.loads(response01.content.decode())

        self.assertEqual('status' in json_data01, True, "status expected in the json response, and not found")
        self.assertEqual('success' in json_data01, True, "success expected in the json response, and not found")
        self.assertEqual('office_id' in json_data01, True, "office_id expected in the json response, and not found")
        self.assertEqual('office_we_vote_id' in json_data01, True,
                         "office_we_vote_id expected in the json response, and not found")
        self.assertEqual('google_civic_election_id' in json_data01, True,
                         "google_civic_election_id expected in the json response, and not found")
        self.assertEqual('candidate_list' in json_data01, True,
                         "candidate_list expected in the json response, and not found")

        self.assertEqual(
            json_data01['status'], 'VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING',
            "status: {status} (VALID_OFFICE_ID_AND_OFFICE_WE_VOTE_ID_MISSING expected), ".format(
                status=json_data01['status']))
        self.assertEqual(json_data01['success'], False, "success: {success} (success 'False' expected), ".format(
                success=json_data01['success']))
        self.assertEqual(json_data01['office_id'], 0, "office_id: {office_id} ('0' expected), ".format(
                office_id=json_data01['office_id']))
        self.assertEqual(json_data01['office_we_vote_id'], '',
                         "office_we_vote_id: {office_we_vote_id} ('' expected), ".format(
                             office_we_vote_id=json_data01['office_we_vote_id']))
        self.assertEqual(json_data01['google_civic_election_id'], 0,
                         "google_civic_election_id: {google_civic_election_id} ('0' expected), ".format(
                             google_civic_election_id=json_data01['google_civic_election_id']))
        self.assertListEqual(json_data01['candidate_list'], [],
                              "candidate_list: {candidate_list} (Empty list expected), ".format(
                candidate_list=json_data01['candidate_list']))

        #######################################
        # We want to import some election-related data so we can test lists
        import_data_for_tests()

        #######################################
        # Retrieve contest_office so we can work with it
        contest_office_manager = ContestOfficeManager()
        results = contest_office_manager.retrieve_contest_office_from_we_vote_id(
            contest_office_we_vote_id='wv01off922')

        self.assertEqual('success' in results, True,
                         "Unable to retrieve contest_office with contest_office_we_vote_id='wv01off922'")

        if results['success']:
            contest_office = results['contest_office']
        else:
            contest_office = ContestOffice()

        self.assertEqual('wv01off922' in contest_office.we_vote_id, True,
                         "contest_office retrieved does not have contest_office.we_vote_id='wv01off922'")

        #######################################
        # We should get a valid response
        response02 = self.client.get(self.candidates_retrieve_url, {'office_we_vote_id': contest_office.we_vote_id})
        json_data02 = json.loads(response02.content.decode())

        self.assertEqual('status' in json_data02, True, "status expected in the json response, and not found")
        self.assertEqual('success' in json_data02, True, "success expected in the json response, and not found")
        self.assertEqual('office_id' in json_data02, True, "office_id expected in the json response, and not found")
        self.assertEqual('office_we_vote_id' in json_data02, True,
                         "office_we_vote_id expected in the json response, and not found")
        self.assertEqual('google_civic_election_id' in json_data02, True,
                         "google_civic_election_id expected in the json response, and not found")
        self.assertEqual('candidate_list' in json_data02, True,
                         "candidate_list expected in the json response, and not found")

        self.assertEqual(
            json_data02['status'], 'CANDIDATES_RETRIEVED',
            "status: {status} (CANDIDATES_RETRIEVED expected), ".format(
                status=json_data02['status']))
        self.assertEqual(json_data02['success'], True, "success: {success} (success 'True' expected), ".format(
                success=json_data02['success']))
        # For this test we don't know what the internal office_id should be
        # self.assertEqual(json_data02['office_id'], 0, "office_id: {office_id} ('0' expected), ".format(
        #         office_id=json_data02['office_id']))
        self.assertEqual(json_data02['office_we_vote_id'], 'wv01off922',
                         "office_we_vote_id: {office_we_vote_id} ('wv01off922' expected), ".format(
                             office_we_vote_id=json_data02['office_we_vote_id']))
        self.assertEqual(json_data02['google_civic_election_id'], '4162',
                         "google_civic_election_id: {google_civic_election_id} ('4162' expected), ".format(
                             google_civic_election_id=json_data02['google_civic_election_id']))
        self.assertEqual(len(json_data02['candidate_list']), 3,
                         "len(candidate_list): {candidate_list_count} (3 candidates expected), ".format(
                             candidate_list_count=len(json_data02['candidate_list'])))
