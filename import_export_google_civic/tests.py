from types import SimpleNamespace

from django.test import SimpleTestCase

from import_export_google_civic.controllers_representatives import \
    groom_and_store_office_held_with_representatives_json


class GroomAndStoreOfficeHeldMutableDefaultsTest(SimpleTestCase):
    def test_mutable_defaults_are_independent_between_calls(self):
        first_results = groom_and_store_office_held_with_representatives_json()
        second_results = groom_and_store_office_held_with_representatives_json()

        for key in (
                'office_held_dict_list_for_location',
                'existing_offices_held_by_ocd_and_name_dict',
                'existing_offices_held_by_vote_usa_office_id_dict',
                'existing_representatives_by_office_and_name_dict',
                'existing_representative_to_office_held_links_dict',
                'new_office_held_we_vote_ids_list',
                'new_representative_we_vote_ids_list',
        ):
            with self.subTest(key=key):
                self.assertIsNot(first_results[key], second_results[key])

    def test_none_arguments_are_initialized_to_empty_collections(self):
        results = groom_and_store_office_held_with_representatives_json(
            divisions_dict=None,
            office_held_dict=None,
            officials_list=None,
            office_held_dict_list_for_location=None,
            existing_offices_held_by_ocd_and_name_dict=None,
            existing_offices_held_by_vote_usa_office_id_dict=None,
            existing_representatives_by_office_and_name_dict=None,
            existing_representative_to_office_held_links_dict=None,
            new_office_held_we_vote_ids_list=None,
            new_representative_we_vote_ids_list=None,
            update_or_create_rules=None,
        )

        self.assertEqual(results['office_held_dict_list_for_location'], [])
        self.assertEqual(results['existing_offices_held_by_ocd_and_name_dict'], {})
        self.assertEqual(results['existing_offices_held_by_vote_usa_office_id_dict'], {})
        self.assertEqual(results['existing_representatives_by_office_and_name_dict'], {})
        self.assertEqual(results['existing_representative_to_office_held_links_dict'], {})
        self.assertEqual(results['new_office_held_we_vote_ids_list'], [])
        self.assertEqual(results['new_representative_we_vote_ids_list'], [])

    def test_supplied_empty_collections_are_preserved(self):
        office_held = SimpleNamespace(
            id=1,
            we_vote_id='wv-office-held-1',
            ocd_division_id='ocd-division/test',
            office_held_name='Mayor',
            vote_usa_office_id='vote-usa-office-1',
        )
        location_offices = []
        offices_by_ocd_and_name = {'ocd-division/test': {'Mayor': office_held}}
        offices_by_vote_usa_id = {}
        representatives_by_office_and_name = {}
        representative_to_office_links = {}
        new_office_ids = []
        new_representative_ids = []

        results = groom_and_store_office_held_with_representatives_json(
            divisions_dict={},
            office_held_dict={
                'name': 'Mayor',
                'divisionId': 'ocd-division/test',
                'levels': [],
                'roles': [],
                'officialIndices': [],
            },
            officials_list=[],
            office_held_dict_list_for_location=location_offices,
            existing_offices_held_by_ocd_and_name_dict=offices_by_ocd_and_name,
            existing_offices_held_by_vote_usa_office_id_dict=offices_by_vote_usa_id,
            existing_representatives_by_office_and_name_dict=representatives_by_office_and_name,
            existing_representative_to_office_held_links_dict=representative_to_office_links,
            new_office_held_we_vote_ids_list=new_office_ids,
            new_representative_we_vote_ids_list=new_representative_ids,
            update_or_create_rules={},
        )

        self.assertIs(results['office_held_dict_list_for_location'], location_offices)
        self.assertIs(results['existing_offices_held_by_ocd_and_name_dict'], offices_by_ocd_and_name)
        self.assertIs(results['existing_offices_held_by_vote_usa_office_id_dict'], offices_by_vote_usa_id)
        self.assertIs(results['existing_representatives_by_office_and_name_dict'], representatives_by_office_and_name)
        self.assertIs(results['existing_representative_to_office_held_links_dict'], representative_to_office_links)
        self.assertIs(results['new_office_held_we_vote_ids_list'], new_office_ids)
        self.assertIs(results['new_representative_we_vote_ids_list'], new_representative_ids)
        self.assertEqual(location_offices, [{
            'office_held_name': 'Mayor',
            'office_held_we_vote_id': 'wv-office-held-1',
            'offices_held_display_order': 0,
        }])
        self.assertIs(offices_by_vote_usa_id['vote-usa-office-1'], office_held)