from unittest import mock
from collections import namedtuple

from django.test import SimpleTestCase, TestCase

from ballot.models import BallotReturned, BallotReturnedManager


Location = namedtuple('Location', ['address', 'latitude', 'longitude'])


class BallotTestCase(TestCase):
    databases = ["default", "readonly"]

    def setUp(self):
        BallotReturned.objects.create(**{'google_civic_election_id': 4184,
                                         'latitude': 34.6604854,
                                         'longitude': -90.184124,
                                         'normalized_city': 'coldwater',
                                         'normalized_line1': '13247 arkabutla rd',
                                         'normalized_state': 'MS',
                                         'normalized_zip': '38618',
                                         'polling_location_we_vote_id': 'wv01ploc43132',
                                         })
        self.ballot_manager = BallotReturnedManager()

    def test_do_not_return_ballot_in_different_state(self):
        with mock.patch('ballot.models.get_geocoder_for_service') as mock_geopy:
            google_client = mock_geopy('google')()
            google_client.geocode.return_value = Location(address='1200 Broadway Avenue, Oakland, CA 94720, USA',
                                                          latitude=37.8030442, longitude=-122.2739699)

            result = self.ballot_manager.find_closest_ballot_returned('Oakland, CA')
            self.assertEqual(google_client.geocode.call_count, 1)
            self.assertIn('NO_STORED_BALLOT_MATCHES_STATE CA.', result['status'],
                          "status: {status} (GEOCODER_FOUND_LOCATION NO_STORED_BALLOT_MATCHES_STATE CA. expected)"
                          .format(status=result['status']))
            self.assertFalse(result['geocoder_quota_exceeded'])
            self.assertFalse(result['ballot_returned_found'])
            self.assertIsNone(result['ballot_returned'])

    def test_address_not_found(self):
        with mock.patch('ballot.models.get_geocoder_for_service') as mock_geopy:
            google_client = mock_geopy('google')()
            google_client.geocode.return_value = None
            result = self.ballot_manager.find_closest_ballot_returned('blah bal blh, OK')
            self.assertEqual(google_client.geocode.call_count, 1)
            self.assertIn(
                'Geocoder could not find location matching "blah bal blh, OK". Trying City, State. '
                'NO_STORED_BALLOT_MATCHES_STATE OK.',
                result['status'],
                "status: {status} (Geocoder could not find location matching \"blah bal blh, OK\" expected)"
                .format(status=result['status']))
            self.assertFalse(result['geocoder_quota_exceeded'])
            self.assertFalse(result['ballot_returned_found'])
            self.assertIsNone(result['ballot_returned'])

    def test_ballot_found(self):
        ballot_in_ms = BallotReturned.objects.get()
        self.assertEqual(ballot_in_ms.normalized_state, 'MS')
        with mock.patch('ballot.models.get_geocoder_for_service') as mock_geopy:
            google_client = mock_geopy('google')()
            google_client.geocode.return_value = Location(address='Jackson, MS, USA',
                                                          latitude=32.310251, longitude=-90.3289724)
            result = self.ballot_manager.find_closest_ballot_returned('Jackson, MS')
            self.assertIn('GEOCODER_FOUND_LOCATION', result['status'],
                          "status: {status} (GEOCODER_FOUND_LOCATION expected)"
                          .format(status=result['status']))
            self.assertIn('BALLOT_RETURNED_FOUND', result['status'],
                          "status: {status} (BALLOT_RETURNED_FOUND expected)"
                          .format(status=result['status']))
            self.assertFalse(result['geocoder_quota_exceeded'])
            self.assertTrue(result['ballot_returned_found'])
            self.assertEqual(result['ballot_returned'], ballot_in_ms)

    def test_return_closest_ballot(self):
        """ When several ballots match the queried state, return the closest one. """
        ballot_in_jackson = BallotReturned.objects.create(**{'google_civic_election_id': 4184,
                                                             'latitude': 32.269163,
                                                             'longitude': -90.234566,
                                                             'normalized_city': 'jackson',
                                                             'normalized_line1': '1020 w mcdowell rd',
                                                             'normalized_state': 'MS',
                                                             'normalized_zip': '39204',
                                                             'polling_location_we_vote_id': 'wv01ploc42284',
                                                             })
        self.assertEqual(BallotReturned.objects.filter(normalized_state='MS').count(), 2)
        with mock.patch('ballot.models.get_geocoder_for_service') as mock_geopy:
            google_client = mock_geopy('google')()
            google_client.geocode.return_value = Location(address='Jackson, MS, USA',
                                                          latitude=32.310251, longitude=-90.3289724)

            result = self.ballot_manager.find_closest_ballot_returned('Jackson, MS')
            self.assertIn('GEOCODER_FOUND_LOCATION', result['status'],
                          "status: {status} (GEOCODER_FOUND_LOCATION expected)"
                          .format(status=result['status']))
            self.assertIn('BALLOT_RETURNED_FOUND', result['status'],
                          "status: {status} (BALLOT_RETURNED_FOUND expected)"
                          .format(status=result['status']))
            self.assertFalse(result['geocoder_quota_exceeded'])
            self.assertTrue(result['ballot_returned_found'])
            self.assertEqual(result['ballot_returned'], ballot_in_jackson)


