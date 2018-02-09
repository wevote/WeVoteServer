# import_export_batches/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import MEASURE, CANDIDATE, POLITICIAN
from party.controllers import retrieve_all_party_names_and_ids_api, party_import_from_xml_data
from electoral_district.controllers import electoral_district_import_from_xml_data
from import_export_ctcl.controllers import create_candidate_selection_rows, retrieve_candidate_from_candidate_selection
import codecs
import csv
from django.db import models
from organization.models import ORGANIZATION_TYPE_CHOICES, UNKNOWN, alphanumeric
from position.models import POSITION, POSITION_CHOICES, NO_STANCE
from politician.models import GENDER_CHOICES, UNKNOWN
from urllib.request import Request, urlopen
from django.utils.http import urlquote
from voter_guide.models import ORGANIZATION_WORD
from election.models import ElectionManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, LANGUAGE_CODE_ENGLISH, LANGUAGE_CODE_SPANISH
import urllib
from exception.models import handle_exception
import magic
from datetime import date
import json

import xml.etree.ElementTree as ElementTree

IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
CONTEST_OFFICE = 'CONTEST_OFFICE'
ELECTED_OFFICE = 'ELECTED_OFFICE'

KIND_OF_BATCH_CHOICES = (
    (MEASURE,           'Measure'),
    (ELECTED_OFFICE,    'ElectedOffice'),
    (CONTEST_OFFICE,    'ContestOffice'),
    (CANDIDATE,         'Candidate'),
    (ORGANIZATION_WORD, 'Organization'),
    (POSITION,          'Position'),
    (POLITICIAN,        'Politician'),
    (IMPORT_BALLOT_ITEM,   'Ballot Returned'),
)

IMPORT_TO_BE_DETERMINED = 'IMPORT_TO_BE_DETERMINED'
DO_NOT_PROCESS = 'DO_NOT_PROCESS'
CLEAN_DATA_MANUALLY = 'CLEAN_DATA_MANUALLY'
IMPORT_CREATE = 'IMPORT_CREATE'
IMPORT_ADD_TO_EXISTING = 'IMPORT_ADD_TO_EXISTING'
IMPORT_DATA_ALREADY_MATCHING = 'IMPORT_DATA_ALREADY_MATCHING'
IMPORT_QUERY_ERROR = 'IMPORT_QUERY_ERROR'

KIND_OF_ACTION_CHOICES = (
    (IMPORT_TO_BE_DETERMINED,  'To Be Determined'),
    (DO_NOT_PROCESS,    'Do not process'),
    (IMPORT_CREATE,            'Create'),
    (IMPORT_ADD_TO_EXISTING,   'Add to Existing'),
)

BATCH_SET_SOURCE_CTCL = 'CTCL'
BATCH_SET_SOURCE_IMPORT_EXPORT_ENDORSEMENTS = 'IMPORT_EXPORT_ENDORSEMENTS'

BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES = {
    'candidate_name': 'candidate_name',
    'candidate_ctcl_uuid': 'candidate_ctcl_uuid',
    'candidate_ctcl_person_id': 'candidate_ctcl_person_id',
    'candidate_is_top_ticket': 'candidate_is_top_ticket',
    'candidate_is_incumbent': 'candidate_is_incumbent',
    'candidate_party_name': 'candidate_party_name',
    'candidate_profile_image_url': 'candidate_profile_image_url',
    'candidate_batch_id': 'candidate_batch_id',
    'candidate_twitter_handle': 'candidate_twitter_handle',
    'candidate_url': 'candidate_url (website)',
    'election_day': 'election_day',
    'facebook_url': 'facebook_url',
    'google_civic_election_id': 'google_civic_election_id',
    'state_code': 'state_code',
    'contest_office_we_vote_id': 'contest_office_we_vote_id',
    'contest_office_name': 'contest_office_name',
}

BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES = {
    'contest_office_name': 'contest_office_name',
    'electoral_district_id': 'electoral_district_id',
    'contest_office_batch_id': 'contest_office_batch_id',
    'contest_office_ctcl_uuid': 'contest_office_ctcl_uuid',
    'contest_office_votes_allowed': 'contest_office_votes_allowed',
    'contest_office_number_elected': 'contest_office_number_elected',
    'candidate_name': 'candidate_name',
    'elected_office_id': 'elected_office_id',
    'candidate_selection_id1': 'candidate_selection_id1',
    'candidate_selection_id2': 'candidate_selection_id2',
    'candidate_selection_id3': 'candidate_selection_id3',
    'candidate_selection_id4': 'candidate_selection_id4',
    'candidate_selection_id5': 'candidate_selection_id5',
    'candidate_selection_id6': 'candidate_selection_id6',
    'candidate_selection_id7': 'candidate_selection_id7',
    'candidate_selection_id8': 'candidate_selection_id8',
    'candidate_selection_id9': 'candidate_selection_id9',
    'candidate_selection_id10': 'candidate_selection_id10',
    'election_day': 'election_day',
    'google_civic_election_id': 'google_civic_election_id',
    'state_code': 'state_code',
}

BATCH_IMPORT_KEYS_ACCEPTED_FOR_ELECTED_OFFICES = {
    'elected_office_name': 'elected_office_name',
    'electoral_district_id': 'electoral_district_id',
    'state_code': 'state_code',
    'elected_office_ctcl_uuid': 'elected_office_ctcl_uuid',
    'elected_office_description': 'elected_office_description',
    'elected_office_is_partisan': 'elected_office_is_partisan',
    'elected_office_name_es': 'elected_office_name_es',
    'elected_office_description_es': 'elected_office_description_es',
    'elected_office_batch_id': 'elected_office_batch_id',
}

BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES = {
    'measure_title': 'measure_title',
    'electoral_district_id': 'electoral_district_id',
    'state_code': 'state_code',
    'measure_name': 'measure_name',
    'measure_text': 'measure_text',
    'measure_sub_title': 'measure_sub_title',
    'ctcl_uuid': 'ctcl_uuid',
}

BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS = {
    'organization_address': 'organization_address',
    'organization_city': 'organization_city',
    'organization_contact_name': 'organization_contact_name',
    'organization_facebook': 'organization_facebook',
    'organization_instagram': 'organization_instagram',
    'organization_name': 'organization_name',
    'organization_phone1': 'organization_phone1',
    'organization_phone2': 'organization_phone2',
    'organization_state': 'organization_state',
    'organization_twitter_handle': 'organization_twitter_handle',
    'organization_website': 'organization_website',
    'organization_we_vote_id': 'organization_we_vote_id',
    'organization_zip': 'organization_zip',
    'organization_type': 'organization_type',
    'state_served_code': 'state_served_code',
}
BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS = {
    'politician_full_name': 'politician_full_name',
    'politician_ctcl_uuid': 'politician_ctcl_uuid',
    'politician_twitter_url': 'politician_twitter_url',
    'politician_facebook_id': 'politician_facebook_id',
    'politician_party_name': 'politician_party_name',
    'politician_first_name': 'politician_first_name',
    'politician_middle_name': 'politician_middle_name',
    'politician_last_name': 'politician_last_name',
    'politician_website_url': 'politician_website_url',
    'politician_email_address': 'politician_email_address',
    'politician_youtube_id': 'politician_youtube_id',
    'politician_googleplus_id': 'politician_googleplus_id',
    'politician_phone_number': 'politician_phone_number',
    'politician_batch_id': 'politician_batch_id',
}

BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS = {
    'position_we_vote_id': 'position_we_vote_id',
    'candidate_name': 'candidate_name',
    'candidate_twitter_handle': 'candidate_twitter_handle',
    'contest_office_name': 'contest_office_name',
    'contest_measure_title': 'contest_measure_title',
    'election_day': 'election_day',
    'grade_rating': 'grade_rating',
    'google_civic_election_id': 'google_civic_election_id',
    'more_info_url': 'more_info_url',
    'stance': 'stance (SUPPORT or OPPOSE)',
    'support': 'support (TRUE or FALSE)',
    'oppose': 'oppose (TRUE or FALSE)',
    'percent_rating': 'percent_rating',
    'statement_text': 'statement_text',
    'state_code': 'state_code',
    'organization_name': 'organization_name',
    'organization_we_vote_id': 'organization_we_vote_id',
    'organization_twitter_handle': 'organization_twitter_handle (position owner)',
}

BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS = {
    'polling_location_we_vote_id': 'polling_location_we_vote_id',
    'contest_office_we_vote_id': 'contest_office_we_vote_id',
    'contest_office_name': 'contest_office_name',
    'candidate_name': 'candidate_name',
    'candidate_twitter_handle': 'candidate_twitter_handle',
    'contest_measure_we_vote_id': 'contest_measure_we_vote_id',
    'contest_measure_name': 'contest_measure_name',
    'local_ballot_order': 'local_ballot_order',
}


logger = wevote_functions.admin.get_logger(__name__)


def get_value_if_index_in_list(incoming_list, index):
    try:
        return incoming_list[index]
    except IndexError:
        return ""


def get_header_map_value_if_index_in_list(incoming_list, index, kind_of_batch=""):
    try:
        # The header_value is a value like "Organization Name" or "Street Address"
        original_header_value = incoming_list[index]
        original_header_value_str = str(original_header_value)
        original_header_value_str = original_header_value_str.lower()

        # We want to check to see if there is a suggested We Vote header for this value
        batch_manager = BatchManager()
        header_value_recognized_by_we_vote = batch_manager.fetch_batch_header_translation_suggestion(
            kind_of_batch, original_header_value_str)

        if positive_value_exists(header_value_recognized_by_we_vote):
            return header_value_recognized_by_we_vote
        else:
            return original_header_value_str
    except IndexError:
        return ""


