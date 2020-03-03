from unittest import mock
from collections import namedtuple

from django.test import TestCase

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
