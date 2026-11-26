from django.test import SimpleTestCase

from office_held.controllers import generate_office_held_dict_from_office_held_object, \
    generate_office_held_dict_list_from_office_held_object_list
from office_held.models import OfficeHeld, OfficesHeldForLocation


class GenerateOfficeHeldDictTest(SimpleTestCase):
    def setUp(self):
        self.office_held_fields = {
            'district_id': 'district-1',
            'district_name': 'District 1',
            'ocd_division_id': 'ocd-division/country:us/state:ca',
            'office_explanation_we_vote_id': 'wv-office-explanation-1',
            'office_held_description': 'Description',
            'office_held_facebook_url': 'https://facebook.com/mayor',
            'id': 123,
            'office_held_name': 'Mayor',
            'office_held_twitter_handle': '@mayor',
            'office_held_url': 'https://example.com/mayor',
            'we_vote_id': 'wv-office-held-123',
            'primary_party': 'Democratic',
            'race_office_level': 'Local',
            'state_code': 'CA',
            'vote_usa_office_id': 'vote-usa-office-123',
        }
        self.expected_office_held_dict = {
            'district_id': 'district-1',
            'district_name': 'District 1',
            'ocd_division_id': 'ocd-division/country:us/state:ca',
            'office_explanation_we_vote_id': 'wv-office-explanation-1',
            'office_held_description': 'Description',
            'office_held_facebook_url': 'https://facebook.com/mayor',
            'office_held_id': 123,
            'office_held_name': 'Mayor',
            'office_held_twitter_handle': '@mayor',
            'office_held_url': 'https://example.com/mayor',
            'office_held_we_vote_id': 'wv-office-held-123',
            'primary_party': 'Democrat',
            'race_office_level': 'Local',
            'state_code': 'CA',
            'vote_usa_office_id': 'vote-usa-office-123',
        }

    def test_object_and_dictionary_produce_expected_serialization(self):
        office_held = OfficeHeld(**self.office_held_fields)

        self.assertEqual(
            generate_office_held_dict_from_office_held_object(office_held),
            self.expected_office_held_dict,
        )
        self.assertEqual(
            generate_office_held_dict_from_office_held_object(self.office_held_fields),
            self.expected_office_held_dict,
        )

    def test_dictionary_party_display_handles_null_and_empty_values(self):
        for primary_party in (None, ''):
            with self.subTest(primary_party=primary_party):
                office_held_fields = dict(self.office_held_fields, primary_party=primary_party)

                result = generate_office_held_dict_from_office_held_object(office_held_fields)

                self.assertEqual(result['primary_party'], '')

    def test_missing_dictionary_field_raises_key_error(self):
        office_held_fields = dict(self.office_held_fields)
        del office_held_fields['district_id']

        with self.assertRaises(KeyError):
            generate_office_held_dict_from_office_held_object(office_held_fields)

    def test_list_serializer_accepts_mixed_objects_and_dictionaries(self):
        office_held = OfficeHeld(**self.office_held_fields)

        results = generate_office_held_dict_list_from_office_held_object_list(
            office_held_list=[office_held, self.office_held_fields],
        )

        self.assertEqual(results['office_held_dict_list'], [
            self.expected_office_held_dict,
            self.expected_office_held_dict,
        ])
        self.assertTrue(results['success'])


class OfficesHeldForLocationStringTest(SimpleTestCase):
    def test_str_includes_primary_key_and_state_code(self):
        offices_held_for_location = OfficesHeldForLocation(id=123, state_code='CA')

        self.assertEqual(
            str(offices_held_for_location),
            'OfficesHeldForLocation(id=123, state_code=CA)',
        )

    def test_str_omits_missing_state_code(self):
        for state_code in (None, ''):
            with self.subTest(state_code=state_code):
                offices_held_for_location = OfficesHeldForLocation(id=123, state_code=state_code)

                self.assertEqual(str(offices_held_for_location), 'OfficesHeldForLocation(id=123)')

    def test_str_uses_unsaved_fallback(self):
        offices_held_for_location = OfficesHeldForLocation(state_code='CA')

        self.assertEqual(
            str(offices_held_for_location),
            'OfficesHeldForLocation(id=unsaved, state_code=CA)',
        )