class BatchManager(models.Model):

    def __unicode__(self):
        return "BatchManager"

        pass

    def create_batch_from_uri(self, batch_uri, kind_of_batch, google_civic_election_id, organization_we_vote_id):
        # Retrieve the CSV
        response = urllib.request.urlopen(batch_uri)
        csv_data = csv.reader(codecs.iterdecode(response, 'utf-8'))
        batch_file_name = ""
        return self.create_batch_from_csv_data(
            batch_file_name, csv_data, kind_of_batch, google_civic_election_id, organization_we_vote_id)

    def create_batch_from_local_file_upload(
            self, batch_file, kind_of_batch, google_civic_election_id, organization_we_vote_id,
            polling_location_we_vote_id=""):
        if (batch_file.content_type == 'text/csv') or (batch_file.content_type == 'application/vnd.ms-excel'):
            csv_data = csv.reader(codecs.iterdecode(batch_file, 'utf-8'), delimiter=',')
            batch_file_name = batch_file.name
            return self.create_batch_from_csv_data(
                batch_file_name, csv_data, kind_of_batch, google_civic_election_id, organization_we_vote_id,
                polling_location_we_vote_id)

        status = "CREATE_BATCH_FILETYPE_NOT_RECOGNIZED"
        results = {
            'success': False,
            'status': status,
            'batch_header_id': 0,
            'batch_saved': False,
            'number_of_batch_rows': 0,
        }
        return results

    def create_batch_from_csv_data(self, file_name, csv_data, kind_of_batch, google_civic_election_id,
                                   organization_we_vote_id, polling_location_we_vote_id=""):
        first_line = True
        success = False
        status = ""
        number_of_batch_rows = 0
        # limit_for_testing = 5

        # Retrieve from JSON
        # request = Request(batch_uri, headers={'User-Agent': 'Mozilla/5.0'})
        # url_processor = urlopen(request)
        # data = url_processor.read()
        # incoming_data = data.decode('utf-8')
        # structured_json = json.loads(incoming_data)
        # for one_entry in structured_json:

        batch_header_id = 0
        batch_header_map_id = 0
        for line in csv_data:
            if first_line:
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000=get_value_if_index_in_list(line, 0),
                        batch_header_column_001=get_value_if_index_in_list(line, 1),
                        batch_header_column_002=get_value_if_index_in_list(line, 2),
                        batch_header_column_003=get_value_if_index_in_list(line, 3),
                        batch_header_column_004=get_value_if_index_in_list(line, 4),
                        batch_header_column_005=get_value_if_index_in_list(line, 5),
                        batch_header_column_006=get_value_if_index_in_list(line, 6),
                        batch_header_column_007=get_value_if_index_in_list(line, 7),
                        batch_header_column_008=get_value_if_index_in_list(line, 8),
                        batch_header_column_009=get_value_if_index_in_list(line, 9),
                        batch_header_column_010=get_value_if_index_in_list(line, 10),
                        batch_header_column_011=get_value_if_index_in_list(line, 11),
                        batch_header_column_012=get_value_if_index_in_list(line, 12),
                        batch_header_column_013=get_value_if_index_in_list(line, 13),
                        batch_header_column_014=get_value_if_index_in_list(line, 14),
                        batch_header_column_015=get_value_if_index_in_list(line, 15),
                        batch_header_column_016=get_value_if_index_in_list(line, 16),
                        batch_header_column_017=get_value_if_index_in_list(line, 17),
                        batch_header_column_018=get_value_if_index_in_list(line, 18),
                        batch_header_column_019=get_value_if_index_in_list(line, 19),
                        batch_header_column_020=get_value_if_index_in_list(line, 20),
                        batch_header_column_021=get_value_if_index_in_list(line, 21),
                        batch_header_column_022=get_value_if_index_in_list(line, 22),
                        batch_header_column_023=get_value_if_index_in_list(line, 23),
                        batch_header_column_024=get_value_if_index_in_list(line, 24),
                        batch_header_column_025=get_value_if_index_in_list(line, 25),
                        batch_header_column_026=get_value_if_index_in_list(line, 26),
                        batch_header_column_027=get_value_if_index_in_list(line, 27),
                        batch_header_column_028=get_value_if_index_in_list(line, 28),
                        batch_header_column_029=get_value_if_index_in_list(line, 29),
                        batch_header_column_030=get_value_if_index_in_list(line, 30),
                        batch_header_column_031=get_value_if_index_in_list(line, 31),
                        batch_header_column_032=get_value_if_index_in_list(line, 32),
                        batch_header_column_033=get_value_if_index_in_list(line, 33),
                        batch_header_column_034=get_value_if_index_in_list(line, 34),
                        batch_header_column_035=get_value_if_index_in_list(line, 35),
                        batch_header_column_036=get_value_if_index_in_list(line, 36),
                        batch_header_column_037=get_value_if_index_in_list(line, 37),
                        batch_header_column_038=get_value_if_index_in_list(line, 38),
                        batch_header_column_039=get_value_if_index_in_list(line, 39),
                        batch_header_column_040=get_value_if_index_in_list(line, 40),
                        batch_header_column_041=get_value_if_index_in_list(line, 41),
                        batch_header_column_042=get_value_if_index_in_list(line, 42),
                        batch_header_column_043=get_value_if_index_in_list(line, 43),
                        batch_header_column_044=get_value_if_index_in_list(line, 44),
                        batch_header_column_045=get_value_if_index_in_list(line, 45),
                        batch_header_column_046=get_value_if_index_in_list(line, 46),
                        batch_header_column_047=get_value_if_index_in_list(line, 47),
                        batch_header_column_048=get_value_if_index_in_list(line, 48),
                        batch_header_column_049=get_value_if_index_in_list(line, 49),
                        batch_header_column_050=get_value_if_index_in_list(line, 50),
                        )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap

                        # For each line, check for translation suggestions
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000=get_header_map_value_if_index_in_list(line, 0, kind_of_batch),
                            batch_header_map_001=get_header_map_value_if_index_in_list(line, 1, kind_of_batch),
                            batch_header_map_002=get_header_map_value_if_index_in_list(line, 2, kind_of_batch),
                            batch_header_map_003=get_header_map_value_if_index_in_list(line, 3, kind_of_batch),
                            batch_header_map_004=get_header_map_value_if_index_in_list(line, 4, kind_of_batch),
                            batch_header_map_005=get_header_map_value_if_index_in_list(line, 5, kind_of_batch),
                            batch_header_map_006=get_header_map_value_if_index_in_list(line, 6, kind_of_batch),
                            batch_header_map_007=get_header_map_value_if_index_in_list(line, 7, kind_of_batch),
                            batch_header_map_008=get_header_map_value_if_index_in_list(line, 8, kind_of_batch),
                            batch_header_map_009=get_header_map_value_if_index_in_list(line, 9, kind_of_batch),
                            batch_header_map_010=get_header_map_value_if_index_in_list(line, 10, kind_of_batch),
                            batch_header_map_011=get_header_map_value_if_index_in_list(line, 11, kind_of_batch),
                            batch_header_map_012=get_header_map_value_if_index_in_list(line, 12, kind_of_batch),
                            batch_header_map_013=get_header_map_value_if_index_in_list(line, 13, kind_of_batch),
                            batch_header_map_014=get_header_map_value_if_index_in_list(line, 14, kind_of_batch),
                            batch_header_map_015=get_header_map_value_if_index_in_list(line, 15, kind_of_batch),
                            batch_header_map_016=get_header_map_value_if_index_in_list(line, 16, kind_of_batch),
                            batch_header_map_017=get_header_map_value_if_index_in_list(line, 17, kind_of_batch),
                            batch_header_map_018=get_header_map_value_if_index_in_list(line, 18, kind_of_batch),
                            batch_header_map_019=get_header_map_value_if_index_in_list(line, 19, kind_of_batch),
                            batch_header_map_020=get_header_map_value_if_index_in_list(line, 20, kind_of_batch),
                            batch_header_map_021=get_header_map_value_if_index_in_list(line, 21, kind_of_batch),
                            batch_header_map_022=get_header_map_value_if_index_in_list(line, 22, kind_of_batch),
                            batch_header_map_023=get_header_map_value_if_index_in_list(line, 23, kind_of_batch),
                            batch_header_map_024=get_header_map_value_if_index_in_list(line, 24, kind_of_batch),
                            batch_header_map_025=get_header_map_value_if_index_in_list(line, 25, kind_of_batch),
                            batch_header_map_026=get_header_map_value_if_index_in_list(line, 26, kind_of_batch),
                            batch_header_map_027=get_header_map_value_if_index_in_list(line, 27, kind_of_batch),
                            batch_header_map_028=get_header_map_value_if_index_in_list(line, 28, kind_of_batch),
                            batch_header_map_029=get_header_map_value_if_index_in_list(line, 29, kind_of_batch),
                            batch_header_map_030=get_header_map_value_if_index_in_list(line, 30, kind_of_batch),
                            batch_header_map_031=get_header_map_value_if_index_in_list(line, 31, kind_of_batch),
                            batch_header_map_032=get_header_map_value_if_index_in_list(line, 32, kind_of_batch),
                            batch_header_map_033=get_header_map_value_if_index_in_list(line, 33, kind_of_batch),
                            batch_header_map_034=get_header_map_value_if_index_in_list(line, 34, kind_of_batch),
                            batch_header_map_035=get_header_map_value_if_index_in_list(line, 35, kind_of_batch),
                            batch_header_map_036=get_header_map_value_if_index_in_list(line, 36, kind_of_batch),
                            batch_header_map_037=get_header_map_value_if_index_in_list(line, 37, kind_of_batch),
                            batch_header_map_038=get_header_map_value_if_index_in_list(line, 38, kind_of_batch),
                            batch_header_map_039=get_header_map_value_if_index_in_list(line, 39, kind_of_batch),
                            batch_header_map_040=get_header_map_value_if_index_in_list(line, 40, kind_of_batch),
                            batch_header_map_041=get_header_map_value_if_index_in_list(line, 41, kind_of_batch),
                            batch_header_map_042=get_header_map_value_if_index_in_list(line, 42, kind_of_batch),
                            batch_header_map_043=get_header_map_value_if_index_in_list(line, 43, kind_of_batch),
                            batch_header_map_044=get_header_map_value_if_index_in_list(line, 44, kind_of_batch),
                            batch_header_map_045=get_header_map_value_if_index_in_list(line, 45, kind_of_batch),
                            batch_header_map_046=get_header_map_value_if_index_in_list(line, 46, kind_of_batch),
                            batch_header_map_047=get_header_map_value_if_index_in_list(line, 47, kind_of_batch),
                            batch_header_map_048=get_header_map_value_if_index_in_list(line, 48, kind_of_batch),
                            batch_header_map_049=get_header_map_value_if_index_in_list(line, 49, kind_of_batch),
                            batch_header_map_050=get_header_map_value_if_index_in_list(line, 50, kind_of_batch),
                        )
                        batch_header_map_id = batch_header_map.id
                        status += "BATCH_HEADER_MAP_SAVED "

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        if positive_value_exists(file_name):
                            batch_name = str(batch_header_id) + ": " + file_name
                        if not positive_value_exists(batch_name):
                            batch_name = str(batch_header_id) + ": " + kind_of_batch
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch=kind_of_batch,
                            organization_we_vote_id=organization_we_vote_id,
                            polling_location_we_vote_id=polling_location_we_vote_id,
                            # source_uri=batch_uri,
                            )
                        status += "BATCH_DESCRIPTION_SAVED "
                        success = True
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    batch_header_id = 0
                    status += "EXCEPTION_BATCH_HEADER "
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            else:
                # if number_of_batch_rows >= limit_for_testing:
                #     break
                if positive_value_exists(batch_header_id):
                    try:
                        batch_row = BatchRow.objects.create(
                            batch_header_id=batch_header_id,
                            batch_row_000=get_value_if_index_in_list(line, 0),
                            batch_row_001=get_value_if_index_in_list(line, 1),
                            batch_row_002=get_value_if_index_in_list(line, 2),
                            batch_row_003=get_value_if_index_in_list(line, 3),
                            batch_row_004=get_value_if_index_in_list(line, 4),
                            batch_row_005=get_value_if_index_in_list(line, 5),
                            batch_row_006=get_value_if_index_in_list(line, 6),
                            batch_row_007=get_value_if_index_in_list(line, 7),
                            batch_row_008=get_value_if_index_in_list(line, 8),
                            batch_row_009=get_value_if_index_in_list(line, 9),
                            batch_row_010=get_value_if_index_in_list(line, 10),
                            batch_row_011=get_value_if_index_in_list(line, 11),
                            batch_row_012=get_value_if_index_in_list(line, 12),
                            batch_row_013=get_value_if_index_in_list(line, 13),
                            batch_row_014=get_value_if_index_in_list(line, 14),
                            batch_row_015=get_value_if_index_in_list(line, 15),
                            batch_row_016=get_value_if_index_in_list(line, 16),
                            batch_row_017=get_value_if_index_in_list(line, 17),
                            batch_row_018=get_value_if_index_in_list(line, 18),
                            batch_row_019=get_value_if_index_in_list(line, 19),
                            batch_row_020=get_value_if_index_in_list(line, 20),
                            batch_row_021=get_value_if_index_in_list(line, 21),
                            batch_row_022=get_value_if_index_in_list(line, 22),
                            batch_row_023=get_value_if_index_in_list(line, 23),
                            batch_row_024=get_value_if_index_in_list(line, 24),
                            batch_row_025=get_value_if_index_in_list(line, 25),
                            batch_row_026=get_value_if_index_in_list(line, 26),
                            batch_row_027=get_value_if_index_in_list(line, 27),
                            batch_row_028=get_value_if_index_in_list(line, 28),
                            batch_row_029=get_value_if_index_in_list(line, 29),
                            batch_row_030=get_value_if_index_in_list(line, 30),
                            batch_row_031=get_value_if_index_in_list(line, 31),
                            batch_row_032=get_value_if_index_in_list(line, 32),
                            batch_row_033=get_value_if_index_in_list(line, 33),
                            batch_row_034=get_value_if_index_in_list(line, 34),
                            batch_row_035=get_value_if_index_in_list(line, 35),
                            batch_row_036=get_value_if_index_in_list(line, 36),
                            batch_row_037=get_value_if_index_in_list(line, 37),
                            batch_row_038=get_value_if_index_in_list(line, 38),
                            batch_row_039=get_value_if_index_in_list(line, 39),
                            batch_row_040=get_value_if_index_in_list(line, 40),
                            batch_row_041=get_value_if_index_in_list(line, 41),
                            batch_row_042=get_value_if_index_in_list(line, 42),
                            batch_row_043=get_value_if_index_in_list(line, 43),
                            batch_row_044=get_value_if_index_in_list(line, 44),
                            batch_row_045=get_value_if_index_in_list(line, 45),
                            batch_row_046=get_value_if_index_in_list(line, 46),
                            batch_row_047=get_value_if_index_in_list(line, 47),
                            batch_row_048=get_value_if_index_in_list(line, 48),
                            batch_row_049=get_value_if_index_in_list(line, 49),
                            batch_row_050=get_value_if_index_in_list(line, 50),
                        )
                        number_of_batch_rows += 1
                    except Exception as e:
                        # Stop trying to save rows -- break out of the for loop
                        status += "EXCEPTION_BATCH_ROW "
                        break

        results = {
            'success':              success,
            'status':               status,
            'batch_header_id':      batch_header_id,
            'batch_saved':          success,
            'number_of_batch_rows': number_of_batch_rows,
        }
        return results


    def create_batch_header_translation_suggestion(
            self, kind_of_batch, header_value_recognized_by_we_vote, incoming_alternate_header_value):
        """

        :param kind_of_batch:
        :param header_value_recognized_by_we_vote:
        :param incoming_alternate_header_value:
        :return:
        """
        success = False
        status = ""
        suggestion_created = False
        suggestion_updated = False
        header_value_recognized_by_we_vote = header_value_recognized_by_we_vote.lower()
        incoming_alternate_header_value = incoming_alternate_header_value.lower()

        if not positive_value_exists(kind_of_batch) or not positive_value_exists(header_value_recognized_by_we_vote) \
                or not positive_value_exists(incoming_alternate_header_value):
            status += "CREATE_BATCH_HEADER_TRANSLATION_SUGGESTION-MISSING_REQUIRED_VARIABLE "
            results = {
                'success':              success,
                'status':               status,
                'suggestion_created':   suggestion_created,
                'suggestion_updated':   suggestion_updated,
            }
            return results

        if kind_of_batch == CANDIDATE:
            batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES
        elif kind_of_batch == CONTEST_OFFICE:
            batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES
        elif kind_of_batch == ELECTED_OFFICE:
            batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_ELECTED_OFFICES
        elif kind_of_batch == MEASURE:
            batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES
        elif kind_of_batch == ORGANIZATION_WORD:
            batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS
        elif kind_of_batch == POLITICIAN:
            batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS
        elif kind_of_batch == POSITION:
            batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS
        elif kind_of_batch == IMPORT_BALLOT_ITEM:
            batch_import_keys_accepted = BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS
        else:
            batch_import_keys_accepted = {}
        if incoming_alternate_header_value in batch_import_keys_accepted:
            success = True
            status += "SUGGESTION_IS_BATCH_IMPORT_KEY "
            results = {
                'success': success,
                'status': status,
                'suggestion_created': suggestion_created,
                'suggestion_updated': suggestion_updated,
            }
            return results

        try:
            batch_header_translation_suggestion, suggestion_created = BatchHeaderTranslationSuggestion.objects.update_or_create(
                kind_of_batch=kind_of_batch,
                header_value_recognized_by_we_vote=header_value_recognized_by_we_vote,
                incoming_alternate_header_value=incoming_alternate_header_value)
            success = True

            status += "BATCH_HEADER_TRANSLATION_SUGGESTION_SAVED "
        except Exception as e:
            success = False
            status += "BATCH_HEADER_TRANSLATION_SUGGESTION_SAVE_FAILED "

        results = {
            'success':              success,
            'status':               status,
            'suggestion_created':   suggestion_created,
            'suggestion_updated':   suggestion_updated,
        }
        return results

    def fetch_batch_row_count(self, batch_header_id):
        """
        :param batch_header_id:
        :return:
        """

        try:
            batch_row_query = BatchRow.objects.filter(batch_header_id=batch_header_id)
            batch_row_count = batch_row_query.count()
        except BatchRowActionElectedOffice.DoesNotExist:
            batch_row_count = 0
        except Exception as e:
            batch_row_count = 0

        return batch_row_count

    def fetch_batch_row_action_count(self, batch_header_id, kind_of_batch=''):
        """
        :param batch_header_id:
        :param kind_of_batch:
        :return:
        """

        batch_row_action_count = 0
        try:
            if kind_of_batch == CANDIDATE:
                batch_row_action_query = BatchRowActionCandidate.objects.filter(batch_header_id=batch_header_id)
                batch_row_action_count = batch_row_action_query.count()
            elif kind_of_batch == CONTEST_OFFICE:
                batch_row_action_query = BatchRowActionContestOffice.objects.filter(batch_header_id=batch_header_id)
                batch_row_action_count = batch_row_action_query.count()
            elif kind_of_batch == ELECTED_OFFICE:
                batch_row_action_query = BatchRowActionElectedOffice.objects.filter(batch_header_id=batch_header_id)
                batch_row_action_count = batch_row_action_query.count()
            elif kind_of_batch == POLITICIAN:
                batch_row_action_query = BatchRowActionPolitician.objects.filter(batch_header_id=batch_header_id)
                batch_row_action_count = batch_row_action_query.count()
        except Exception as e:
            batch_row_action_count = 0

        return batch_row_action_count

    def retrieve_batch_header_translation_suggestion(self, kind_of_batch, incoming_alternate_header_value):
        """
        We are looking at one header value from a file imported by an admin or volunteer. We want to see if
        there are any suggestions for headers already recognized by We Vote. Ex/ "Organization" -> "organization_name"
        :param kind_of_batch:
        :param incoming_alternate_header_value:
        :return:
        """
        success = False
        status = ""
        batch_header_translation_suggestion_found = False

        if not positive_value_exists(kind_of_batch) or not positive_value_exists(incoming_alternate_header_value):
            status += "RETRIEVE_BATCH_HEADER_TRANSLATION_SUGGESTION-MISSING_REQUIRED_VARIABLE "
            results = {
                'success':                                      success,
                'status':                                       status,
                'batch_header_translation_suggestion':          BatchHeaderTranslationSuggestion(),
                'batch_header_translation_suggestion_found':    batch_header_translation_suggestion_found,
            }
            return results

        try:
            # Note that we don't care about case sensitivity when we search for the alternate value
            batch_header_translation_suggestion = BatchHeaderTranslationSuggestion.objects.get(
                kind_of_batch=kind_of_batch,
                incoming_alternate_header_value__iexact=incoming_alternate_header_value)
            batch_header_translation_suggestion_found = True
            success = True
            status += "BATCH_HEADER_TRANSLATION_SUGGESTION_SAVED "
        except Exception as e:
            batch_header_translation_suggestion = BatchHeaderTranslationSuggestion()
            success = False
            status += "BATCH_HEADER_TRANSLATION_SUGGESTION_SAVE_FAILED "

        results = {
            'success':                                      success,
            'status':                                       status,
            'batch_header_translation_suggestion':          batch_header_translation_suggestion,
            'batch_header_translation_suggestion_found':    batch_header_translation_suggestion_found,
        }
        return results

    def create_batch_row_translation_map(  # TODO This hasn't been built
            self, kind_of_batch, header_value_recognized_by_we_vote, incoming_alternate_header_value):
        success = False
        status = ""

        if not positive_value_exists(kind_of_batch) or not positive_value_exists(header_value_recognized_by_we_vote) \
                or not positive_value_exists(incoming_alternate_header_value):
            status += "CREATE_BATCH_HEADER_TRANSLATION_SUGGESTION-MISSING_REQUIRED_VARIABLE "
            results = {
                'success': success,
                'status': status,
            }
            return results

        try:
            header_value_recognized_by_we_vote = header_value_recognized_by_we_vote.lower()
            incoming_alternate_header_value = incoming_alternate_header_value.lower()
            batch_header_translation_suggestion, created = BatchHeaderTranslationSuggestion.objects.update_or_create(
                kind_of_batch=kind_of_batch,
                header_value_recognized_by_we_vote=header_value_recognized_by_we_vote,
                incoming_alternate_header_value=incoming_alternate_header_value)
            success = True
            status += "BATCH_HEADER_TRANSLATION_SUGGESTION_SAVED "
        except Exception as e:
            success = False
            status += "BATCH_HEADER_TRANSLATION_SUGGESTION_SAVE_FAILED "

        results = {
            'success': success,
            'status': status,
        }
        return results

    def retrieve_batch_row_translation_map(self, kind_of_batch, incoming_alternate_header_value):
        # TODO This hasn't been built yet
        success = False
        status = ""
        batch_header_translation_suggestion_found = False

        if not positive_value_exists(kind_of_batch) or not positive_value_exists(incoming_alternate_header_value):
            status += "RETRIEVE_BATCH_HEADER_TRANSLATION_SUGGESTION-MISSING_REQUIRED_VARIABLE "
            results = {
                'success':                                      success,
                'status':                                       status,
                'batch_header_translation_suggestion':          BatchHeaderTranslationSuggestion(),
                'batch_header_translation_suggestion_found':    batch_header_translation_suggestion_found,
            }
            return results

        try:
            # Note that we don't care about case sensitivity when we search for the alternate value
            batch_header_translation_suggestion = BatchHeaderTranslationSuggestion.objects.get(
                kind_of_batch=kind_of_batch,
                incoming_alternate_header_value__iexact=incoming_alternate_header_value)
            batch_header_translation_suggestion_found = True
            success = True
            status += "BATCH_HEADER_TRANSLATION_SUGGESTION_SAVED "
        except Exception as e:
            batch_header_translation_suggestion = BatchHeaderTranslationSuggestion()
            success = False
            status += "BATCH_HEADER_TRANSLATION_SUGGESTION_SAVE_FAILED "

        results = {
            'success':                                      success,
            'status':                                       status,
            'batch_header_translation_suggestion':          batch_header_translation_suggestion,
            'batch_header_translation_suggestion_found':    batch_header_translation_suggestion_found,
        }
        return results

    def retrieve_batch_row_action_organization(self, batch_header_id, batch_row_id):
        try:
            batch_row_action_organization = BatchRowActionOrganization.objects.get(batch_header_id=batch_header_id,
                                                                                   batch_row_id=batch_row_id)
            batch_row_action_found = True
            success = True
            status = "BATCH_ROW_ACTION_ORGANIZATION_RETRIEVED"
        except BatchRowActionOrganization.DoesNotExist:
            batch_row_action_organization = BatchRowActionOrganization()
            batch_row_action_found = False
            success = True
            status = "BATCH_ROW_ACTION_ORGANIZATION_NOT_FOUND"
        except Exception as e:
            batch_row_action_organization = BatchRowActionOrganization()
            batch_row_action_found = False
            success = False
            status = "BATCH_ROW_ACTION_ORGANIZATION_RETRIEVE_ERROR"

        results = {
            'success':                          success,
            'status':                           status,
            'batch_row_action_found':           batch_row_action_found,
            'batch_row_action_organization':    batch_row_action_organization,
        }
        return results

    def retrieve_batch_row_action_measure(self, batch_header_id, batch_row_id):
        try:
            batch_row_action_measure = BatchRowActionMeasure.objects.get(batch_header_id=batch_header_id,
                                                                         batch_row_id=batch_row_id)
            batch_row_action_found = True
            success = True
            status = "BATCH_ROW_ACTION_MEASURE_RETRIEVED"
        except BatchRowActionMeasure.DoesNotExist:
            batch_row_action_measure = BatchRowActionMeasure()
            batch_row_action_found = False
            success = True
            status = "BATCH_ROW_ACTION_MEASURE_NOT_FOUND"
        except Exception as e:
            batch_row_action_measure = BatchRowActionMeasure()
            batch_row_action_found = False
            success = False
            status = "BATCH_ROW_ACTION_MEASURE_RETRIEVE_ERROR"

        results = {
            'success':                  success,
            'status':                   status,
            'batch_row_action_found':   batch_row_action_found,
            'batch_row_action_measure': batch_row_action_measure,
        }
        return results

    def retrieve_batch_row_action_elected_office(self, batch_header_id, batch_row_id):
        """
        Retrieves data from BatchRowActionElectedOffice table
        :param batch_header_id:
        :param batch_row_id:
        :return:
        """

        try:
            batch_row_action_elected_office = BatchRowActionElectedOffice.objects.get(batch_header_id=batch_header_id,
                                                                                      batch_row_id=batch_row_id)
            batch_row_action_found = True
            success = True
            status = "BATCH_ROW_ACTION_ELECTED_OFFICE_RETRIEVED"
        except BatchRowActionElectedOffice.DoesNotExist:
            batch_row_action_elected_office = BatchRowActionElectedOffice()
            batch_row_action_found = False
            success = True
            status = "BATCH_ROW_ACTION_ELECTED_OFFICE_NOT_FOUND"
        except Exception as e:
            batch_row_action_elected_office = BatchRowActionElectedOffice()
            batch_row_action_found = False
            success = False
            status = "BATCH_ROW_ACTION_ELECTED_OFFICE_RETRIEVE_ERROR"

        results = {
            'success':                          success,
            'status':                           status,
            'batch_row_action_found':           batch_row_action_found,
            'batch_row_action_elected_office':  batch_row_action_elected_office,
        }
        return results

    def retrieve_batch_row_action_contest_office(self, batch_header_id, batch_row_id):
        """
        Retrieves data from BatchRowActionContestOffice table
        :param batch_header_id:
        :param batch_row_id:
        :return:
        """

        try:
            batch_row_action_contest_office = BatchRowActionContestOffice.objects.get(batch_header_id=batch_header_id,
                                                                                      batch_row_id=batch_row_id)
            batch_row_action_found = True
            success = True
            status = "BATCH_ROW_ACTION_CONTEST_OFFICE_RETRIEVED"
        except BatchRowActionContestOffice.DoesNotExist:
            batch_row_action_contest_office = BatchRowActionContestOffice()
            batch_row_action_found = False
            success = True
            status = "BATCH_ROW_ACTION_CONTEST_OFFICE_NOT_FOUND"
        except Exception as e:
            batch_row_action_contest_office = BatchRowActionContestOffice()
            batch_row_action_found = False
            success = False
            status = "BATCH_ROW_ACTION_CONTEST_OFFICE_RETRIEVE_ERROR"

        results = {
            'success':                          success,
            'status':                           status,
            'batch_row_action_found':           batch_row_action_found,
            'batch_row_action_contest_office':  batch_row_action_contest_office,
        }
        return results

    def retrieve_batch_row_action_politician(self, batch_header_id, batch_row_id):
        """
        Retrieves data from BatchRowActionPolitician table
        :param batch_header_id:
        :param batch_row_id:
        :return:
        """

        try:
            batch_row_action_politician = BatchRowActionPolitician.objects.get(batch_header_id=batch_header_id,
                                                                               batch_row_id=batch_row_id)
            batch_row_action_found = True
            success = True
            status = "BATCH_ROW_ACTION_POLITICIAN_RETRIEVED"
        except BatchRowActionPolitician.DoesNotExist:
            batch_row_action_politician = BatchRowActionPolitician()
            batch_row_action_found = False
            success = True
            status = "BATCH_ROW_ACTION_POLITICIAN_NOT_FOUND"
        except Exception as e:
            batch_row_action_politician = BatchRowActionPolitician()
            batch_row_action_found = False
            success = False
            status = "BATCH_ROW_ACTION_POLITICIAN_RETRIEVE_ERROR"

        results = {
            'success':                      success,
            'status':                       status,
            'batch_row_action_found':       batch_row_action_found,
            'batch_row_action_politician':  batch_row_action_politician,
        }
        return results

    def retrieve_batch_row_action_position(self, batch_header_id, batch_row_id):
        """
        Retrieves data from BatchRowActionPosition table
        :param batch_header_id:
        :param batch_row_id:
        :return:
        """

        try:
            batch_row_action_position = BatchRowActionPosition.objects.get(batch_header_id=batch_header_id,
                                                                           batch_row_id=batch_row_id)
            batch_row_action_found = True
            success = True
            status = "BATCH_ROW_ACTION_POSITION_RETRIEVED"
        except BatchRowActionPosition.DoesNotExist:
            batch_row_action_position = BatchRowActionPosition()
            batch_row_action_found = False
            success = True
            status = "BATCH_ROW_ACTION_POSITION_NOT_FOUND"
        except Exception as e:
            batch_row_action_position = BatchRowActionPosition()
            batch_row_action_found = False
            success = False
            status = "BATCH_ROW_ACTION_POSITION_RETRIEVE_ERROR"

        results = {
            'success':                      success,
            'status':                       status,
            'batch_row_action_found':       batch_row_action_found,
            'batch_row_action_position':    batch_row_action_position,
        }
        return results

    def retrieve_batch_row_action_ballot_item(self, batch_header_id, batch_row_id):
        """
        Retrieves data from BatchRowActionBallotItem table
        :param batch_header_id:
        :param batch_row_id:
        :return:
        """

        try:
            batch_row_action_ballot_item = BatchRowActionBallotItem.objects.get(batch_header_id=batch_header_id,
                                                                                batch_row_id=batch_row_id)
            batch_row_action_found = True
            success = True
            status = "BATCH_ROW_ACTION_BALLOT_ITEM_RETRIEVED "
        except BatchRowActionBallotItem.DoesNotExist:
            batch_row_action_ballot_item = BatchRowActionBallotItem()
            batch_row_action_found = False
            success = True
            status = "BATCH_ROW_ACTION_BALLOT_ITEM_NOT_FOUND "
        except Exception as e:
            batch_row_action_ballot_item = BatchRowActionBallotItem()
            batch_row_action_found = False
            success = False
            status = "BATCH_ROW_ACTION_BALLOT_ITEM_RETRIEVE_ERROR "

        results = {
            'success':                      success,
            'status':                       status,
            'batch_row_action_found':       batch_row_action_found,
            'batch_row_action_ballot_item': batch_row_action_ballot_item,
        }
        return results

    def retrieve_batch_row_action_candidate(self, batch_header_id, batch_row_id):
        """
        Retrieves data from BatchRowActionCandidate table
        :param batch_header_id:
        :param batch_row_id:
        :return:
        """

        try:
            batch_row_action_candidate = BatchRowActionCandidate.objects.get(batch_header_id=batch_header_id,
                                                                             batch_row_id=batch_row_id)
            batch_row_action_found = True
            success = True
            status = "BATCH_ROW_ACTION_CANDIDATE_RETRIEVED"
        except BatchRowActionCandidate.DoesNotExist:
            batch_row_action_candidate = BatchRowActionCandidate()
            batch_row_action_found = False
            success = True
            status = "BATCH_ROW_ACTION_CANDIDATE_NOT_FOUND"
        except Exception as e:
            batch_row_action_candidate = BatchRowActionCandidate()
            batch_row_action_found = False
            success = False
            status = "BATCH_ROW_ACTION_CANDIDATE_RETRIEVE_ERROR"

        results = {
            'success':                      success,
            'status':                       status,
            'batch_row_action_found':       batch_row_action_found,
            'batch_row_action_candidate':   batch_row_action_candidate,
        }
        return results

    def retrieve_value_from_batch_row(self, batch_header_name_we_want, batch_header_map, one_batch_row):
        index_number = 0
        batch_header_name_we_want = batch_header_name_we_want.lower().strip()
        number_of_columns = 50
        while index_number < number_of_columns:
            index_number_string = "00" + str(index_number)
            index_number_string = index_number_string[-3:]
            batch_header_map_attribute_name = "batch_header_map_" + index_number_string
            # If this position in the batch_header_map matches the batch_header_name_we_want, then we know what column
            # to look in within one_batch_row for the value
            value_from_batch_header_map = getattr(batch_header_map, batch_header_map_attribute_name)
            if value_from_batch_header_map is None:
                # Break out when we stop getting batch_header_map values
                return ""
            if batch_header_name_we_want == value_from_batch_header_map.lower().strip():
                one_batch_row_attribute_name = "batch_row_" + index_number_string
                value_from_batch_row = getattr(one_batch_row, one_batch_row_attribute_name)
                if isinstance(value_from_batch_row, str):
                    return value_from_batch_row.strip()
                else:
                    return value_from_batch_row
            index_number += 1
        return ""

    def retrieve_column_name_from_batch_row(self, batch_header_name_we_want, batch_header_map):
        """
        Given column name from batch_header_map, retrieve equivalent column name from batch row
        :param batch_header_name_we_want: 
        :param batch_header_map: 
        :return:
        """
        index_number = 0
        batch_header_name_we_want = batch_header_name_we_want.lower().strip()
        number_of_columns = 50
        while index_number < number_of_columns:
            index_number_string = "00" + str(index_number)
            index_number_string = index_number_string[-3:]
            batch_header_map_attribute_name = "batch_header_map_" + index_number_string
            # If this position in the batch_header_map matches the batch_header_name_we_want, then we know what column
            # to look in within one_batch_row for the value, eg: batch_header_map_000 --> measure_batch_id
            value_from_batch_header_map = getattr(batch_header_map, batch_header_map_attribute_name)
            if value_from_batch_header_map is None:
                # Break out when we stop getting batch_header_map values
                return ""
            if batch_header_name_we_want == value_from_batch_header_map.lower().strip():
                one_batch_row_attribute_name = "batch_row_" + index_number_string
                return one_batch_row_attribute_name
            index_number += 1
        return ""

    def find_file_type(self, batch_uri):
        """
        Determines the file type based on file extension. If no known extension, it gets the file type information from
        file magic.
        :param batch_uri:
        :return: filetype - XML, json, csv
        """
        # check for file extension
        batch_uri = batch_uri.lower()
        file_extension = batch_uri.split('.')
        if 'xml' in file_extension:
            filetype = 'xml'
        elif 'json' in file_extension:
            filetype = 'json'
        elif 'csv' in file_extension:
            filetype = 'csv'
        else:
            # if the filetype is neither xml, json nor csv, get the file type info from magic
            file = urllib.request.urlopen(batch_uri)
            filetype = magic.from_buffer(file.read())
            file.close()

        return filetype

    def find_possible_matches(self, kind_of_batch, batch_row_name, incoming_batch_row_value,
                              google_civic_election_id, state_code):
        if kind_of_batch == CONTEST_OFFICE:
            # TODO DALE
            pass
        possible_matches = {
            'New York City Mayor': 'New York City Mayor'
        }

        results = {
            'possible_matches_found': True,
            'possible_matches': possible_matches
        }
        return results

    def create_batch_vip_xml(self, batch_uri, kind_of_batch, google_civic_election_id, organization_we_vote_id):
        """
        Retrieves CTCL data from an xml file - Measure, Office, Candidate, Politician
        :param batch_uri:
        :param kind_of_batch:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :return:
        """
        # Retrieve from XML
        request = urllib.request.urlopen(batch_uri)
        # xml_data = request.read()
        # xml_data = xmltodict.parse(xml_data)
        # # xml_data_list_json = list(xml_data)
        # structured_json = json.dumps(xml_data)

        xml_tree = ElementTree.parse(request)
        request.close()
        xml_root = xml_tree.getroot()

        if xml_root:
            if kind_of_batch == MEASURE:
                return self.store_measure_xml(batch_uri, google_civic_election_id, organization_we_vote_id, xml_root)
            elif kind_of_batch == ELECTED_OFFICE:
                return self.store_elected_office_xml(batch_uri, google_civic_election_id, organization_we_vote_id,
                                                     xml_root)
            elif kind_of_batch == CONTEST_OFFICE:
                return self.store_contest_office_xml(batch_uri, google_civic_election_id, organization_we_vote_id,
                                                     xml_root)
            elif kind_of_batch == CANDIDATE:
                return self.store_candidate_xml(batch_uri, google_civic_election_id, organization_we_vote_id, xml_root)
            elif kind_of_batch == POLITICIAN:
                return self.store_politician_xml(batch_uri, google_civic_election_id, organization_we_vote_id, xml_root)
            else:
                results = {
                    'success': False,
                    'status': '',
                    'batch_header_id': 0,
                    'batch_saved': False,
                    'number_of_batch_rows': 0,
                }
                return results

    def store_measure_xml(self, batch_uri, google_civic_election_id, organization_we_vote_id, xml_root, batch_set_id=0):
        """
        Retrieves Measure data from CTCL xml file
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :param xml_root:
        :param batch_set_id:
        :return:
        """
        # Process BallotMeasureContest data

        number_of_batch_rows = 0
        first_line = True
        success = True
        status = ''
        limit_for_testing = 0
        batch_header_id = 0

        # Look for BallotMeasureContest and create the batch_header first. BallotMeasureContest is the direct child node
        # of VipObject
        ballot_measure_xml_node = xml_root.findall('BallotMeasureContest')
        # if ballot_measure_xml_node is not None:
        for one_ballot_measure in ballot_measure_xml_node:
            if positive_value_exists(limit_for_testing) and number_of_batch_rows >= limit_for_testing:
                break

            # look for relevant child nodes under BallotMeasureContest: id, BallotTitle, BallotSubTitle,
            # ElectoralDistrictId, other::ctcl-uid
            ballot_measure_id = one_ballot_measure.attrib['id']

            ballot_measure_subtitle_node = one_ballot_measure.find('BallotSubTitle/Text')
            if ballot_measure_subtitle_node is not None:
                ballot_measure_subtitle = ballot_measure_subtitle_node.text
            else:
                ballot_measure_subtitle = ''

            ballot_measure_title_node = one_ballot_measure.find('BallotTitle')
            if ballot_measure_title_node is not None:
                ballot_measure_title = one_ballot_measure.find('BallotTitle/Text').text
            else:
                ballot_measure_title = ''

            electoral_district_id_node = one_ballot_measure.find('ElectoralDistrictId')
            if electoral_district_id_node is not None:
                electoral_district_id = electoral_district_id_node.text
            else:
                electoral_district_id = ''

            ctcl_uuid_node = one_ballot_measure.find(
                "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']")
            if ctcl_uuid_node is not None:
                ctcl_uuid = one_ballot_measure.find(
                    "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']/Value").text
            else:
                ctcl_uuid = ''

            ballot_measure_name_node = one_ballot_measure.find('Name')
            if ballot_measure_name_node is not None:
                ballot_measure_name = ballot_measure_name_node.text
            else:
                ballot_measure_name = ''

            if first_line:
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='id',
                        batch_header_column_001='BallotSubTitle',
                        batch_header_column_002='BallotTitle',
                        batch_header_column_003='ElectoralDistrictId',
                        batch_header_column_004='other::ctcl-uuid',
                        batch_header_column_005='Name',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='measure_batch_id',
                            batch_header_map_001='measure_sub_title',
                            batch_header_map_002='measure_title',
                            batch_header_map_003='electoral_district_id',
                            batch_header_map_004='measure_ctcl_uuid',
                            batch_header_map_005='measure_name'
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "MEASURE " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='MEASURE',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            # check for measure_id, title OR subtitle or name AND ctcl_uuid
            if (positive_value_exists(ballot_measure_id) and positive_value_exists(ctcl_uuid) and
                    (positive_value_exists(ballot_measure_subtitle) or positive_value_exists(ballot_measure_title) or
                         positive_value_exists(ballot_measure_name))):

                try:
                    batch_row = BatchRow.objects.create(
                        batch_header_id=batch_header_id,
                        batch_row_000=ballot_measure_id,
                        batch_row_001=ballot_measure_subtitle,
                        batch_row_002=ballot_measure_title,
                        batch_row_003=electoral_district_id,
                        batch_row_004=ctcl_uuid,
                        batch_row_005=ballot_measure_name
                    )
                    number_of_batch_rows += 1
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    status += " EXCEPTION_BATCH_ROW"
                    break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_batch_rows': number_of_batch_rows,
        }
        return results

    def store_elected_office_xml(self, batch_uri, google_civic_election_id, organization_we_vote_id, xml_root,
                                 batch_set_id=0):
        """
        Retrieves Office data from CTCL xml file
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :param xml_root:
        :param batch_set_id
        :return:
        """
        # Process VIP Office data
        number_of_batch_rows = 0
        first_line = True
        success = False
        status = ''
        limit_for_testing = 0
        batch_header_id = 0

        # Look for Office and create the batch_header first. Office is the direct child node
        # of VipObject
        elected_office_xml_node = xml_root.findall('Office')
        # if ballot_measure_xml_node is not None:
        for one_elected_office in elected_office_xml_node:
            if positive_value_exists(limit_for_testing) and number_of_batch_rows >= limit_for_testing:
                break

            # look for relevant child nodes under Office: id, Name, Description, ElectoralDistrictId,
            # IsPartisan, other::ctcl-uid
            elected_office_id = one_elected_office.attrib['id']

            elected_office_name_node = one_elected_office.find("./Name/Text/[@language='"+LANGUAGE_CODE_ENGLISH+"']")
            if elected_office_name_node is not None:
                elected_office_name = elected_office_name_node.text
            else:
                elected_office_name = ""

            elected_office_name_es_node = one_elected_office.find("./Name/Text/[@language='"+LANGUAGE_CODE_SPANISH+"']")
            if elected_office_name_es_node is not None:
                elected_office_name_es = elected_office_name_es_node.text
            else:
                elected_office_name_es = ""

            elected_office_description_node = one_elected_office.find(
                "Description/Text/[@language='"+LANGUAGE_CODE_ENGLISH+"']")
            if elected_office_description_node is not None:
                elected_office_description = elected_office_description_node.text
            else:
                elected_office_description = ""

            elected_office_description_es_node = one_elected_office.find(
                "Description/Text/[@language='"+LANGUAGE_CODE_SPANISH+"']")
            if elected_office_description_es_node is not None:
                elected_office_description_es = elected_office_description_es_node.text
            else:
                elected_office_description_es = ""

            electoral_district_id_node = one_elected_office.find('ElectoralDistrictId')
            if electoral_district_id_node is not None:
                electoral_district_id = electoral_district_id_node.text
            else:
                electoral_district_id = ""

            elected_office_is_partisan_node = one_elected_office.find('IsPartisan')
            if elected_office_is_partisan_node is not None:
                elected_office_is_partisan = elected_office_is_partisan_node.text
            else:
                elected_office_is_partisan = ""

            ctcl_uuid = ""
            ctcl_uuid_node = one_elected_office.find(
                "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']")
            if ctcl_uuid_node is not None:
                ctcl_uuid = one_elected_office.find(
                    "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']/Value").text

            if first_line:
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='id',
                        batch_header_column_001='NameEnglish',
                        batch_header_column_002='NameSpanish',
                        batch_header_column_003='DescriptionEnglish',
                        batch_header_column_004='DescriptionSpanish',
                        batch_header_column_005='ElectoralDistrictId',
                        batch_header_column_006='IsPartisan',
                        batch_header_column_007='other::ctcl-uuid',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='elected_office_batch_id',
                            batch_header_map_001='elected_office_name',
                            batch_header_map_002='elected_office_name_es',
                            batch_header_map_003='elected_office_description',
                            batch_header_map_004='elected_office_description_es',
                            batch_header_map_005='electoral_district_id',
                            batch_header_map_006='elected_office_is_partisan',
                            batch_header_map_007='elected_office_ctcl_uuid',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "ELECTED_OFFICE " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='ELECTED_OFFICE',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            # check for office_batch_id or electoral_district or name AND ctcl_uuid
            if positive_value_exists(elected_office_id) and positive_value_exists(ctcl_uuid) and \
                    (positive_value_exists(electoral_district_id) or positive_value_exists(elected_office_name)) or \
                    positive_value_exists(elected_office_name_es):
                try:
                    batch_row = BatchRow.objects.create(
                        batch_header_id=batch_header_id,
                        batch_row_000=elected_office_id,
                        batch_row_001=elected_office_name,
                        batch_row_002=elected_office_name_es,
                        batch_row_003=elected_office_description,
                        batch_row_004=elected_office_description_es,
                        batch_row_005=electoral_district_id,
                        batch_row_006=elected_office_is_partisan,
                        batch_row_007=ctcl_uuid
                    )
                    number_of_batch_rows += 1
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    status += " EXCEPTION_BATCH_ROW"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_batch_rows': number_of_batch_rows,
        }
        return results

    def store_contest_office_xml(self, batch_uri, google_civic_election_id, organization_we_vote_id, xml_root,
                                 batch_set_id=0):
        """
        Retrieves ContestOffice data from CTCL xml file
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :param xml_root:
        :param batch_set_id
        :return:
        """
        # Process VIP CandidateContest data
        number_of_batch_rows = 0
        first_line = True
        success = True
        status = ''
        limit_for_testing = 0
        batch_header_id = 0

        candidate_selection_id_key_list = [
            'candidate_selection_id_1', 'candidate_selection_id_2', 'candidate_selection_id_3',
            'candidate_selection_id_4', 'candidate_selection_id_5', 'candidate_selection_id_6',
            'candidate_selection_id_7', 'candidate_selection_id_8', 'candidate_selection_id_9',
            'candidate_selection_id_10']
        # Look for CandidateContest and create the batch_header first. CandidateContest is the direct child node
        # of VipObject
        contest_office_xml_node = xml_root.findall('CandidateContest')
        # if contest_office_xml_node is not None:
        for one_contest_office in contest_office_xml_node:
            if positive_value_exists(limit_for_testing) and number_of_batch_rows >= limit_for_testing:
                break

            # look for relevant child nodes under CandidateContest: id, Name, OfficeId, ElectoralDistrictId,
            # other::ctcl-uid, VotesAllowed, NumberElected
            contest_office_id = one_contest_office.attrib['id']

            contest_office_name_node = one_contest_office.find('Name')
            if contest_office_name_node is not None:
                contest_office_name = contest_office_name_node.text
            else:
                contest_office_name = ""

            contest_office_number_elected_node = one_contest_office.find('NumberElected')
            if contest_office_number_elected_node is not None:
                contest_office_number_elected = contest_office_number_elected_node.text
            else:
                contest_office_number_elected = ""

            electoral_district_id_node = one_contest_office.find('ElectoralDistrictId')
            if electoral_district_id_node is not None:
                electoral_district_id = electoral_district_id_node.text
            else:
                electoral_district_id = ""

            contest_office_votes_allowed_node = one_contest_office.find('VotesAllowed')
            if contest_office_votes_allowed_node is not None:
                contest_office_votes_allowed = contest_office_votes_allowed_node.text
            else:
                contest_office_votes_allowed = ""

            elected_office_id_node = one_contest_office.find('OfficeIds')
            if elected_office_id_node is not None:
                elected_office_id = elected_office_id_node.text
            else:
                elected_office_id = ""

            ctcl_uuid = ""
            ctcl_uuid_node = one_contest_office.find(
                "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']")
            if ctcl_uuid_node is not None:
                ctcl_uuid = one_contest_office.find(
                    "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']/Value").text

            candidate_selection_ids_dict = {}
            ballot_selection_ids_node = one_contest_office.find('./BallotSelectionIds')
            if ballot_selection_ids_node is not None:
                ballot_selection_ids_str = ballot_selection_ids_node.text
                if ballot_selection_ids_str:
                    ballot_selection_ids_value_list = ballot_selection_ids_str.split()
                    # for len in ballot_selection_ids_list words,
                    # Assuming that there are maximum 10 ballot selection ids for a given contest office
                    ballot_selection_ids_dict = dict(
                        zip(candidate_selection_id_key_list, ballot_selection_ids_value_list))

                    # move this to batchrowactionContestOffice create if we run into performance/load issue
                    candidate_selection_list = []
                    for key, value in ballot_selection_ids_dict.items():
                        results = retrieve_candidate_from_candidate_selection(value, batch_set_id)
                        if results['candidate_id_found']:
                            candidate_selection_item = results['candidate_selection']
                            candidate_value = candidate_selection_item.contest_office_id
                            candidate_selection_list.append(candidate_value)

                    candidate_selection_ids_dict = dict(zip(candidate_selection_id_key_list, candidate_selection_list))
            if first_line:
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='id',
                        batch_header_column_001='Name',
                        batch_header_column_002='OfficeIds',
                        batch_header_column_003='ElectoralDistrictId',
                        batch_header_column_004='VotesAllowed',
                        batch_header_column_005='NumberElected',
                        batch_header_column_006='other::ctcl-uuid',
                        batch_header_column_007='CandidateSelectionId1',
                        batch_header_column_008='CandidateSelectionId2',
                        batch_header_column_009='CandidateSelectionId3',
                        batch_header_column_010='CandidateSelectionId4',
                        batch_header_column_011='CandidateSelectionId5',
                        batch_header_column_012='CandidateSelectionId6',
                        batch_header_column_013='CandidateSelectionId7',
                        batch_header_column_014='CandidateSelectionId8',
                        batch_header_column_015='CandidateSelectionId9',
                        batch_header_column_016='CandidateSelectionId10',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='contest_office_batch_id',
                            batch_header_map_001='contest_office_name',
                            batch_header_map_002='elected_office_id',
                            batch_header_map_003='electoral_district_id',
                            batch_header_map_004='contest_office_votes_allowed',
                            batch_header_map_005='contest_office_number_elected',
                            batch_header_map_006='contest_office_ctcl_uuid',
                            batch_header_map_007='candidate_selection_id1',
                            batch_header_map_008='candidate_selection_id2',
                            batch_header_map_009='candidate_selection_id3',
                            batch_header_map_010='candidate_selection_id4',
                            batch_header_map_011='candidate_selection_id5',
                            batch_header_map_012='candidate_selection_id6',
                            batch_header_map_013='candidate_selection_id7',
                            batch_header_map_014='candidate_selection_id8',
                            batch_header_map_015='candidate_selection_id9',
                            batch_header_map_016='candidate_selection_id10',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "CONTEST_OFFICE " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='CONTEST_OFFICE',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            # check for contest_office_batch_id or electoral_district or name AND ctcl_uuid
            if positive_value_exists(contest_office_id) and positive_value_exists(ctcl_uuid) and \
                    (positive_value_exists(electoral_district_id) or positive_value_exists(contest_office_name)):
                try:
                    batch_row = BatchRow.objects.create(
                        batch_header_id=batch_header_id,
                        batch_row_000=contest_office_id,
                        batch_row_001=contest_office_name,
                        batch_row_002=elected_office_id,
                        batch_row_003=electoral_district_id,
                        batch_row_004=contest_office_votes_allowed,
                        batch_row_005=contest_office_number_elected,
                        batch_row_006=ctcl_uuid,
                        batch_row_007=candidate_selection_ids_dict.get('candidate_selection_id_1', ''),
                        batch_row_008=candidate_selection_ids_dict.get('candidate_selection_id_2', ''),
                        batch_row_009=candidate_selection_ids_dict.get('candidate_selection_id_3', ''),
                        batch_row_010=candidate_selection_ids_dict.get('candidate_selection_id_4', ''),
                        batch_row_011=candidate_selection_ids_dict.get('candidate_selection_id_5', ''),
                        batch_row_012=candidate_selection_ids_dict.get('candidate_selection_id_6', ''),
                        batch_row_013=candidate_selection_ids_dict.get('candidate_selection_id_7', ''),
                        batch_row_014=candidate_selection_ids_dict.get('candidate_selection_id_8', ''),
                        batch_row_015=candidate_selection_ids_dict.get('candidate_selection_id_9', ''),
                        batch_row_016=candidate_selection_ids_dict.get('candidate_selection_id_10', ''),
                    )
                    number_of_batch_rows += 1
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    status += " EXCEPTION_BATCH_ROW"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_batch_rows': number_of_batch_rows,
        }
        return results

    def store_politician_xml(self, batch_uri, google_civic_election_id, organization_we_vote_id, xml_root,
                             batch_set_id=0):
        """
        Retrieves Politician data from CTCL xml file
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :param xml_root:
        :param batch_set_id
        :return:
        """
        # Process VIP Person data
        number_of_batch_rows = 0
        first_line = True
        success = True
        status = ''
        limit_for_testing = 0
        batch_header_id = 0

        # Get party names and their corresponding party ids
        party_details_list = retrieve_all_party_names_and_ids_api()

        # Look for Person and create the batch_header first. Person is the direct child node
        # of VipObject
        person_xml_node = xml_root.findall('Person')
        for one_person in person_xml_node:
            if positive_value_exists(limit_for_testing) and number_of_batch_rows >= limit_for_testing:
                break

            # look for relevant child nodes under Person: id, FullName, FirstName, LastName, MiddleName, PartyId, Email,
            # PhoneNumber, Website, Twitter, ctcl-uuid
            person_id = one_person.attrib['id']

            person_full_name_node = one_person.find("./FullName/Text/[@language='"+LANGUAGE_CODE_ENGLISH+"']")
            if person_full_name_node is not None:
                person_full_name = person_full_name_node.text
            else:
                person_full_name = ''

            person_first_name_node = one_person.find('FirstName')
            if person_first_name_node is not None:
                person_first_name = person_first_name_node.text
            else:
                person_first_name = ''

            person_middle_name_node = one_person.find('MiddleName')
            if person_middle_name_node is not None:
                person_middle_name = person_middle_name_node.text
            else:
                person_middle_name = ''

            person_last_name_node = one_person.find('LastName')
            if person_last_name_node is not None:
                person_last_name = person_last_name_node.text
            else:
                person_last_name = ''

            person_party_name = ''
            person_party_id_node = one_person.find('PartyId')
            if person_party_id_node is not None:
                person_party_id = person_party_id_node.text
                # get party name from candidate_party_id
                if party_details_list is not None:
                    # party_details_dict =  [entry for entry in party_details_list]
                    for one_party in party_details_list:
                        # get the party name matching person_party_id
                        try:
                            party_id_temp = one_party.get('party_id_temp')
                            if person_party_id == party_id_temp:
                                person_party_name = one_party.get('party_name')
                                break
                        except Exception as e:
                            pass

            person_email_id_node = one_person.find('./ContactInformation/Email')
            if person_email_id_node is not None:
                person_email_id = person_email_id_node.text
            else:
                person_email_id = ''

            person_phone_number_node = one_person.find('./ContactInformation/Phone')
            if person_phone_number_node is not None:
                person_phone_number = person_phone_number_node.text
            else:
                person_phone_number = ''

            person_website_url_node = one_person.find("./ContactInformation/Uri/[@annotation='website']")
            if person_website_url_node is not None:
                person_website_url = person_website_url_node.text
            else:
                person_website_url = ''

            person_facebook_id_node = one_person.find("./ContactInformation/Uri/[@annotation='facebook']")
            if person_facebook_id_node is not None:
                person_facebook_id = person_facebook_id_node.text
            else:
                person_facebook_id = ''

            person_twitter_id_node = one_person.find("./ContactInformation/Uri/[@annotation='twitter']")
            if person_twitter_id_node is not None:
                person_twitter_id = person_twitter_id_node.text
            else:
                person_twitter_id = ''

            person_youtube_id_node = one_person.find("./ContactInformation/Uri/[@annotation='youtube']")
            if person_youtube_id_node is not None:
                person_youtube_id = person_youtube_id_node.text
            else:
                person_youtube_id = ''

            person_googleplus_id_node = one_person.find("./ContactInformation/Uri/[@annotation='googleplus']")
            if person_googleplus_id_node is not None:
                person_googleplus_id = person_googleplus_id_node.text
            else:
                person_googleplus_id = ''

            ctcl_uuid = ""
            ctcl_uuid_node = one_person.find(
                "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']")
            if ctcl_uuid_node is not None:
                ctcl_uuid = one_person.find(
                    "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']/Value").text

            if first_line:
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='id',
                        batch_header_column_001='FullName',
                        batch_header_column_002='FirstName',
                        batch_header_column_003='MiddleName',
                        batch_header_column_004='LastName',
                        batch_header_column_005='PartyName',
                        batch_header_column_006='Email',
                        batch_header_column_007='Phone',
                        batch_header_column_008='uri::website',
                        batch_header_column_009='uri::facebook',
                        batch_header_column_010='uri::twitter',
                        batch_header_column_011='uri::youtube',
                        batch_header_column_012='uri::googleplus',
                        batch_header_column_013='other::ctcl-uuid',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='politician_batch_id',
                            batch_header_map_001='politician_full_name',
                            batch_header_map_002='politician_first_name',
                            batch_header_map_003='politician_middle_name',
                            batch_header_map_004='politician_last_name',
                            batch_header_map_005='politician_party_name',
                            batch_header_map_006='politician_email_address',
                            batch_header_map_007='politician_phone_number',
                            batch_header_map_008='politician_website_url',
                            batch_header_map_009='politician_facebook_id',
                            batch_header_map_010='politician_twitter_url',
                            batch_header_map_011='politician_youtube_id',
                            batch_header_map_012='politician_googleplus_id',
                            batch_header_map_013='politician_ctcl_uuid',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "POLITICIAN " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='POLITICIAN',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            # check for office_batch_id or electoral_district or name AND ctcl_uuid
            # if positive_value_exists(person_id) and ctcl_uuid is not None or person_full_name is not None or \
            #                 person_first_name is not None:
            if positive_value_exists(person_id) and positive_value_exists(ctcl_uuid) and \
                    (positive_value_exists(person_full_name) or positive_value_exists(person_first_name)):
                try:
                    batch_row = BatchRow.objects.create(
                        batch_header_id=batch_header_id,
                        batch_row_000=person_id,
                        batch_row_001=person_full_name,
                        batch_row_002=person_first_name,
                        batch_row_003=person_middle_name,
                        batch_row_004=person_last_name,
                        batch_row_005=person_party_name,
                        batch_row_006=person_email_id,
                        batch_row_007=person_phone_number,
                        batch_row_008=person_website_url,
                        batch_row_009=person_facebook_id,
                        batch_row_010=person_twitter_id,
                        batch_row_011=person_youtube_id,
                        batch_row_012=person_googleplus_id,
                        batch_row_013=ctcl_uuid,
                    )
                    number_of_batch_rows += 1
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    status += " EXCEPTION_BATCH_ROW"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_batch_rows': number_of_batch_rows,
        }
        return results

    def store_candidate_xml(self, batch_uri, google_civic_election_id, organization_we_vote_id, xml_root,
                            batch_set_id=0):
        """
        Retrieves Candidate data from CTCL xml file
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :param xml_root:
        :param batch_set_id
        :return:
        """
        # Process VIP Candidate data
        number_of_batch_rows = 0
        first_line = True
        success = True
        status = ''
        limit_for_testing = 0
        batch_header_id = 0

        # Call party api to get corresponding party name from party id
        party_details_list = retrieve_all_party_names_and_ids_api()

        # Look for Candidate and create the batch_header first. Candidate is the direct child node
        # of VipObject
        candidate_xml_node = xml_root.findall('Candidate')
        for one_candidate in candidate_xml_node:
            if positive_value_exists(limit_for_testing) and number_of_batch_rows >= limit_for_testing:
                break

            candidate_name_english = None
            candidate_ctcl_person_id = ""
            candidate_party_name = ""
            ctcl_uuid = ""

            # look for relevant child nodes under Candidate: id, BallotName, personId, PartyId, isTopTicket,
            # other::ctcl-uid
            candidate_id = one_candidate.attrib['id']

            candidate_selection_id = one_candidate.find("./BallotSelectionIds")

            candidate_name_node_english = one_candidate.find("./BallotName/Text/[@language='"+LANGUAGE_CODE_ENGLISH+"']")
            if candidate_name_node_english is not None:
                candidate_name_english = candidate_name_node_english.text

            candidate_ctcl_person_id_node = one_candidate.find('./PersonId')
            if candidate_ctcl_person_id_node is not None:
                candidate_ctcl_person_id = candidate_ctcl_person_id_node.text

            candidate_party_id_node = one_candidate.find('./PartyId')
            if candidate_party_id_node is not None:
                candidate_party_id = candidate_party_id_node.text
                # get party name from candidate_party_id
                if party_details_list is not None:
                    # party_details_dict =  [entry for entry in party_details_list]
                    for one_party in party_details_list:
                        # get the candidate party name matching candidate_party_id
                        if candidate_party_id == one_party.get('party_id_temp'):
                            candidate_party_name = one_party.get('party_name')
                            break
            else:
                candidate_party_name = ''

            candidate_is_top_ticket_node = one_candidate.find('IsTopTicket')
            if candidate_is_top_ticket_node is not None:
                candidate_is_top_ticket = candidate_is_top_ticket_node.text
            else:
                candidate_is_top_ticket = ''

            ctcl_uuid_node = one_candidate.find(
                "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']")
            if ctcl_uuid_node is not None:
                ctcl_uuid = one_candidate.find(
                    "./ExternalIdentifiers/ExternalIdentifier/[OtherType='ctcl-uuid']/Value").text

            if first_line:
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='id',
                        batch_header_column_001='PersonId',
                        batch_header_column_002='Name',
                        batch_header_column_003='PartyName',
                        batch_header_column_004='IsTopTicket',
                        batch_header_column_005='other::ctcl-uuid',
                        batch_header_column_006='other::CandidateSelectionId',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='candidate_batch_id',
                            batch_header_map_001='candidate_ctcl_person_id',
                            batch_header_map_002='candidate_name',
                            batch_header_map_003='candidate_party_name',
                            batch_header_map_004='candidate_is_top_ticket',
                            batch_header_map_005='candidate_ctcl_uuid',
                            batch_header_map_006='candidate_selection_id',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "CANDIDATE " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='CANDIDATE',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            # check for candidate_id or candidate_ctcl_person_id or name AND ctcl_uuid
            if positive_value_exists(candidate_id) and positive_value_exists(ctcl_uuid) and \
                    (positive_value_exists(candidate_ctcl_person_id) or positive_value_exists(candidate_name_english)):
                try:
                    batch_row = BatchRow.objects.create(
                        batch_header_id=batch_header_id,
                        batch_row_000=candidate_id,
                        batch_row_001=candidate_ctcl_person_id,
                        batch_row_002=candidate_name_english,
                        batch_row_003=candidate_party_name,
                        batch_row_004=candidate_is_top_ticket,
                        batch_row_005=ctcl_uuid,
                        batch_row_006=candidate_selection_id
                    )
                    number_of_batch_rows += 1
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    status += " EXCEPTION_BATCH_ROW"
                    handle_exception(e, logger=logger, exception_message=status)
                    success = False

                    break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_batch_rows': number_of_batch_rows,
        }
        return results

    def store_state_data_from_xml(self, batch_uri, google_civic_election_id, organization_we_vote_id, xml_root,
                                  batch_set_id=0):
        """
        Retrieves state data from CTCL xml file
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :param xml_root:
        :param batch_set_id
        :return:
        """
        # This state is not used right now. Parsing it for future reference
        # Process VIP State data
        number_of_batch_rows = 0
        first_line = True
        success = True
        status = ''
        limit_for_testing = 0
        batch_header_id = 0

        # Look for State and create the batch_header first. State is the direct child node of VipObject
        # TODO Will this be a single node object or will there be multiple state nodes in a CTCL XML?
        state_xml_node = xml_root.findall('State')
        for one_state in state_xml_node:
            state_name = None
            if positive_value_exists(limit_for_testing) and number_of_batch_rows >= limit_for_testing:
                break

            # look for relevant child nodes under State: id, ocd-id, Name
            state_id = one_state.attrib['id']

            state_name_node = one_state.find('./Name')
            if state_name_node is not None:
                state_name = state_name_node.text

            ocd_id_node = one_state.find("./ExternalIdentifiers/ExternalIdentifier/[Type='ocd-id']")
            if ocd_id_node is not None:
                ocd_id = one_state.find("./ExternalIdentifiers/ExternalIdentifier/[Type='ocd-id']/Value").text
            else:
                ocd_id = ''

            if first_line:
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='id',
                        batch_header_column_001='Name',
                        batch_header_column_002='other::ocd-id',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='state_id',
                            batch_header_map_001='state_name',
                            batch_header_map_002='ocd_id',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "STATE " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='STATE',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            # check for state_id or name AND ocd_id
            if positive_value_exists(state_id) and (positive_value_exists(state_name)):
                try:
                    batch_row = BatchRow.objects.create(
                        batch_header_id=batch_header_id,
                        batch_row_000=state_id,
                        batch_row_001=state_name,
                        batch_row_002=ocd_id,
                    )
                    number_of_batch_rows += 1
                except Exception as e:
                    # Stop trying to save rows -- break out of the for loop
                    status += " EXCEPTION_BATCH_ROW"
                    handle_exception(e, logger=logger, exception_message=status)
                    success = False

                    break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_batch_rows': number_of_batch_rows,
        }
        return results

    def store_election_metadata_from_xml(self, batch_uri, google_civic_election_id, organization_we_vote_id, xml_root,
                                         batch_set_id=0):
        """
        Retrieves election metadata from CTCL xml file
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :param xml_root:
        :param batch_set_id
        :return:
        """
        # This election metadata is not used right now. Parsing it for future reference
        # Process VIP Election metadata
        success = True
        status = ''
        batch_header_id = 0

        # Look for Election and create the batch_header first. Election is the direct child node of VipObject
        election_xml_node = xml_root.find('Election')
        election_date_str = None

        # look for relevant child nodes under Election: id, Date, StateId
        if not election_xml_node:
            results = {
                'success': success,
                'status': "STORE_ELECTION_METADATA_FROM_XML-ELECTION_NODE_NOT_FOUND",
                'batch_header_id': batch_header_id,
                'batch_saved': success,
            }
            return results

        election_id = election_xml_node.attrib['id']

        election_date_xml_node = election_xml_node.find('./Date')
        if election_date_xml_node is not None:
            election_date = election_date_xml_node.text

        state_id_node = election_xml_node.find("./StateId")
        if state_id_node is not None:
            state_id = state_id_node.text
        else:
            state_id = ''

        try:
            batch_header = BatchHeader.objects.create(
                batch_header_column_000='id',
                batch_header_column_001='Date',
                batch_header_column_002='StateId',
            )
            batch_header_id = batch_header.id

            if positive_value_exists(batch_header_id):
                # Save an initial BatchHeaderMap
                batch_header_map = BatchHeaderMap.objects.create(
                    batch_header_id=batch_header_id,
                    batch_header_map_000='election_id',
                    batch_header_map_001='election_date',
                    batch_header_map_002='state_id',
                )
                batch_header_map_id = batch_header_map.id
                status += " BATCH_HEADER_MAP_SAVED"

            if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                # Now save the BatchDescription
                batch_name = "ELECTION " + " batch_header_id: " + str(batch_header_id)
                batch_description_text = ""
                batch_description = BatchDescription.objects.create(
                    batch_header_id=batch_header_id,
                    batch_header_map_id=batch_header_map_id,
                    batch_name=batch_name,
                    batch_description_text=batch_description_text,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_batch='ELECTION',
                    organization_we_vote_id=organization_we_vote_id,
                    source_uri=batch_uri,
                    batch_set_id=batch_set_id,
                )
                status += " BATCH_DESCRIPTION_SAVED"
                success = True
        except Exception as e:
            # Stop trying to save rows -- break out of the for loop
            batch_header_id = 0
            status += " EXCEPTION_BATCH_HEADER"
            handle_exception(e, logger=logger, exception_message=status)

        # check for state_id or name AND ocd_id
        if positive_value_exists(election_id) and positive_value_exists(election_date) and \
                positive_value_exists(state_id):
            try:
                batch_row = BatchRow.objects.create(
                    batch_header_id=batch_header_id,
                    batch_row_000=election_id,
                    batch_row_001=election_date,
                    batch_row_002=state_id,
                )
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                status += " EXCEPTION_BATCH_ROW"
                handle_exception(e, logger=logger, exception_message=status)
                success = False

        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
        }
        return results

    def store_source_metadata_from_xml(self, batch_uri, google_civic_election_id, organization_we_vote_id, xml_root,
                                         batch_set_id=0):
        """
        Retrieves source metadata from CTCL xml file
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :param xml_root:
        :param batch_set_id
        :return:
        """
        # This source data is not used for now. Parsing it for future reference
        # Process VIP Source metadata
        success = False
        status = ''
        batch_header_id = 0

        # Look for Source and create the batch_header first. Election is the direct child node of VipObject
        source_xml_node = xml_root.find('Source')
        source_date_str = None

        if not source_xml_node:
            results = {
                'success': success,
                'status': "STORE_SOURCE_METADATA_FROM_XML-SOURCE_NODE_NOT_FOUND",
                'batch_header_id': batch_header_id,
                'batch_saved': success,
            }
            return results

        # look for relevant child nodes under Source: id, DateTime, Name, OrganizationUri, VipId
        source_id = source_xml_node.attrib['id']

        source_datetime_xml_node = source_xml_node.find('./DateTime')
        if source_datetime_xml_node is not None:
            source_datetime = source_datetime_xml_node.text

        source_name_node = source_xml_node.find("./Name")
        if source_name_node is not None:
            source_name = source_xml_node.text
        else:
            source_name = ''

        organization_uri_node = source_xml_node.find("./OrganizationUri")
        if organization_uri_node is not None:
            organization_uri = source_xml_node.text

        vip_id_node = source_xml_node.find("./VipId")
        if vip_id_node is not None:
            vip_id = source_xml_node.text
        else:
            vip_id = ''

        try:
            batch_header = BatchHeader.objects.create(
                batch_header_column_000='id',
                batch_header_column_001='DateTime',
                batch_header_column_002='Name',
                batch_header_column_003='OrganizationUri',
                batch_header_column_004='VipId',
            )
            batch_header_id = batch_header.id

            if positive_value_exists(batch_header_id):
                # Save an initial BatchHeaderMap
                batch_header_map = BatchHeaderMap.objects.create(
                    batch_header_id=batch_header_id,
                    batch_header_map_000='source_id',
                    batch_header_map_001='source_datetime',
                    batch_header_map_002='source_name',
                    batch_header_map_003='organization_uri',
                    batch_header_map_004='vip_id'
                )
                batch_header_map_id = batch_header_map.id
                status += " BATCH_HEADER_MAP_SAVED"

            if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                # Now save the BatchDescription
                batch_name = "SOURCE " + " batch_header_id: " + str(batch_header_id)
                batch_description_text = ""
                batch_description = BatchDescription.objects.create(
                    batch_header_id=batch_header_id,
                    batch_header_map_id=batch_header_map_id,
                    batch_name=batch_name,
                    batch_description_text=batch_description_text,
                    google_civic_election_id=google_civic_election_id,
                    kind_of_batch='SOURCE',
                    organization_we_vote_id=organization_we_vote_id,
                    source_uri=batch_uri,
                    batch_set_id=batch_set_id,
                )
                status += " BATCH_DESCRIPTION_SAVED"
                success = True
        except Exception as e:
            # Stop trying to save rows -- break out of the for loop
            batch_header_id = 0
            status += " EXCEPTION_BATCH_HEADER"
            handle_exception(e, logger=logger, exception_message=status)

        # check for state_id or name AND ocd_id
        if positive_value_exists(source_id) and positive_value_exists(source_datetime) and \
                positive_value_exists(source_name) and positive_value_exists(organization_uri):
            try:
                batch_row = BatchRow.objects.create(
                    batch_header_id=batch_header_id,
                    batch_row_000=source_id,
                    batch_row_001=source_datetime,
                    batch_row_002=source_name,
                    batch_row_003=organization_uri,
                    batch_row_004=vip_id
                )
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                status += " EXCEPTION_BATCH_ROW"
                handle_exception(e, logger=logger, exception_message=status)
                success = False

        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
        }
        return results

    def create_batch_set_vip_xml(self, batch_file, batch_uri, google_civic_election_id, organization_we_vote_id):
        """
        Retrieves CTCL Batch Set data from an xml file - Measure, Office, Candidate, Politician
        :param batch_file:
        :param batch_uri:
        :param google_civic_election_id:
        :param organization_we_vote_id:
        :return:
        """
        import_date = date.today()

        # Retrieve from XML
        if batch_file:
            xml_tree = ElementTree.parse(batch_file)
            batch_set_name = batch_file.name + " - " + str(import_date)

        else:
            request = urllib.request.urlopen(batch_uri)
            # xml_data = request.read()
            # xml_data = xmltodict.parse(xml_data)
            # # xml_data_list_json = list(xml_data)
            # structured_json = json.dumps(xml_data)

            xml_tree = ElementTree.parse(request)
            request.close()

            # set batch_set_name as file_name
            batch_set_name_list = batch_uri.split('/')
            batch_set_name = batch_set_name_list[len(batch_set_name_list) - 1] + " - " + str(import_date)

        xml_root = xml_tree.getroot()

        status = ''
        success = False
        number_of_batch_rows = 0
        batch_set_id = 0
        continue_batch_set_processing = True  # Set to False if we run into a problem that requires we stop processing

        if xml_root:
            # create batch_set object
            try:
                batch_set = BatchSet.objects.create(batch_set_description_text="", batch_set_name=batch_set_name,
                                                    batch_set_source=BATCH_SET_SOURCE_CTCL,
                                                    google_civic_election_id=google_civic_election_id,
                                                    source_uri=batch_uri, import_date=import_date)
                batch_set_id = batch_set.id
                if positive_value_exists(batch_set_id):
                    status += " BATCH_SET_SAVED"
                    success = True
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                continue_batch_set_processing = False
                batch_set_id = 0
                status += " EXCEPTION_BATCH_SET "
                handle_exception(e, logger=logger, exception_message=status)

            # import Electoral District
            skip_electoral_district = False  # We can set this to True during development to save time
            if continue_batch_set_processing and not skip_electoral_district:
                electoral_district_list_found = False
                electoral_district_item_list = xml_root.findall('ElectoralDistrict')
                if not len(electoral_district_item_list):
                    continue_batch_set_processing = False
                else:
                    results = electoral_district_import_from_xml_data(electoral_district_item_list)
                    if results['success']:
                        status += "CREATE_BATCH_SET_ELECTORAL_DISTRICT_IMPORTED "
                        number_of_batch_rows += results['saved']
                        # TODO check this whether it should be only saved or updated Electoral districts
                        number_of_batch_rows += results['updated']
                        electoral_district_list_found = True
                    else:
                        continue_batch_set_processing = False
                        status += results['status']
                        status += " CREATE_BATCH_SET_ELECTORAL_DISTRICT_ERRORS "

            # import Party
            skip_party = False  # We can set this to True during development to save time
            if continue_batch_set_processing and not skip_party:
                party_list_found = False
                party_item_list = xml_root.findall('Party')
                if not len(party_item_list):
                    continue_batch_set_processing = False
                    status += " CREATE_BATCH_SET-PARTY_IMPORT_ERRORS-NO_party_item_list "
                else:
                    results = party_import_from_xml_data(party_item_list)
                    if results['success']:
                        status += "CREATE_BATCH_SET_PARTY_IMPORTED"
                        number_of_batch_rows += results['saved']
                        number_of_batch_rows += results['updated']
                        # TODO check this whether it should be only saved or updated Electoral districts
                        party_list_found = True
                        # A given data source may not always have electoral district and/or party data,
                        # but the referenced electoral district id or party id might be already present
                        # in the master database tables, hence commenting out below code
                        # if not electoral_district_list_found or not party_list_found:
                        #     results = {
                        #         'success': False,
                        #         'status': status,
                        #         'batch_header_id': 0,
                        #         'batch_saved': False,
                        #         'number_of_batch_rows': 0,
                        #     }
                        #     return results
                    else:
                        continue_batch_set_processing = False
                        status += results['status']
                        status += " CREATE_BATCH_SET-PARTY_IMPORT_ERRORS "

            # look for different data sets in the XML - ElectedOffice, ContestOffice, Candidate, Politician, Measure

            # Elected Office
            skip_elected_office = False  # We can set this to True during development to save time
            if continue_batch_set_processing and not skip_elected_office:
                results = self.store_elected_office_xml(batch_uri, google_civic_election_id, organization_we_vote_id,
                                                        xml_root, batch_set_id)
                if results['success']:
                    # Elected Office data found
                    status += 'CREATE_BATCH_SET_ELECTED_OFFICE_DATA_FOUND'
                    number_of_batch_rows += results['number_of_batch_rows']
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-PARTY_IMPORT_ERRORS "

            # Candidate-to-office-mappings
            skip_candidate_mapping = False  # We can set this to True during development to save time
            if continue_batch_set_processing and not skip_candidate_mapping:
                results = create_candidate_selection_rows(xml_root, batch_set_id)
                if results['success']:
                    # Elected Office data found
                    status += 'CREATE_BATCH_SET_CANDIDATE_SELECTION_DATA_FOUND'
                    number_of_batch_rows += results['number_of_batch_rows']
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-CANDIDATE_SELECTION_ERRORS "

            # ContestOffice entries
            skip_contest_office = False  # We can set this to True during development to save time
            if continue_batch_set_processing and not skip_contest_office:
                results = self.store_contest_office_xml(
                    batch_uri, google_civic_election_id, organization_we_vote_id, xml_root, batch_set_id)
                if results['success']:
                    # Contest Office data found
                    status += 'CREATE_BATCH_SET_CONTEST_OFFICE_DATA_FOUND'
                    number_of_batch_rows += results['number_of_batch_rows']
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-CONTEST_OFFICE_ERRORS "

            # Politician entries
            skip_politician = False  # We can set this to True during development to save time
            if continue_batch_set_processing and not skip_politician:
                results = self.store_politician_xml(
                    batch_uri, google_civic_election_id, organization_we_vote_id, xml_root, batch_set_id)
                if results['success']:
                    status += 'CREATE_BATCH_SET_POLITICIAN_DATA_FOUND'
                    number_of_batch_rows += results['number_of_batch_rows']
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-POLITICIAN_ERRORS "

            # Candidate entries
            skip_candidate = False  # We can set this to True during development to save time
            if continue_batch_set_processing and not skip_candidate:
                results = self.store_candidate_xml(
                    batch_uri, google_civic_election_id, organization_we_vote_id, xml_root, batch_set_id)
                if results['success']:
                    status += 'CREATE_BATCH_SET_CANDIDATE_DATA_FOUND'
                    number_of_batch_rows += results['number_of_batch_rows']
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-CANDIDATE_ERRORS "

            # Measure entries
            skip_measure = False  # We can set this to True during development to save time
            if continue_batch_set_processing and not skip_measure:
                results = self.store_measure_xml(
                    batch_uri, google_civic_election_id, organization_we_vote_id, xml_root, batch_set_id)
                if results['success']:
                    status += 'CREATE_BATCH_SET_MEASURE_DATA_FOUND'
                    number_of_batch_rows += results['number_of_batch_rows']
                    success = True
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-MEASURE_ERRORS "

            # State data entries
            if continue_batch_set_processing:
                results = self.store_state_data_from_xml(batch_uri, google_civic_election_id, organization_we_vote_id,
                                                         xml_root, batch_set_id)
                if results['success']:
                    status += 'CREATE_BATCH_SET_STATE_DATA_FOUND'
                    number_of_batch_rows += results['number_of_batch_rows']
                    success = True
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-STATE_DATA_ERRORS "

            # Election metadata entries
            if continue_batch_set_processing:
                results = self.store_election_metadata_from_xml(
                    batch_uri, google_civic_election_id, organization_we_vote_id, xml_root, batch_set_id)
                if results['success']:
                    status += ' CREATE_BATCH_SET_ELECTION_METADATA_FOUND '
                    number_of_batch_rows += 1
                    success = True
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-ELECTION_METADATA_ERRORS "

            # Source metadata entries
            if continue_batch_set_processing:
                results = self.store_source_metadata_from_xml(
                    batch_uri, google_civic_election_id, organization_we_vote_id, xml_root, batch_set_id)
                if results['success']:
                    status += ' CREATE_BATCH_SET_SOURCE_METADATA_FOUND '
                    number_of_batch_rows += 1
                    success = True
                else:
                    continue_batch_set_processing = False
                    status += results['status']
                    status += " CREATE_BATCH_SET-SOURCE_METADATA_ERRORS "

        results = {
            'success':                  success,
            'status':                   status,
            'batch_set_id':             batch_set_id,
            'batch_saved':              success,
            'number_of_batch_rows':     number_of_batch_rows,
        }
        return results

    def count_number_of_batch_action_rows(self, header_id, kind_of_batch):
        """
            Return count of batch rows for a given header id
        :param header_id: 
        :return: 
        """
        number_of_batch_action_rows = 0
        if positive_value_exists(header_id):
            if kind_of_batch == MEASURE:
                number_of_batch_action_rows = BatchRowActionMeasure.objects.filter(batch_header_id=header_id).count()
            elif kind_of_batch == ELECTED_OFFICE:
                number_of_batch_action_rows = BatchRowActionElectedOffice.objects.filter(batch_header_id=header_id).\
                    count()
            elif kind_of_batch == CONTEST_OFFICE:
                number_of_batch_action_rows = BatchRowActionContestOffice.objects.filter(batch_header_id=header_id).\
                    count()
            elif kind_of_batch == CANDIDATE:
                number_of_batch_action_rows = BatchRowActionCandidate.objects.filter(batch_header_id=header_id).count()
            elif kind_of_batch == POLITICIAN:
                number_of_batch_action_rows = BatchRowActionPolitician.objects.filter(batch_header_id=header_id).count()
            else:
                number_of_batch_action_rows = 0
        return number_of_batch_action_rows

    def fetch_batch_header_translation_suggestion(self, kind_of_batch, alternate_header_value):
        """
        We are looking at one header value from a file imported by an admin or volunteer. We want to see if
        there are any suggestions for headers already recognized by We Vote.
        :param kind_of_batch:
        :param alternate_header_value:
        :return:
        """
        results = self.retrieve_batch_header_translation_suggestion(kind_of_batch, alternate_header_value)
        if results['batch_header_translation_suggestion_found']:
            batch_header_translation_suggestion = results['batch_header_translation_suggestion']
            return batch_header_translation_suggestion.header_value_recognized_by_we_vote
        return ""

    # TODO This hasn't been built
    def fetch_batch_row_translation_map(self, kind_of_batch, batch_row_name, incoming_alternate_row_value):
        results = self.retrieve_batch_row_translation_map(kind_of_batch, incoming_alternate_row_value)
        if results['batch_header_translation_suggestion_found']:
            batch_header_translation_suggestion = results['batch_header_translation_suggestion']
            return batch_header_translation_suggestion.header_value_recognized_by_we_vote
        return ""

    def fetch_elected_office_name_from_elected_office_ctcl_id(self, elected_office_ctcl_id, batch_set_id):
        """
        Take in elected_office_ctcl_id and batch_set_id, look up BatchRow and return elected_office_name
        :param elected_office_ctcl_id: 
        :param batch_set_id:
        :return:
        """
        elected_office_name = ''
        batch_header_id = 0
        # From batch_description, get the header_id using batch_set_id
        # batch_header_id = get_batch_header_id_from_batch_description(batch_set_id, ELECTED_OFFICE)
        try:
            if positive_value_exists(batch_set_id):
                batch_description_on_stage = BatchDescription.objects.get(batch_set_id=batch_set_id,
                                                                          kind_of_batch=ELECTED_OFFICE)
                if batch_description_on_stage:
                    batch_header_id = batch_description_on_stage.batch_header_id
        except BatchDescription.DoesNotExist:
                elected_office_name = ''
                pass

        # Lookup BatchRow with given header_id and elected_office_ctcl_id. But before doing that, we need to get batch
        # row column name that matches 'elected_office_batch_id'
        try:
            batch_manager = BatchManager()
            if positive_value_exists(batch_header_id) and elected_office_ctcl_id:
                batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)

                # Get the column name in BatchRow that stores elected_office_batch_id - id taken from batch_header_map
                # eg: batch_row_000 -> elected_office_batch_id
                elected_office_id_column_name = batch_manager.retrieve_column_name_from_batch_row(
                    "elected_office_batch_id", batch_header_map)

                # we found batch row column name corresponding to elected_office_batch_id, now look up batch_row table
                # with given batch_header_id and elected_office_batch_id (batch_row_00)
                batch_row_on_stage = BatchRow.objects.get(batch_header_id=batch_header_id,
                                                          **{ elected_office_id_column_name: elected_office_ctcl_id})
                # we know the batch row, next retrieve value for elected_office_name eg: off1 -> NC State Senator
                elected_office_name = batch_manager.retrieve_value_from_batch_row('elected_office_name',
                                                                                  batch_header_map, batch_row_on_stage)

        except BatchRow.DoesNotExist:
            elected_office_name = ''

        return elected_office_name

    def fetch_state_code_from_person_id_in_candidate(self, person_id, batch_set_id):
        """
        Take in person_id, batch_set_id, look up BatchRowActionCandidate and return state_code
        :param person_id: 
        :param batch_set_id:
        :return: 
        """
        state_code = ''
        batch_header_id = 0
        # From batch_description, get the header_id using batch_set_id
        # batch_header_id = get_batch_header_id_from_batch_description(batch_set_id, CANDIDATE)
        try:
            if positive_value_exists(batch_set_id):
                batch_description_on_stage = BatchDescription.objects.get(batch_set_id=batch_set_id,
                                                                          kind_of_batch=CANDIDATE)
                if batch_description_on_stage:
                    batch_header_id = batch_description_on_stage.batch_header_id
        except BatchDescription.DoesNotExist:
            pass

        try:
            if positive_value_exists(batch_header_id) and person_id is not None:
                batchrowaction_candidate = BatchRowActionCandidate.objects.get(batch_header_id=batch_header_id,
                                                                               candidate_ctcl_person_id=person_id)

                if batchrowaction_candidate is not None:
                    state_code = batchrowaction_candidate.state_code
                    if state_code is None:
                        return ''

        except BatchRowActionCandidate.DoesNotExist:
            state_code = ''

        return state_code

    def retrieve_election_details_from_election_day_or_state_code(self, election_day='', state_code=''):
        """
        Retrieve election_name and google_civic_election_id from election_day and/or state_code
        :param election_day: 
        :param state_code: 
        :return: 
        """

        success = False
        election_name = ''
        google_civic_election_id = ''

        # election lookup using state & election day, and fetch google_civic_election_id
        election_manager = ElectionManager()
        election_results = election_manager.retrieve_elections_by_election_date(election_day)
        if election_results['success']:
            election_list = election_results['election_list']
            if len(election_list) == 1:
                [election] = election_list
                election_name = election.election_name
                google_civic_election_id = election.google_civic_election_id
                success = True
            else:
                # use state_code & election_date for lookup. If multiple entries found, do not set
                # google_civic_election_id
                election_results = election_manager.retrieve_elections_by_state_and_election_date(state_code,
                                                                                                  election_day)
                if election_results['success']:
                    election_list = election_results['election_list']
                    if len(election_list) == 1:
                        [election] = election_list
                        election_name = election.election_name
                        google_civic_election_id = election.google_civic_election_id
                        success = True

        results = {
            'success': success,
            'election_name': election_name,
            'google_civic_election_id': google_civic_election_id,
        }

        return results

    def create_batch_set_organization_endorsements(self, organization):
        """
        Create batch set for organization endorsements
        :param organization: 
        :return: 
        """
        batch_set_id = 0
        batch_saved = False
        status = ''
        success = False
        number_of_batch_rows = 0
        batch_set_id = 0
        election_name = ''
        structured_organization_endorsement_json = ''
        google_civic_election_id = 0

        organization_endorsements_api_url = organization.organization_endorsements_api_url
        if not organization_endorsements_api_url:
            results = {
                'success': False,
                'status':       "CREATE_BATCH_SET_ORGANIZATION_ENDORSEMENTS-INVALID_URL",
                'batch_saved': batch_saved,
                'number_of_batch_rows': 0,
                'election_name': election_name,
                'batch_set_id': batch_set_id,
                'google_civic_election_id': google_civic_election_id,
            }

        import_date = date.today()
        try:
            endorsement_req = urllib.request.Request(organization_endorsements_api_url,
                                                     headers={'User-Agent': 'Mozilla/5.0'})
            endorsement_url = urlopen(endorsement_req)
            # endorsement_url.close()
            # structured_organization_endorsement_json = json.loads(endorsement_url)
            organization_endorsement_url = endorsement_url.read()
            organization_endorsement_json = organization_endorsement_url.decode('utf-8')
            structured_organization_endorsement_json = json.loads(organization_endorsement_json)
            batch_set_name_url = urlquote(organization_endorsements_api_url)
        except Exception as e:
            batch_set_id = 0
            status += " EXCEPTION_BATCH_SET "
            handle_exception(e, logger=logger, exception_message=status)

        if not structured_organization_endorsement_json:
            results = {
                'success': False,
                'status': "CREATE_BATCH_SET_ORGANIZATION_ENDORSEMENT_FAILED",
                'batch_saved': batch_saved,
                'number_of_batch_rows': 0,
                'election_name': election_name,
                'batch_set_id': batch_set_id,
                'google_civic_election_id': google_civic_election_id,
            }
            return results

        # set batch_set_name as file_name
        batch_set_name_list = batch_set_name_url.split('/')
        batch_set_name = organization.organization_name + " - " + batch_set_name_list[len(batch_set_name_list) - 1] + \
            " - " + str(import_date)

        # create batch_set object
        try:
            batch_set = BatchSet.objects.create(batch_set_description_text="", batch_set_name=batch_set_name,
                                                batch_set_source=BATCH_SET_SOURCE_IMPORT_EXPORT_ENDORSEMENTS,
                                                source_uri=batch_set_name_url, import_date=import_date)
            batch_set_id = batch_set.id
            if positive_value_exists(batch_set_id):
                status += " BATCH_SET_SAVED"
                success = True
        except Exception as e:
            # Stop trying to save rows -- break out of the for loop
            batch_set_id = 0
            status += " EXCEPTION_BATCH_SET "
            handle_exception(e, logger=logger, exception_message=status)

        # import metadata like organization name, url, endorsement url, twitter url, org image url, email
        # organization_name = structured_organization_endorsement_json['organization_name']
        # organization_url = structured_organization_endorsement_json['organization_url']
        # organization_endorsements_url = structured_organization_endorsement_json['organization_endorsements_url']
        # organization_twitter_url = structured_organization_endorsement_json['organization_twitter_url']
        # organization_image_url = structured_organization_endorsement_json['organization_image_url']
        # organization_image_url_https = structured_organization_endorsement_json['organization_image_url_https']
        # organization_email = structured_organization_endorsement_json['organization_email']
        candidate_positions_list = structured_organization_endorsement_json['candidate_positions']
        # measure_positions_list = structured_organization_endorsement_json['measure_positions']
        organization_we_vote_id = organization.we_vote_id
        organization_twitter_handle = organization.organization_twitter_handle

        # import Offices from json
        results = self.import_offices_from_endorsement_json(batch_set_name_url, batch_set_id, organization_we_vote_id,
                                                            candidate_positions_list)
        if results['success']:
            status += 'CREATE_BATCH_SET_OFFICE_DATA_IMPORTED'
            number_of_batch_rows += results['number_of_offices']
        else:
            continue_batch_set_processing = False
            status += results['status']
            status += " CREATE_BATCH_SET-OFFICE_ERRORS "

        # import Candidates from json
        results = self.import_candidates_from_endorsement_json(batch_set_name_url, batch_set_id,
                                                               organization_we_vote_id, candidate_positions_list)
        if results['success']:
            status += 'CREATE_BATCH_SET_CANDIDATE_DATA_IMPORTED'
            number_of_batch_rows += results['number_of_candidates']
        else:
            continue_batch_set_processing = False
            status += results['status']
            status += " CREATE_BATCH_SET-CANDIDATE_ERRORS "

        results = self.import_candidate_positions_from_endorsement_json(batch_set_name_url, batch_set_id,
                                                                        organization_we_vote_id,
                                                                        organization_twitter_handle,
                                                                        candidate_positions_list)
        if results['success']:
            success = True
            status += "CREATE_BATCH_SET_CANDIDATE_POSITIONS_IMPORTED "
            number_of_batch_rows += results['number_of_candidate_positions']
            # TODO check this whether it should be only saved or updated Candidate positionss
            # number_of_batch_rows += results['updated']
            batch_saved = True
            election_name = results['election_name']
            google_civic_election_id = results['google_civic_election_id']
        else:
            # continue_batch_set_processing = False
            status += results['status']
            status += " CREATE_BATCH_SET_CANDIDATE_POSITIONS_ERRORS "

        results = {
            'success': success,
            'status': status,
            'number_of_batch_rows': number_of_batch_rows,
            'batch_saved': batch_saved,
            'election_name': election_name,
            'batch_set_id': batch_set_id,
            'google_civic_election_id': google_civic_election_id,
        }
        return results

    def import_offices_from_endorsement_json(self, batch_uri='', batch_set_id='', organization_we_vote_id='',
                                             candidate_positions_list=''):
        """
        Import Offices from organization endorsements json file
        :param batch_uri: 
        :param batch_set_id: 
        :param organization_we_vote_id:
        :param candidate_positions_list: 
        :return: 
        """

        status = ''
        success = False
        number_of_offices = 0
        first_line = True
        election_day = ''
        google_civic_election_id = 0

        if not candidate_positions_list:
            results = {
                'success': False,
                'status': "IMPORT_OFFICES_FROM_ENDORSEMENT_JSON-INVALID_DATA",
                'number_of_offices': 0,
                'election_day': '',
                'google_civic_election_id': google_civic_election_id,
            }
            return results

        # else:
        for one_entry in candidate_positions_list:
            # read office details for each candidate position
            office_name = one_entry['office_name']
            state_code = one_entry['state_code']
            candidate_name = one_entry['name']
            election_day = one_entry['election_day']
            google_civic_election_id = one_entry['google_civic_election_id']
            party = one_entry['party']
            office_ocd_division_id = one_entry['office_ocd_division_id']

            if first_line:
                # create batch_header and batch_header_map for candidate_positions
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='office_name',
                        batch_header_column_001='state_code',
                        batch_header_column_002='candidate_name',
                        batch_header_column_003='election_day',
                        batch_header_column_004='google_civic_election_id',
                        batch_header_column_005='party',
                        batch_header_column_006='office_ocd_division_id',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='contest_office_name',
                            batch_header_map_001='state_code',
                            batch_header_map_002='candidate_name',
                            batch_header_map_003='election_day',
                            batch_header_map_004='google_civic_election_id',
                            batch_header_map_005='party',
                            batch_header_map_006='office_ocd_division_id',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "ENDORSEMENTS_JSON_OFFICES " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='CONTEST_OFFICE',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            try:
                batch_row = BatchRow.objects.create(
                    batch_header_id=batch_header_id,
                    batch_row_000=office_name,
                    batch_row_001=state_code,
                    batch_row_002=candidate_name,
                    batch_row_003=election_day,
                    batch_row_004=google_civic_election_id,
                    batch_row_005=party,
                    batch_row_006=office_ocd_division_id,
                )
                number_of_offices += 1
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                status += " EXCEPTION_BATCH_ROW"
                handle_exception(e, logger=logger, exception_message=status)
                break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_offices': number_of_offices,
            'election_day': election_day,
            'google_civic_election_id': google_civic_election_id,
        }

        return results

    def import_candidates_from_endorsement_json(self, batch_uri='', batch_set_id='', organization_we_vote_id='',
                                             candidate_positions_list=''):
        """
        Import Candidates from organization endorsements json file
        :param batch_uri: 
        :param batch_set_id: 
        :param organization_we_vote_id:
        :param candidate_positions_list: 
        :return: 
        """

        status = ''
        success = False
        number_of_candidates = 0
        first_line = True
        election_day = ''
        google_civic_election_id = 0

        if not candidate_positions_list:
            results = {
                'success': False,
                'status': "IMPORT_CANDIDATES_FROM_ENDORSEMENT_JSON-INVALID_DATA",
                'number_of_candidates': 0,
                'election_day': election_day,
                'google_civic_election_id': google_civic_election_id,
            }
            return results

        # else:
        for one_entry in candidate_positions_list:
            # read position details for each candidate
            candidate_name = one_entry['name']
            candidate_facebook_url = one_entry['facebook_url']
            candidate_twitter_url = one_entry['twitter_url']
            candidate_website_url = one_entry['website_url']
            party = one_entry['party']
            contest_office_name = one_entry['office_name']
            candidate_profile_image_url_https = one_entry['profile_image_url_https']
            state_code = one_entry['state_code']
            election_day = one_entry['election_day']
            google_civic_election_id = one_entry['google_civic_election_id']
            candidate_ocd_division_id = one_entry['candidate_ocd_division_id']

            if first_line:
                # create batch_header and batch_header_map for candidate_positions
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='name',
                        batch_header_column_001='twitter_url',
                        batch_header_column_002='facebook_url',
                        batch_header_column_003='more_info_url',
                        batch_header_column_004='state_code',
                        batch_header_column_005='office_name',
                        batch_header_column_006='profile_image_url_https',
                        batch_header_column_007='party',
                        batch_header_column_008='election_day',
                        batch_header_column_009='google_civic_election_id',
                        batch_header_column_010='candidate_ocd_division_id',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='candidate_name',
                            batch_header_map_001='candidate_twitter_handle',
                            batch_header_map_002='facebook_url',
                            batch_header_map_003='candidate_url',
                            batch_header_map_004='state_code',
                            batch_header_map_005='contest_office_name',
                            batch_header_map_006='candidate_profile_image_url',
                            batch_header_map_007='candidate_party_name',
                            batch_header_map_008='election_day',
                            batch_header_map_009='google_civic_election_id',
                            batch_header_map_010='candidate_ocd_division_id',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "ENDORSEMENTS_JSON_CANDIDATES " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='CANDIDATE',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            try:
                batch_row = BatchRow.objects.create(
                    batch_header_id=batch_header_id,
                    batch_row_000=candidate_name,
                    batch_row_001=candidate_twitter_url,
                    batch_row_002=candidate_facebook_url,
                    batch_row_003=candidate_website_url,
                    batch_row_004=state_code,
                    batch_row_005=contest_office_name,
                    batch_row_006=candidate_profile_image_url_https,
                    batch_row_007=party,
                    batch_row_008=election_day,
                    batch_row_009=google_civic_election_id,
                    batch_row_010=candidate_ocd_division_id,
                )
                number_of_candidates += 1
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                status += " EXCEPTION_BATCH_ROW"
                handle_exception(e, logger=logger, exception_message=status)
                break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_candidates': number_of_candidates,
            'election_day': election_day,
            'google_civic_election_id': google_civic_election_id,
        }

        return results

    def import_candidate_positions_from_endorsement_json(self, batch_uri, batch_set_id, organization_we_vote_id,
                                                         organization_twitter_handle, candidate_positions_list):
        """
        Import candidate positions from organization endorsements json file
        :param batch_uri: 
        :param batch_set_id: 
        :param organization_we_vote_id: 
        :param organization_twitter_handle: 
        :param candidate_positions_list: 
        :return: 
        """

        status = ''
        success = False
        number_of_candidate_positions = 0
        first_line = True
        election_name = ''
        google_civic_election_id = 0

        if not candidate_positions_list:
            results = {
                'success': False,
                'status': "IMPORT_CANDIDATE_POSITIONS_FROM_ENDORSEMENT_JSON-INVALID_DATA",
                'candidate_positions_saved': False,
                'number_of_candidate_positions': 0,
                'election_name': election_name,
                'google_civic_election_id': google_civic_election_id,
            }
            return results

        # else:
        for one_entry in candidate_positions_list:
            # read position details for each candidate
            candidate_name = one_entry['name']
            stance = one_entry['stance']
            percent_rating = one_entry['percent_rating']
            grade_rating = one_entry['grade_rating']
            candidate_twitter_url = one_entry['twitter_url']
            candidate_website_url = one_entry['website_url']
            candidate_position_description = one_entry['position_description']
            office_name = one_entry['office_name']
            state_code = one_entry['state_code']
            election_day = one_entry['election_day']
            google_civic_election_id = one_entry['google_civic_election_id']
            organization_position_url = one_entry['organization_position_url']

            if first_line:
                # create batch_header and batch_header_map for candidate_positions
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='name',
                        batch_header_column_001='stance',
                        batch_header_column_002='percent_rating',
                        batch_header_column_003='grade_rating',
                        batch_header_column_004='organization_twitter_handle',
                        batch_header_column_005='twitter_url',
                        batch_header_column_006='more_info_url',
                        batch_header_column_007='position_description',
                        batch_header_column_008='office_name',
                        batch_header_column_009='state_code',
                        batch_header_column_010='election_day',
                        batch_header_column_011='google_civic_election_id',
                        batch_header_column_012='organization_position_url',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='candidate_name',
                            batch_header_map_001='stance',
                            batch_header_map_002='percent_rating',
                            batch_header_map_003='grade_rating',
                            batch_header_map_004='organization_twitter_handle',
                            batch_header_map_005='candidate_twitter_handle',
                            batch_header_map_006='more_info_url',
                            batch_header_map_007='statement_text',
                            batch_header_map_008='contest_office_name',
                            batch_header_map_009='state_code',
                            batch_header_map_010='election_day',
                            batch_header_map_011='google_civic_election_id',
                            batch_header_map_012='organization_position_url',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "ENDORSEMENTS_JSON_CANDIDATE_POSITIONS " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            google_civic_election_id=google_civic_election_id,
                            kind_of_batch='POSITION',
                            organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            try:
                batch_row = BatchRow.objects.create(
                    batch_header_id=batch_header_id,
                    batch_row_000=candidate_name,
                    batch_row_001=stance,
                    batch_row_002=percent_rating,
                    batch_row_003=grade_rating,
                    batch_row_004=organization_twitter_handle,
                    batch_row_005=candidate_twitter_url,
                    batch_row_006=candidate_website_url,
                    batch_row_007=candidate_position_description,
                    batch_row_008=office_name,
                    batch_row_009=state_code,
                    batch_row_010=election_day,
                    batch_row_011=google_civic_election_id,
                    batch_row_012=organization_position_url,
                )
                number_of_candidate_positions += 1
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                status += " EXCEPTION_BATCH_ROW"
                handle_exception(e, logger=logger, exception_message=status)
                break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_candidate_positions': number_of_candidate_positions,
            'election_name': election_name,
            'google_civic_election_id': google_civic_election_id,
        }

        return results

    def import_measure_positions_from_endorsement_json(self, batch_uri, batch_set_id, measure_positions_list):
        """
        Import measure positions from organization endorsements json file        
        :param batch_uri: 
        :param batch_set_id: 
        :param measure_positions_list: 
        :return: 
        """

        status = ''
        success = False
        number_of_measure_positions = 0
        first_line = True
        election_name = ''
        google_civic_election_id = 0

        if not measure_positions_list:
            results = {
                'success': False,
                'status': "IMPORT_MEASURE_POSITIONS_FROM_ENDORSEMENT_JSON-INVALID_DATA",
                'measure_positions_saved': False,
                'number_of_measure_positions': 0,
                'election_name': election_name,
                'google_civic_election_id': google_civic_election_id,
            }
            return results

        # else:
        for one_entry in measure_positions_list:
            # read position details for each candidate
            measure_name = one_entry['name']
            stance = one_entry['stance']
            measure_ocd_division_id = one_entry['measure_ocd_division_id']
            organization_position_url = one_entry['organization_position_url']
            measure_id = one_entry['id']
            twitter_url = one_entry['twitter_url']
            facebook_url = one_entry['facebook_url']
            website_url = one_entry['website_url']
            image_url = one_entry['image_url']
            image_url_https = one_entry['image_url_https']
            measure_position_description = one_entry['position_description']
            state_code = one_entry['state_code']
            election_day = one_entry['election_day']
            google_civic_election_id = one_entry['google_civic_election_id']

            if first_line:
                # create batch_header and batch_header_map for candidate_positions
                first_line = False
                try:
                    batch_header = BatchHeader.objects.create(
                        batch_header_column_000='id',
                        batch_header_column_001='name',
                        batch_header_column_002='stance',
                        batch_header_column_003='measure_ocd_division_id',
                        batch_header_column_004='organization_position_url',
                        batch_header_column_005='twitter_url',
                        batch_header_column_006='facebook_url',
                        batch_header_column_007='website_url',
                        batch_header_column_008='image_url',
                        batch_header_column_009='image_url_https',
                        batch_header_column_010='position_description',
                        batch_header_column_011='state_code',
                        batch_header_column_012='election_day',
                        batch_header_column_013='google_civic_election_id',
                    )
                    batch_header_id = batch_header.id

                    if positive_value_exists(batch_header_id):
                        # Save an initial BatchHeaderMap
                        batch_header_map = BatchHeaderMap.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_000='measure_id',
                            batch_header_map_001='measure_title',
                            batch_header_map_002='stance',
                            batch_header_map_003='measure_ocd_division_id',
                            batch_header_map_004='organization_position_url',
                            batch_header_map_005='measure_twitter_handle',
                            batch_header_map_006='facebook_url',
                            batch_header_map_007='more_info_url',
                            batch_header_map_008='image_url',
                            batch_header_map_009='image_url_https',
                            batch_header_map_010='statement_text',
                            batch_header_map_011='state_code',
                            batch_header_map_012='election_day',
                            batch_header_map_013='google_civic_election_id',
                        )
                        batch_header_map_id = batch_header_map.id
                        status += " BATCH_HEADER_MAP_SAVED"

                    if positive_value_exists(batch_header_id) and positive_value_exists(batch_header_map_id):
                        # Now save the BatchDescription
                        batch_name = "ENDORSEMENTS_JSON_MEASURES " + " batch_header_id: " + str(batch_header_id)
                        batch_description_text = ""
                        batch_description = BatchDescription.objects.create(
                            batch_header_id=batch_header_id,
                            batch_header_map_id=batch_header_map_id,
                            batch_name=batch_name,
                            batch_description_text=batch_description_text,
                            # google_civic_election_id=google_civic_election_id,
                            kind_of_batch='POSITION',
                            # organization_we_vote_id=organization_we_vote_id,
                            source_uri=batch_uri,
                            batch_set_id=batch_set_id,
                        )
                        status += " BATCH_DESCRIPTION_SAVED"
                        success = True
                except Exception as e:
                    batch_header_id = 0
                    status += " EXCEPTION_BATCH_HEADER"
                    handle_exception(e, logger=logger, exception_message=status)
                    break
            if not positive_value_exists(batch_header_id):
                break

            try:
                batch_row = BatchRow.objects.create(
                    batch_header_id=batch_header_id,
                    batch_row_000=measure_id,
                    batch_row_001=measure_name,
                    batch_row_002=stance,
                    batch_row_003=measure_ocd_division_id,
                    batch_row_004=organization_position_url,
                    batch_row_005=twitter_url,
                    batch_row_006=facebook_url,
                    batch_row_007=website_url,
                    batch_row_008=image_url,
                    batch_row_009=image_url_https,
                    batch_row_010=measure_position_description,
                    batch_row_011=state_code,
                    batch_row_012=election_day,
                    batch_row_013=google_civic_election_id,
                )
                number_of_measure_positions += 1
            except Exception as e:
                # Stop trying to save rows -- break out of the for loop
                status += " EXCEPTION_BATCH_ROW"
                handle_exception(e, logger=logger, exception_message=status)
                break
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'batch_saved': success,
            'number_of_measure_positions': number_of_measure_positions,
            'election_name': election_name,
            'google_civic_election_id': google_civic_election_id,
        }

        return results

