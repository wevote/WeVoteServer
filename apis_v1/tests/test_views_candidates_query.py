# apis_v1/test_views_candidates_query.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import json

from django.test import TestCase
from django.urls import reverse

from candidate.models import CandidateCampaign, CandidateListManager, CandidateToOfficeLink
from election.models import Election


class WeVoteAPIsV1TestsCandidatesQuery(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        self.candidates_query_url = reverse("apis_v1:candidatesQueryView")
        self.upcoming_election = Election.objects.create(
            google_civic_election_id='1000564',
            election_name='Massachusetts State Primary',
            election_day_text='2099-11-03',
            state_code='MA',
            ignore_this_election=False,
        )
        self.past_election = Election.objects.create(
            google_civic_election_id='1000001',
            election_name='General Election',
            election_day_text='2020-11-03',
            state_code='TX',
            ignore_this_election=False,
        )
        self.walsh = CandidateCampaign.objects.create(
            we_vote_id='wvtestcand24204',
            candidate_name='Michael C. Walsh',
            state_code='MA',
            is_battleground_race=False,
            twitter_followers_count=10,
        )
        self.bloomberg = CandidateCampaign.objects.create(
            we_vote_id='wvtestcandpast1',
            candidate_name='Michael Bloomberg',
            state_code='TX',
            is_battleground_race=True,
            twitter_followers_count=9999999,
        )
        CandidateToOfficeLink.objects.create(
            candidate_we_vote_id=self.walsh.we_vote_id,
            contest_office_we_vote_id='wvtestoffag',
            google_civic_election_id=1000564,
            state_code='MA',
        )
        CandidateToOfficeLink.objects.create(
            candidate_we_vote_id=self.bloomberg.we_vote_id,
            contest_office_we_vote_id='wvtestofftx',
            google_civic_election_id=1000001,
            state_code='TX',
        )

    def _names_in_order(self, candidate_list):
        return [candidate['ballot_item_display_name'] for candidate in candidate_list]

    def test_search_returns_upcoming_match_before_high_twitter_past(self):
        response = self.client.get(self.candidates_query_url, {
            'searchText': 'Michael',
            'numberRequested': 100,
            'useWeVoteFormat': 1,
        })
        json_data = json.loads(response.content.decode())

        self.assertTrue(json_data['success'])
        names = self._names_in_order(json_data['candidates'])
        self.assertIn('Michael C. Walsh', names)
        self.assertIn('Michael Bloomberg', names)
        self.assertLess(names.index('Michael C. Walsh'), names.index('Michael Bloomberg'))
        self.assertIn('CANDIDATES_RETRIEVED_SEARCH_UPCOMING_THEN_PAST', json_data['status'])
        self.assertGreaterEqual(json_data['candidatesReturnedCount'], 2)
        self.assertGreaterEqual(json_data['candidatesTotalCount'], 2)

        walsh_dict = next(item for item in json_data['candidates'] if item['we_vote_id'] == 'wvtestcand24204')
        election_ids = [
            int(office['google_civic_election_id'])
            for office in walsh_dict.get('contest_office_list', [])
            if office.get('google_civic_election_id')
        ]
        self.assertIn(1000564, election_ids)

    def test_token_match_still_finds_middle_initial(self):
        response = self.client.get(self.candidates_query_url, {
            'searchText': 'Michael Walsh',
            'numberRequested': 100,
            'useWeVoteFormat': 1,
        })
        json_data = json.loads(response.content.decode())
        names = self._names_in_order(json_data['candidates'])
        self.assertIn('Michael C. Walsh', names)
        self.assertNotIn('Michael Bloomberg', names)

    def test_state_filter_on_search_text_path(self):
        response = self.client.get(self.candidates_query_url, {
            'searchText': 'Michael',
            'state': 'MA',
            'numberRequested': 100,
            'useWeVoteFormat': 1,
        })
        json_data = json.loads(response.content.decode())
        names = self._names_in_order(json_data['candidates'])
        self.assertIn('Michael C. Walsh', names)
        self.assertNotIn('Michael Bloomberg', names)

    def test_manager_limit_keeps_upcoming_and_drops_past(self):
        results = CandidateListManager().retrieve_candidates_for_search_text(
            search_string='Michael',
            candidates_limit=1,
            return_list_of_objects=True,
            read_only=True,
        )
        self.assertTrue(results['success'])
        returned_names = [candidate.candidate_name for candidate in results['candidate_list_objects']]
        self.assertEqual(returned_names, ['Michael C. Walsh'])
        self.assertEqual(results['candidates_returned_count'], 1)
        self.assertGreaterEqual(results['candidates_total_count'], 2)
        self.assertIn('SEARCH_RESULTS_CAPPED', results['status'])

    def test_year_path_does_not_use_search_text(self):
        response = self.client.get(self.candidates_query_url, {
            'electionDay': '2020',
            'searchText': 'Michael',
            'numberRequested': 10,
        })
        json_data = json.loads(response.content.decode())
        self.assertTrue(json_data['success'])
        self.assertNotIn('CANDIDATES_RETRIEVED_SEARCH_UPCOMING_THEN_PAST', json_data['status'])