class AllBallotItemsNationalElectionTests(SimpleTestCase):
    """State code NA means 'no state' for a single-state election, and 'every state' for a national election."""

    def _retrieve(self, requested_state, election_state_code, election_found=True):
        from ballot.controllers import all_ballot_items_retrieve_for_one_election_for_api

        election = mock.Mock(state_code=election_state_code)
        election_manager = mock.Mock()
        election_manager.retrieve_election.return_value = {
            'election_found': election_found,
            'election': election,
        }
        office_manager = mock.Mock()
        office_manager.retrieve_all_offices_for_upcoming_election.return_value = {
            'success': True,
            'status': '',
            'office_list_found': False,
        }
        measure_manager = mock.Mock()
        measure_manager.retrieve_all_measures_for_upcoming_election.return_value = {
            'success': True,
            'status': '',
            'measure_list_found': False,
        }
        with mock.patch('ballot.controllers.ElectionManager', return_value=election_manager), \
                mock.patch('ballot.controllers.ContestOfficeListManager', return_value=office_manager), \
                mock.patch('ballot.controllers.CandidateListManager'), \
                mock.patch('ballot.controllers.ContestMeasureListManager', return_value=measure_manager):
            all_ballot_items_retrieve_for_one_election_for_api(1000403, requested_state)
        return office_manager, measure_manager

    def test_national_election_requested_as_na_returns_every_state(self):
        office_manager, measure_manager = self._retrieve('NA', '')
        office_manager.retrieve_all_offices_for_upcoming_election.assert_called_once_with(
            1000403, '', True, True)
        measure_manager.retrieve_all_measures_for_upcoming_election.assert_called_once_with(
            google_civic_election_id_list=[1000403],
            state_code='',
            return_list_of_objects=True,
            limit=0,
            read_only=True)

    def test_state_election_requested_as_na_keeps_national_office_filter(self):
        office_manager, measure_manager = self._retrieve('NA', 'KS')
        self.assertEqual(
            office_manager.retrieve_all_offices_for_upcoming_election.call_args[0][1], 'NA')
        self.assertEqual(
            measure_manager.retrieve_all_measures_for_upcoming_election.call_args.kwargs['state_code'], 'NA')

    def test_state_request_is_unchanged(self):
        office_manager, measure_manager = self._retrieve('KS', 'KS')
        self.assertEqual(
            office_manager.retrieve_all_offices_for_upcoming_election.call_args[0][1], 'KS')
        self.assertEqual(
            measure_manager.retrieve_all_measures_for_upcoming_election.call_args.kwargs['state_code'], 'KS')