class BatchSet(models.Model):
    """
    We call each imported CSV or JSON a “batch set”, and store basic information about it in this table.
    """
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    batch_set_name = models.CharField(max_length=255)
    batch_set_description_text = models.CharField(max_length=255)
    batch_set_source = models.CharField(max_length=255)
    source_uri = models.URLField(blank=True, null=True, verbose_name='uri where data is coming from')
    import_date = models.DateTimeField(verbose_name="date when batch set was imported", null=True, auto_now=True)


class BatchDescription(models.Model):
    """
    We call each imported CSV or JSON a “batch”, and store basic information about it in this table.
    """
    batch_header_id = models.PositiveIntegerField(
        verbose_name="unique id of header row", unique=True, null=False)
    batch_set_id = models.PositiveIntegerField(
        verbose_name="unique id of batch set row", unique=False, null=True)
    batch_header_map_id = models.PositiveIntegerField(
        verbose_name="unique id of header map", unique=True, null=False)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    batch_name = models.CharField(max_length=255)
    kind_of_batch = models.CharField(max_length=32, choices=KIND_OF_BATCH_CHOICES, default=MEASURE)
    organization_we_vote_id = models.CharField(
        verbose_name="if for positions, the organization's we vote id", max_length=255, null=True, blank=True)
    polling_location_we_vote_id = models.CharField(
        verbose_name="if for ballot items, the polling location we vote id", max_length=255, null=True, blank=True)
    batch_description_text = models.CharField(max_length=255)
    source_uri = models.URLField(blank=True, null=True, verbose_name='uri where data is coming from')
    date_created = models.DateTimeField(verbose_name='date first saved', null=True, auto_now=True)


class BatchHeader(models.Model):
    """
    When we get data, it will come with column headers. This table stores the headers from the import file.
    """
    batch_header_column_000 = models.TextField(null=True, blank=True)
    batch_header_column_001 = models.TextField(null=True, blank=True)
    batch_header_column_002 = models.TextField(null=True, blank=True)
    batch_header_column_003 = models.TextField(null=True, blank=True)
    batch_header_column_004 = models.TextField(null=True, blank=True)
    batch_header_column_005 = models.TextField(null=True, blank=True)
    batch_header_column_006 = models.TextField(null=True, blank=True)
    batch_header_column_007 = models.TextField(null=True, blank=True)
    batch_header_column_008 = models.TextField(null=True, blank=True)
    batch_header_column_009 = models.TextField(null=True, blank=True)
    batch_header_column_010 = models.TextField(null=True, blank=True)
    batch_header_column_011 = models.TextField(null=True, blank=True)
    batch_header_column_012 = models.TextField(null=True, blank=True)
    batch_header_column_013 = models.TextField(null=True, blank=True)
    batch_header_column_014 = models.TextField(null=True, blank=True)
    batch_header_column_015 = models.TextField(null=True, blank=True)
    batch_header_column_016 = models.TextField(null=True, blank=True)
    batch_header_column_017 = models.TextField(null=True, blank=True)
    batch_header_column_018 = models.TextField(null=True, blank=True)
    batch_header_column_019 = models.TextField(null=True, blank=True)
    batch_header_column_020 = models.TextField(null=True, blank=True)
    batch_header_column_021 = models.TextField(null=True, blank=True)
    batch_header_column_022 = models.TextField(null=True, blank=True)
    batch_header_column_023 = models.TextField(null=True, blank=True)
    batch_header_column_024 = models.TextField(null=True, blank=True)
    batch_header_column_025 = models.TextField(null=True, blank=True)
    batch_header_column_026 = models.TextField(null=True, blank=True)
    batch_header_column_027 = models.TextField(null=True, blank=True)
    batch_header_column_028 = models.TextField(null=True, blank=True)
    batch_header_column_029 = models.TextField(null=True, blank=True)
    batch_header_column_030 = models.TextField(null=True, blank=True)
    batch_header_column_031 = models.TextField(null=True, blank=True)
    batch_header_column_032 = models.TextField(null=True, blank=True)
    batch_header_column_033 = models.TextField(null=True, blank=True)
    batch_header_column_034 = models.TextField(null=True, blank=True)
    batch_header_column_035 = models.TextField(null=True, blank=True)
    batch_header_column_036 = models.TextField(null=True, blank=True)
    batch_header_column_037 = models.TextField(null=True, blank=True)
    batch_header_column_038 = models.TextField(null=True, blank=True)
    batch_header_column_039 = models.TextField(null=True, blank=True)
    batch_header_column_040 = models.TextField(null=True, blank=True)
    batch_header_column_041 = models.TextField(null=True, blank=True)
    batch_header_column_042 = models.TextField(null=True, blank=True)
    batch_header_column_043 = models.TextField(null=True, blank=True)
    batch_header_column_044 = models.TextField(null=True, blank=True)
    batch_header_column_045 = models.TextField(null=True, blank=True)
    batch_header_column_046 = models.TextField(null=True, blank=True)
    batch_header_column_047 = models.TextField(null=True, blank=True)
    batch_header_column_048 = models.TextField(null=True, blank=True)
    batch_header_column_049 = models.TextField(null=True, blank=True)
    batch_header_column_050 = models.TextField(null=True, blank=True)


class BatchHeaderMap(models.Model):
    """
    When we get data, it will come with column headers. This table stores the replacement header that matches
    the We Vote internal field names.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=True, null=False)
    batch_header_map_000 = models.TextField(null=True, blank=True)
    batch_header_map_001 = models.TextField(null=True, blank=True)
    batch_header_map_002 = models.TextField(null=True, blank=True)
    batch_header_map_003 = models.TextField(null=True, blank=True)
    batch_header_map_004 = models.TextField(null=True, blank=True)
    batch_header_map_005 = models.TextField(null=True, blank=True)
    batch_header_map_006 = models.TextField(null=True, blank=True)
    batch_header_map_007 = models.TextField(null=True, blank=True)
    batch_header_map_008 = models.TextField(null=True, blank=True)
    batch_header_map_009 = models.TextField(null=True, blank=True)
    batch_header_map_010 = models.TextField(null=True, blank=True)
    batch_header_map_011 = models.TextField(null=True, blank=True)
    batch_header_map_012 = models.TextField(null=True, blank=True)
    batch_header_map_013 = models.TextField(null=True, blank=True)
    batch_header_map_014 = models.TextField(null=True, blank=True)
    batch_header_map_015 = models.TextField(null=True, blank=True)
    batch_header_map_016 = models.TextField(null=True, blank=True)
    batch_header_map_017 = models.TextField(null=True, blank=True)
    batch_header_map_018 = models.TextField(null=True, blank=True)
    batch_header_map_019 = models.TextField(null=True, blank=True)
    batch_header_map_020 = models.TextField(null=True, blank=True)
    batch_header_map_021 = models.TextField(null=True, blank=True)
    batch_header_map_022 = models.TextField(null=True, blank=True)
    batch_header_map_023 = models.TextField(null=True, blank=True)
    batch_header_map_024 = models.TextField(null=True, blank=True)
    batch_header_map_025 = models.TextField(null=True, blank=True)
    batch_header_map_026 = models.TextField(null=True, blank=True)
    batch_header_map_027 = models.TextField(null=True, blank=True)
    batch_header_map_028 = models.TextField(null=True, blank=True)
    batch_header_map_029 = models.TextField(null=True, blank=True)
    batch_header_map_030 = models.TextField(null=True, blank=True)
    batch_header_map_031 = models.TextField(null=True, blank=True)
    batch_header_map_032 = models.TextField(null=True, blank=True)
    batch_header_map_033 = models.TextField(null=True, blank=True)
    batch_header_map_034 = models.TextField(null=True, blank=True)
    batch_header_map_035 = models.TextField(null=True, blank=True)
    batch_header_map_036 = models.TextField(null=True, blank=True)
    batch_header_map_037 = models.TextField(null=True, blank=True)
    batch_header_map_038 = models.TextField(null=True, blank=True)
    batch_header_map_039 = models.TextField(null=True, blank=True)
    batch_header_map_040 = models.TextField(null=True, blank=True)
    batch_header_map_041 = models.TextField(null=True, blank=True)
    batch_header_map_042 = models.TextField(null=True, blank=True)
    batch_header_map_043 = models.TextField(null=True, blank=True)
    batch_header_map_044 = models.TextField(null=True, blank=True)
    batch_header_map_045 = models.TextField(null=True, blank=True)
    batch_header_map_046 = models.TextField(null=True, blank=True)
    batch_header_map_047 = models.TextField(null=True, blank=True)
    batch_header_map_048 = models.TextField(null=True, blank=True)
    batch_header_map_049 = models.TextField(null=True, blank=True)
    batch_header_map_050 = models.TextField(null=True, blank=True)


class BatchRow(models.Model):
    """
    Individual data rows
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    # This is used when we have one batch_set that brings in election data for a variety of elections
    google_civic_election_id = models.PositiveIntegerField(verbose_name="election id", default=0, null=True, blank=True)
    # This is useful for filtering while we are processing batch_rows
    state_code = models.CharField(verbose_name="state code for this data", max_length=2, null=True, blank=True)
    batch_row_000 = models.TextField(null=True, blank=True)
    batch_row_001 = models.TextField(null=True, blank=True)
    batch_row_002 = models.TextField(null=True, blank=True)
    batch_row_003 = models.TextField(null=True, blank=True)
    batch_row_004 = models.TextField(null=True, blank=True)
    batch_row_005 = models.TextField(null=True, blank=True)
    batch_row_006 = models.TextField(null=True, blank=True)
    batch_row_007 = models.TextField(null=True, blank=True)
    batch_row_008 = models.TextField(null=True, blank=True)
    batch_row_009 = models.TextField(null=True, blank=True)
    batch_row_010 = models.TextField(null=True, blank=True)
    batch_row_011 = models.TextField(null=True, blank=True)
    batch_row_012 = models.TextField(null=True, blank=True)
    batch_row_013 = models.TextField(null=True, blank=True)
    batch_row_014 = models.TextField(null=True, blank=True)
    batch_row_015 = models.TextField(null=True, blank=True)
    batch_row_016 = models.TextField(null=True, blank=True)
    batch_row_017 = models.TextField(null=True, blank=True)
    batch_row_018 = models.TextField(null=True, blank=True)
    batch_row_019 = models.TextField(null=True, blank=True)
    batch_row_020 = models.TextField(null=True, blank=True)
    batch_row_021 = models.TextField(null=True, blank=True)
    batch_row_022 = models.TextField(null=True, blank=True)
    batch_row_023 = models.TextField(null=True, blank=True)
    batch_row_024 = models.TextField(null=True, blank=True)
    batch_row_025 = models.TextField(null=True, blank=True)
    batch_row_026 = models.TextField(null=True, blank=True)
    batch_row_027 = models.TextField(null=True, blank=True)
    batch_row_028 = models.TextField(null=True, blank=True)
    batch_row_029 = models.TextField(null=True, blank=True)
    batch_row_030 = models.TextField(null=True, blank=True)
    batch_row_031 = models.TextField(null=True, blank=True)
    batch_row_032 = models.TextField(null=True, blank=True)
    batch_row_033 = models.TextField(null=True, blank=True)
    batch_row_034 = models.TextField(null=True, blank=True)
    batch_row_035 = models.TextField(null=True, blank=True)
    batch_row_036 = models.TextField(null=True, blank=True)
    batch_row_037 = models.TextField(null=True, blank=True)
    batch_row_038 = models.TextField(null=True, blank=True)
    batch_row_039 = models.TextField(null=True, blank=True)
    batch_row_040 = models.TextField(null=True, blank=True)
    batch_row_041 = models.TextField(null=True, blank=True)
    batch_row_042 = models.TextField(null=True, blank=True)
    batch_row_043 = models.TextField(null=True, blank=True)
    batch_row_044 = models.TextField(null=True, blank=True)
    batch_row_045 = models.TextField(null=True, blank=True)
    batch_row_046 = models.TextField(null=True, blank=True)
    batch_row_047 = models.TextField(null=True, blank=True)
    batch_row_048 = models.TextField(null=True, blank=True)
    batch_row_049 = models.TextField(null=True, blank=True)
    batch_row_050 = models.TextField(null=True, blank=True)


class BatchHeaderTranslationSuggestion(models.Model):
    """
    When we bring in batches of data, we want to try to map non-standard headers to the We Vote recognized headers.
    This table stores those mappings.
    """
    kind_of_batch = models.CharField(max_length=32, choices=KIND_OF_BATCH_CHOICES, default=MEASURE)
    header_value_recognized_by_we_vote = models.TextField(null=True, blank=True)
    incoming_alternate_header_value = models.TextField(null=True, blank=True)


class BatchRowTranslationMap(models.Model):
    """
    When we bring in batches of data, we want to map different names (for measures, offices, candidates,
    or organizations) to the We Vote recognized names. This table stores those mappings. So for example
    if one batch uses "Prop A" we want to map it to "Proposition A".
    """
    # Are we translating for a Measure, Office, Candidate, or Organization
    kind_of_batch = models.CharField(max_length=32, choices=KIND_OF_BATCH_CHOICES, default=MEASURE)
    # What is the name of the row? (ex/ contest_office_name)
    batch_row_name = models.CharField(verbose_name="name of the the row", max_length=255, null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    row_value_recognized_by_we_vote = models.TextField(null=True, blank=True)
    incoming_alternate_row_value = models.TextField(null=True, blank=True)


class BatchRowActionMeasure(models.Model):
    """
    The definition of the action for importing one Measure.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    batch_row_id = models.PositiveIntegerField(verbose_name="unique id of batch row", unique=True, null=False)
    kind_of_action = models.CharField(max_length=40, choices=KIND_OF_ACTION_CHOICES, default=IMPORT_TO_BE_DETERMINED)

    # Fields from ContestMeasure
    measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True)
    maplight_id = models.CharField(verbose_name="maplight unique identifier",
                                   max_length=255, null=True, blank=True, unique=False)
    vote_smart_id = models.CharField(verbose_name="votesmart unique identifier",
                                     max_length=200, null=True, blank=True, unique=False)
    # The title of the measure (e.g. 'Proposition 42').
    measure_title = models.CharField(verbose_name="measure title", max_length=255, null=False, blank=False)
    # The measure's title as passed over by Google Civic. We save this so we can match to this measure even
    # if we edit the measure's name locally.
    google_civic_measure_title = models.CharField(verbose_name="measure name exactly as received from google civic",
                                                  max_length=255, null=True, blank=True)
    # A brief description of the referendum. This field is only populated for contests of type 'Referendum'.
    measure_subtitle = models.TextField(verbose_name="google civic referendum subtitle",
                                        null=True, blank=True, default="")
    # The text of the measure. This field is only populated for contests of type 'Referendum'.
    measure_text = models.TextField(verbose_name="measure text", null=True, blank=False)
    # A link to the referendum. This field is only populated for contests of type 'Referendum'.
    measure_url = models.CharField(verbose_name="measure details url", max_length=255, null=True, blank=False)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    # ballot_placement: We store ballot_placement in the BallotItem table instead because it is different for each voter
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="primary party", max_length=255, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="district name", max_length=255, null=False, blank=False)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="district scope", max_length=255, null=False, blank=False)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_id = models.CharField(verbose_name="google civic district id", max_length=255, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="state this measure affects", max_length=2, null=True, blank=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_photo_url = models.URLField(verbose_name='url of wikipedia logo', blank=True, null=True)

    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(verbose_name='url of ballotpedia logo', blank=True, null=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)

    status = models.TextField(verbose_name="batch row action measure status", null=True, blank=True, default="")


class BatchRowActionContestOffice(models.Model):
    """
    The definition of the action for importing one Office.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    batch_row_id = models.PositiveIntegerField(verbose_name="unique id of batch row", unique=False, null=False)
    kind_of_action = models.CharField(max_length=40, choices=KIND_OF_ACTION_CHOICES, default=IMPORT_TO_BE_DETERMINED)

    # Fields from ContestOffice
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this contest office", max_length=255, default=None, null=True,
        blank=True)
    # The name of the office for this contest.
    contest_office_name = models.CharField(verbose_name="name of the contest office", max_length=255, null=False,
                                           blank=False)
    # TODO: Was the original contest_office_name replaced with a mapped value from BatchRowTranslationMap?
    # contest_office_name_mapped = models.BooleanField(verbose_name='office name was replaced', default=False)

    # The offices' name as passed over by Google Civic. We save this so we can match to this office even
    # if we edit the office's name locally.
    google_civic_office_name = models.CharField(verbose_name="office name exactly as received from google civic",
                                                max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=255, null=False, blank=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    maplight_id = models.CharField(
        verbose_name="maplight unique identifier", max_length=255, null=True, blank=True)
    ballotpedia_id = models.CharField(
        verbose_name="ballotpedia unique identifier", max_length=255, null=True, blank=True)
    wikipedia_id = models.CharField(verbose_name="wikipedia unique identifier", max_length=255, null=True, blank=True)
    # vote_type (ranked choice, majority)
    # The number of candidates that a voter may vote for in this contest.
    number_voting_for = models.CharField(verbose_name="google civic number of candidates to vote for",
                                         max_length=255, null=True, blank=True)
    # The number of candidates that will be elected to office in this contest.
    number_elected = models.CharField(verbose_name="google civic number of candidates who will be elected",
                                      max_length=255, null=True, blank=True)

    # State code
    state_code = models.CharField(verbose_name="state this office serves", max_length=2, null=True, blank=True)
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="district name", max_length=255, null=True, blank=True)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="google civic district scope",
                                      max_length=255, null=True, blank=True)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_id = models.CharField(verbose_name="google civic district id", max_length=255, null=True, blank=True)

    # The levels of government of the office for this contest. There may be more than one in cases where a
    # jurisdiction effectively acts at two different levels of government; for example, the mayor of the
    # District of Columbia acts at "locality" level, but also effectively at both
    # "administrative-area-2" and "administrative-area-1".
    contest_level0 = models.CharField(verbose_name="google civic level, option 0",
                                      max_length=255, null=True, blank=True)
    contest_level1 = models.CharField(verbose_name="google civic level, option 1",
                                      max_length=255, null=True, blank=True)
    contest_level2 = models.CharField(verbose_name="google civic level, option 2",
                                      max_length=255, null=True, blank=True)

    # ballot_placement: We store ballot_placement in the BallotItem table instead because it is different for each voter

    # A description of any additional eligibility requirements for voting in this contest.
    electorate_specifications = models.CharField(verbose_name="google civic primary party",
                                                 max_length=255, null=True, blank=True)
    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    special = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    elected_office_name = models.CharField(verbose_name="name of the elected office", max_length=255, null=True,
                                           blank=True, default=None)
    candidate_selection_id1 = models.CharField(verbose_name="temporary id of candidate selection 1", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id2 = models.CharField(verbose_name="temporary id of candidate selection 2", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id3= models.CharField(verbose_name="temporary id of candidate selection 3", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id4 = models.CharField(verbose_name="temporary id of candidate selection 4", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id5 = models.CharField(verbose_name="temporary id of candidate selection 5", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id6 = models.CharField(verbose_name="temporary id of candidate selection 6", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id7 = models.CharField(verbose_name="temporary id of candidate selection 7", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id8 = models.CharField(verbose_name="temporary id of candidate selection 8", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id9 = models.CharField(verbose_name="temporary id of candidate selection 9", max_length=255,
                                               null=True, blank=True, default=None)
    candidate_selection_id10 = models.CharField(verbose_name="temporary id of candidate selection 10", max_length=255,
                                                null=True, blank=True, default=None)

    status = models.TextField(verbose_name="batch row action contest office status", null=True, blank=True, default="")


class BatchRowActionElectedOffice(models.Model):
    """
    The definition of the action for importing one Office.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    batch_row_id = models.PositiveIntegerField(verbose_name="unique id of batch row", unique=False, null=False)
    kind_of_action = models.CharField(max_length=40, choices=KIND_OF_ACTION_CHOICES, default=IMPORT_TO_BE_DETERMINED)

    # Fields from ElectedOffice
    elected_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this elected office", max_length=255, default=None, null=True,
        blank=True)
    # The name of the office for this contest.
    elected_office_name = models.CharField(verbose_name="name of the elected office", max_length=255,
                                              null=False, blank=False)
    elected_office_name_es = models.CharField(verbose_name="name of the elected office in Spanish", max_length=255,
                                              null=True, blank=True, default=None)
    # The offices' name as passed over by Google Civic. We save this so we can match to this office even
    # if we edit the office's name locally.
    google_civic_office_name = models.CharField(verbose_name="office name exactly as received from google civic",
                                                max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=255, null=False, blank=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False, blank=False)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    maplight_id = models.CharField(
        verbose_name="maplight unique identifier", max_length=255, null=True, blank=True)
    ballotpedia_id = models.CharField(
        verbose_name="ballotpedia unique identifier", max_length=255, null=True, blank=True)
    wikipedia_id = models.CharField(verbose_name="wikipedia unique identifier", max_length=255, null=True, blank=True)
    # vote_type (ranked choice, majority)
    # The number of candidates that a voter may vote for in this contest.
    # TODO for now comment out number_voting_for for elected_office table
    # number_voting_for = models.CharField(verbose_name="google civic number of candidates to vote for",
    #                                      max_length=255, null=True, blank=True)
    # The number of candidates that will be elected to office in this contest.
    number_elected = models.CharField(verbose_name="google civic number of candidates who will be elected",
                                      max_length=255, null=True, blank=True)

    # State code
    state_code = models.CharField(verbose_name="state this office serves", max_length=2, null=True, blank=True)
    # If this is a partisan election, the name of the party it is for.
    primary_party = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    # The name of the district.
    district_name = models.CharField(verbose_name="district name", max_length=255, null=True, blank=True)
    # The geographic scope of this district. If unspecified the district's geography is not known.
    # One of: national, statewide, congressional, stateUpper, stateLower, countywide, judicial, schoolBoard,
    # cityWide, township, countyCouncil, cityCouncil, ward, special
    district_scope = models.CharField(verbose_name="google civic district scope",
                                      max_length=255, null=True, blank=True)
    # An identifier for this district, relative to its scope. For example, the 34th State Senate district
    # would have id "34" and a scope of stateUpper.
    district_id = models.CharField(verbose_name="google civic district id", max_length=255, null=True, blank=True)

    # The levels of government of the office for this contest. There may be more than one in cases where a
    # jurisdiction effectively acts at two different levels of government; for example, the mayor of the
    # District of Columbia acts at "locality" level, but also effectively at both
    # "administrative-area-2" and "administrative-area-1".
    contest_level0 = models.CharField(verbose_name="google civic level, option 0",
                                      max_length=255, null=True, blank=True)
    contest_level1 = models.CharField(verbose_name="google civic level, option 1",
                                      max_length=255, null=True, blank=True)
    contest_level2 = models.CharField(verbose_name="google civic level, option 2",
                                      max_length=255, null=True, blank=True)

    # ballot_placement: We store ballot_placement in the BallotItem table instead because it is different for each voter

    # A description of any additional eligibility requirements for voting in this contest.
    electorate_specifications = models.CharField(verbose_name="google civic primary party",
                                                 max_length=255, null=True, blank=True)
    # "Yes" or "No" depending on whether this a contest being held outside the normal election cycle.
    special = models.CharField(verbose_name="google civic primary party", max_length=255, null=True, blank=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    elected_office_description = models.CharField(verbose_name="office description", max_length=255,
                                                     null=True, blank=True)
    elected_office_description_es = models.CharField(verbose_name="office description spanish", max_length=255,
                                                     null=True, blank=True)
    elected_office_is_partisan = models.BooleanField(verbose_name='office is_partisan', default=False)
    elected_office_ctcl_id = models.CharField(verbose_name="we vote permanent id for this elected office",
                                              max_length=255, default=None, null=True, blank=True)

    status = models.TextField(verbose_name="batch row action elected office status", null=True, blank=True, default="")


class BatchRowActionPolitician(models.Model):
    """
    The definition of the action for importing one Politician.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    batch_row_id = models.PositiveIntegerField(verbose_name="unique id of batch row", unique=False, null=False)
    kind_of_action = models.CharField(max_length=40, choices=KIND_OF_ACTION_CHOICES, default=IMPORT_TO_BE_DETERMINED)

    # Fields from Politician
    politician_we_vote_id = models.CharField(verbose_name="we vote permanent id of this politician", max_length=255,
                                             default=None, null=True, blank=True, unique=False)
    # See this url for properties: https://docs.python.org/2/library/functions.html#property
    first_name = models.CharField(verbose_name="first name", max_length=255, default=None, null=True, blank=True)
    middle_name = models.CharField(verbose_name="middle name", max_length=255, default=None, null=True, blank=True)
    last_name = models.CharField(verbose_name="last name", max_length=255, default=None, null=True, blank=True)
    politician_name = models.CharField(verbose_name="official full name", max_length=255, default=None, null=True,
                                       blank=True)
    # This is the politician's name from GoogleCivicCandidateCampaign
    google_civic_candidate_name = models.CharField(verbose_name="full name from google civic", max_length=255,
                                                   default=None, null=True, blank=True)
    # This is the politician's name assembled from TheUnitedStatesIo first_name + last_name for quick search
    full_name_assembled = models.CharField(verbose_name="full name assembled from first_name + last_name",
                                           max_length=255, default=None, null=True, blank=True)
    gender = models.CharField("gender", max_length=1, choices=GENDER_CHOICES, default=UNKNOWN)

    birth_date = models.DateField("birth date", default=None, null=True, blank=True)
    # race = enum?
    # official_image_id = ??
    bioguide_id = models.CharField(verbose_name="bioguide unique identifier", max_length=200, null=True, unique=False)
    thomas_id = models.CharField(verbose_name="thomas unique identifier", max_length=200, null=True, unique=False)
    lis_id = models.CharField(verbose_name="lis unique identifier", max_length=200, null=True, blank=True, unique=False)
    govtrack_id = models.CharField(verbose_name="govtrack unique identifier", max_length=200, null=True, unique=False)
    opensecrets_id = models.CharField(verbose_name="opensecrets unique identifier", max_length=200, null=True,
                                      unique=False)
    vote_smart_id = models.CharField(verbose_name="votesmart unique identifier", max_length=200, null=True,
                                     unique=False)
    fec_id = models.CharField(verbose_name="fec unique identifier", max_length=200, null=True, unique=False, blank=True)
    cspan_id = models.CharField(verbose_name="cspan unique identifier", max_length=200, null=True, blank=True,
                                unique=False)
    wikipedia_id = models.CharField(verbose_name="wikipedia url", max_length=500, default=None, null=True, blank=True)
    ballotpedia_id = models.CharField(verbose_name="ballotpedia url", max_length=500, default=None, null=True,
                                      blank=True)
    house_history_id = models.CharField(verbose_name="house history unique identifier", max_length=200, null=True,
                                        blank=True)
    maplight_id = models.CharField(verbose_name="maplight unique identifier", max_length=200, null=True, unique=False,
                                   blank=True)
    washington_post_id = models.CharField(verbose_name="washington post unique identifier", max_length=200, null=True,
                                          unique=False)
    icpsr_id = models.CharField(verbose_name="icpsr unique identifier", max_length=200, null=True, unique=False)
    # The full name of the party the official belongs to.
    political_party = models.CharField(verbose_name="politician political party", max_length=255, null=True)
    state_code = models.CharField(verbose_name="politician home state", max_length=2, null=True)
    politician_url = models.URLField(verbose_name='latest website url of politician', blank=True, null=True)

    politician_twitter_handle = models.CharField(verbose_name='politician twitter screen_name', max_length=255,
                                                  null=True, unique=False)
    we_vote_hosted_profile_image_url_large = models.URLField(verbose_name='we vote hosted large image url',
                                                             blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.URLField(verbose_name='we vote hosted medium image url',
                                                              blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.URLField(verbose_name='we vote hosted tiny image url', blank=True,
                                                            null=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    politician_facebook_id = models.CharField(verbose_name='politician facebook user name', max_length=255, null=True,
                                              unique=False)
    politician_phone_number = models.CharField(verbose_name='politician phone number', max_length=255, null=True,
                                               unique=False)
    politician_googleplus_id = models.CharField(verbose_name='politician googleplus profile name', max_length=255,
                                                null=True, unique=False)
    politician_youtube_id = models.CharField(verbose_name='politician youtube profile name', max_length=255, null=True,
                                             unique=False)
    politician_email_address = models.CharField(verbose_name='politician email address', max_length=80, null=True,
                                                unique=False)

    status = models.TextField(verbose_name="batch row action politician status", null=True, blank=True, default="")


class BatchRowActionCandidate(models.Model):
    """
    The definition of the action for importing one Candidate.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    batch_row_id = models.PositiveIntegerField(verbose_name="unique id of batch row", unique=False, null=False)
    kind_of_action = models.CharField(max_length=40, choices=KIND_OF_ACTION_CHOICES, default=IMPORT_TO_BE_DETERMINED)

    # Fields from Candidate
    candidate_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of this candidate campaign", max_length=255, default=None, null=True,
        blank=True)
    maplight_id = models.CharField(
        verbose_name="maplight candidate id", max_length=255, default=None, null=True, blank=True)
    vote_smart_id = models.CharField(
        verbose_name="vote smart candidate id", max_length=15, default=None, null=True, blank=True, unique=False)
    # The internal We Vote id for the ContestOffice that this candidate is competing for. During setup we need to allow
    # this to be null.
    contest_office_id = models.CharField(
        verbose_name="contest_office_id id", max_length=255, null=True, blank=True)
    # We want to link the candidate to the contest with permanent ids so we can export and import
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the office this candidate is running for", max_length=255, default=None,
        null=True, blank=True, unique=False)
    contest_office_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)
    # politician (internal) link to local We Vote Politician entry. During setup we need to allow this to be null.
    politician_id = models.BigIntegerField(verbose_name="politician unique identifier", null=True, blank=True)
    # The persistent We Vote unique ID of the Politician, so we can export and import into other databases.
    politician_we_vote_id = models.CharField(
        verbose_name="we vote politician id", max_length=255, null=True, blank=True)
    # The candidate's name.
    candidate_name = models.CharField(verbose_name="candidate name", max_length=255, null=False, blank=False)
    # The candidate's name as passed over by Google Civic. We save this so we can match to this candidate even
    # if we edit the candidate's name locally.
    google_civic_candidate_name = models.CharField(verbose_name="candidate name exactly as received from google civic",
                                                   max_length=255, null=False, blank=False)
    # The full name of the party the candidate is a member of.
    party = models.CharField(verbose_name="party", max_length=255, null=True, blank=True)
    # A URL for a photo of the candidate.
    photo_url = models.CharField(verbose_name="photoUrl", max_length=255, null=True, blank=True)
    photo_url_from_maplight = models.URLField(
        verbose_name='candidate portrait url of candidate from maplight', blank=True, null=True)
    photo_url_from_vote_smart = models.URLField(
        verbose_name='candidate portrait url of candidate from vote smart', blank=True, null=True)
    # The order the candidate appears on the ballot relative to other candidates for this contest.
    order_on_ballot = models.CharField(verbose_name="order on ballot", max_length=255, null=True, blank=True)
    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(
        verbose_name="google civic election id", max_length=255, null=True, blank=True)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    ocd_division_id = models.CharField(verbose_name="ocd division id", max_length=255, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="state this candidate serves", max_length=2, null=True, blank=True)
    # The URL for the candidate's campaign web site.
    candidate_url = models.URLField(verbose_name='website url of candidate campaign', blank=True, null=True)
    facebook_url = models.URLField(verbose_name='facebook url of candidate campaign', blank=True, null=True)

    twitter_url = models.URLField(verbose_name='twitter url of candidate campaign', blank=True, null=True)
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    candidate_twitter_handle = models.CharField(
        verbose_name='candidate twitter screen_name', max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="org name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="org location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(verbose_name="number of twitter followers",
                                                  null=False, blank=True, default=0)
    twitter_profile_image_url_https = models.URLField(verbose_name='url of logo from twitter', blank=True, null=True)
    twitter_profile_background_image_url_https = models.URLField(verbose_name='tile-able background from twitter',
                                                                 blank=True, null=True)
    twitter_profile_banner_url_https = models.URLField(verbose_name='profile banner image from twitter',
                                                       blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)

    google_plus_url = models.URLField(verbose_name='google plus url of candidate campaign', blank=True, null=True)
    youtube_url = models.URLField(verbose_name='youtube url of candidate campaign', blank=True, null=True)
    # The email address for the candidate's campaign.
    candidate_email = models.CharField(verbose_name="candidate campaign email", max_length=255, null=True, blank=True)
    # The voice phone number for the candidate's campaign office.
    candidate_phone = models.CharField(verbose_name="candidate campaign phone", max_length=255, null=True, blank=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_photo_url = models.URLField(verbose_name='url of wikipedia logo', blank=True, null=True)

    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(verbose_name='url of ballotpedia logo', blank=True, null=True)

    # Official Statement from Candidate in Ballot Guide
    ballot_guide_official_statement = models.TextField(verbose_name="official candidate statement from ballot guide",
                                                       null=True, blank=True, default="")
    batch_row_action_office_ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    ctcl_uuid = models.CharField(verbose_name="ctcl uuid", max_length=80, null=True, blank=True)
    candidate_is_top_ticket = models.BooleanField(verbose_name="candidate is top ticket", default=False)
    candidate_is_incumbent = models.BooleanField(verbose_name="candidate is currently in the office", default=False)

    # From VIP standard format
    candidate_ctcl_person_id = models.CharField(verbose_name="candidate person id", max_length=255, null=True, blank=True)

    status = models.TextField(verbose_name="batch row action candidate status", null=True, blank=True, default="")


class BatchRowActionOrganization(models.Model):
    """
    The definition of the action for importing one Organization.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    batch_row_id = models.PositiveIntegerField(verbose_name="unique id of batch row", unique=False, null=False)
    kind_of_action = models.CharField(max_length=40, choices=KIND_OF_ACTION_CHOICES, default=IMPORT_TO_BE_DETERMINED)

    # Fields from Organization
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True)
    organization_name = models.CharField(
        verbose_name="organization name", max_length=255, null=False, blank=False)
    organization_website = models.URLField(verbose_name='url of the endorsing organization', blank=True, null=True)
    organization_email = models.EmailField(
        verbose_name='organization contact email address', max_length=255, unique=False, null=True, blank=True)
    organization_contact_name = models.CharField(max_length=255, null=True, unique=False)
    organization_facebook = models.URLField(verbose_name='url of facebook page', blank=True, null=True)
    organization_image = models.CharField(verbose_name='organization image', max_length=255, null=True, unique=False)
    state_served_code = models.CharField(verbose_name="state this organization serves", max_length=2,
                                         null=True, blank=True)
    # The vote_smart special interest group sigId for this organization
    vote_smart_id = models.BigIntegerField(
        verbose_name="vote smart special interest group id", null=True, blank=True)
    organization_description = models.TextField(
        verbose_name="Text description of this organization.", null=True, blank=True)
    organization_address = models.CharField(
        verbose_name='organization street address', max_length=255, unique=False, null=True, blank=True)
    organization_city = models.CharField(max_length=255, null=True, blank=True)
    organization_state = models.CharField(max_length=2, null=True, blank=True)
    organization_zip = models.CharField(max_length=255, null=True, blank=True)
    organization_phone1 = models.CharField(max_length=255, null=True, blank=True)
    organization_phone2 = models.CharField(max_length=255, null=True, blank=True)
    organization_fax = models.CharField(max_length=255, null=True, blank=True)

    # Facebook session information
    facebook_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                       null=True, blank=True)
    fb_username = models.CharField(max_length=20, validators=[alphanumeric], null=True)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of image from facebook', blank=True, null=True)

    # Twitter information
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    organization_twitter_handle = models.CharField(
        verbose_name='organization twitter screen_name', max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="org name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="org location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(verbose_name="number of twitter followers",
                                                  null=False, blank=True, default=0)
    twitter_profile_image_url_https = models.URLField(verbose_name='url of user logo from twitter',
                                                      blank=True, null=True)
    twitter_profile_background_image_url_https = models.URLField(verbose_name='tile-able background from twitter',
                                                                 blank=True, null=True)
    twitter_profile_banner_url_https = models.URLField(verbose_name='profile banner image from twitter',
                                                       blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)

    # Instagram
    organization_instagram_handle = models.CharField(
        verbose_name='organization instagram screen_name', max_length=255, null=True, unique=False)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_thumbnail_url = models.URLField(verbose_name='url of wikipedia logo thumbnail', blank=True, null=True)
    wikipedia_thumbnail_width = models.IntegerField(verbose_name="width of photo", null=True, blank=True)
    wikipedia_thumbnail_height = models.IntegerField(verbose_name="height of photo", null=True, blank=True)
    wikipedia_photo_url = models.URLField(verbose_name='url of wikipedia logo', blank=True, null=True)

    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(verbose_name='url of ballotpedia logo', blank=True, null=True)

    organization_type = models.CharField(
        verbose_name="type of org", max_length=1, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)

    status = models.TextField(verbose_name="batch row action organization status", null=True, blank=True, default="")


class BatchRowActionPosition(models.Model):
    """
    The definition of the action for importing one Position.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    batch_row_id = models.PositiveIntegerField(verbose_name="unique id of batch row", unique=False, null=False)
    kind_of_action = models.CharField(max_length=40, choices=KIND_OF_ACTION_CHOICES, default=IMPORT_TO_BE_DETERMINED)

    # Fields from Position
    position_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True)

    # The id for the generated position that this PositionEntered entry influences
    ballot_item_display_name = models.CharField(verbose_name="text name for ballot item",
                                                max_length=255, null=True, blank=True)
    # We cache the url to an image for the candidate, measure or office for rapid display
    ballot_item_image_url_https = models.URLField(verbose_name='url of https image for candidate, measure or office',
                                                  blank=True, null=True)
    ballot_item_twitter_handle = models.CharField(verbose_name='twitter screen_name for candidate, measure, or office',
                                                  max_length=255, null=True, unique=False)

    # What is the organization name, voter name, or public figure name? We cache this here for rapid display
    speaker_display_name = models.CharField(
        verbose_name="name of the org or person with position", max_length=255, null=True, blank=True, unique=False)
    # We cache the url to an image for the org, voter, or public_figure for rapid display
    speaker_image_url_https = models.URLField(verbose_name='url of https image for org or person with position',
                                              blank=True, null=True)
    speaker_twitter_handle = models.CharField(verbose_name='twitter screen_name for org or person with position',
                                              max_length=255, null=True, unique=False)

    date_entered = models.DateTimeField(verbose_name='date entered', null=True, auto_now=True)
    # The date the this position last changed
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # The organization this position is for
    organization_id = models.BigIntegerField(null=True, blank=True)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the organization", max_length=255, null=True,
        blank=True, unique=False)

    # The voter expressing the opinion
    # Note that for organizations who have friends, the voter_we_vote_id is what we use to link to the friends
    # (in the PositionForFriends table).
    # Public positions from an organization are shared via organization_we_vote_id (in PositionEntered table), while
    # friend's-only  positions are shared via voter_we_vote_id.
    voter_id = models.BigIntegerField(null=True, blank=True)
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the voter expressing the opinion", max_length=255, null=True,
        blank=True, unique=False)

    # The unique id of the public figure expressing the opinion. May be null if position is from org or voter
    # instead of public figure.
    public_figure_we_vote_id = models.CharField(
        verbose_name="public figure we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique ID of the election containing this contest. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id",
                                                max_length=255, null=True, blank=False, default=0)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=True, blank=True)
    # State code
    state_code = models.CharField(verbose_name="us state of the ballot item position is for",
                                  max_length=2, null=True, blank=True)
    # ### Values from Vote Smart ###
    vote_smart_rating_id = models.BigIntegerField(null=True, blank=True, unique=False)
    # Usually in one of these two formats 2015, 2014-2015
    vote_smart_time_span = models.CharField(
        verbose_name="the period in which the organization stated this position", max_length=255, null=True,
        blank=True, unique=False)
    vote_smart_rating = models.CharField(
        verbose_name="vote smart value between 0-100", max_length=255, null=True,
        blank=True, unique=False)
    vote_smart_rating_name = models.CharField(max_length=255, null=True, blank=True, unique=False)

    # The unique We Vote id of the tweet that is the source of the position
    tweet_source_id = models.BigIntegerField(null=True, blank=True)

    # This is the office that the position refers to.
    #  Either contest_measure is filled, contest_office OR candidate_campaign, but not all three
    contest_office_id = models.BigIntegerField(verbose_name='id of contest_office', null=True, blank=True)
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the contest_office", max_length=255, null=True, blank=True, unique=False)
    contest_office_name = models.CharField(verbose_name="name of the office", max_length=255, null=True, blank=True)

    # This is the candidate/politician that the position refers to.
    #  Either candidate_campaign is filled, contest_office OR contest_measure, but not all three
    candidate_campaign_id = models.BigIntegerField(verbose_name='id of candidate_campaign', null=True, blank=True)
    candidate_campaign_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the candidate_campaign", max_length=255, null=True,
        blank=True, unique=False)
    # The candidate's name as passed over by Google Civic. We save this so we can match to this candidate if an import
    # doesn't include a we_vote_id we recognize.
    google_civic_candidate_name = models.CharField(verbose_name="candidate name exactly as received from google civic",
                                                   max_length=255, null=True, blank=True)
    # The measure's title as passed over by Google Civic. We save this so we can match to this measure if an import
    # doesn't include a we_vote_id we recognize.
    google_civic_measure_title = models.CharField(verbose_name="measure title exactly as received from google civic",
                                                  max_length=255, null=True, blank=True)
    # Useful for queries based on Politicians -- not the main table we use for ballot display though
    politician_id = models.BigIntegerField(verbose_name='', null=True, blank=True)
    politician_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for politician", max_length=255, null=True,
        blank=True, unique=False)
    political_party = models.CharField(verbose_name="political party", max_length=255, null=True)

    # This is the measure/initiative/proposition that the position refers to.
    #  Either contest_measure is filled, contest_office OR candidate_campaign, but not all three
    contest_measure_id = models.BigIntegerField(verbose_name='id of contest_measure', null=True, blank=True)
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for the contest_measure", max_length=255, null=True,
        blank=True, unique=False)

    # Strategic denormalization - this is redundant but will make generating the voter guide easier.
    # geo = models.ForeignKey(Geo, null=True, related_name='pos_geo')
    # issue = models.ForeignKey(Issue, null=True, blank=True, related_name='')

    stance = models.CharField(max_length=15, choices=POSITION_CHOICES, default=NO_STANCE)  # supporting/opposing

    statement_text = models.TextField(null=True, blank=True, )
    statement_html = models.TextField(null=True, blank=True, )
    # A link to any location with more information about this position
    more_info_url = models.URLField(blank=True, null=True, verbose_name='url with more info about this position')

    # Did this position come from a web scraper?
    from_scraper = models.BooleanField(default=False)
    # Was this position certified by an official with the organization?
    organization_certified = models.BooleanField(default=False)
    # Was this position certified by an official We Vote volunteer?
    volunteer_certified = models.BooleanField(default=False)

    status = models.TextField(verbose_name="batch row action position status", null=True, blank=True, default="")


class BatchRowActionBallotItem(models.Model):
    """
    The definition of the action for importing one ballot item.
    """
    batch_header_id = models.PositiveIntegerField(verbose_name="unique id of header row", unique=False, null=False)
    batch_row_id = models.PositiveIntegerField(verbose_name="unique id of batch row", unique=True, null=False)
    kind_of_action = models.CharField(max_length=40, choices=KIND_OF_ACTION_CHOICES, default=IMPORT_TO_BE_DETERMINED)

    ballot_item_id = models.IntegerField(verbose_name="ballot item unique id", default=0, null=True, blank=True)
    # Fields from BallotItem
    # The unique id of the voter for which this ballot was retrieved
    voter_id = models.IntegerField(verbose_name="the voter unique id", default=0, null=False, blank=False)
    # The polling location for which this ballot was retrieved
    polling_location_we_vote_id = models.CharField(
        verbose_name="we vote permanent id of the polling location", max_length=255, default=None, null=True,
        blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.CharField(verbose_name="google civic election id", max_length=20, null=False)
    google_civic_election_id_new = models.PositiveIntegerField(
        verbose_name="google civic election id", default=0, null=False)
    state_code = models.CharField(verbose_name="state the ballot item is related to", max_length=2, null=True)

    google_ballot_placement = models.BigIntegerField(
        verbose_name="the order this item should appear on the ballot", null=True, blank=True, unique=False)
    local_ballot_order = models.IntegerField(
        verbose_name="locally calculated order this item should appear on the ballot", null=True, blank=True)

    # The id for this contest office specific to this server.
    contest_office_id = models.PositiveIntegerField(verbose_name="local id for this contest office", default=0,
                                                    null=True, blank=True)
    # The internal We Vote id for the ContestMeasure that this campaign taking a stance on
    contest_office_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this office", max_length=255, default=None, null=True,
        blank=True, unique=False)
    # The local database id for this measure, specific to this server.
    contest_measure_id = models.PositiveIntegerField(
        verbose_name="contest_measure unique id", default=0, null=True, blank=True)
    # The internal We Vote id for the ContestMeasure that this campaign taking a stance on
    contest_measure_we_vote_id = models.CharField(
        verbose_name="we vote permanent id for this measure", max_length=255, default=None, null=True,
        blank=True, unique=False)
    # This is a sortable name, either the candidate name or the measure name
    ballot_item_display_name = models.CharField(verbose_name="a label we can sort by", max_length=255, null=True,
                                                blank=True)

    measure_subtitle = models.TextField(verbose_name="google civic referendum subtitle",
                                        null=True, blank=True, default="")

    status = models.TextField(verbose_name="batch row action ballot item status", null=True, blank=True, default="")
