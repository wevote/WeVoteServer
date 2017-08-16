# import_export_batches/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import MEASURE, CANDIDATE, POLITICIAN
from .models import BatchManager, BatchDescription, BatchHeaderMap, BatchRow, BatchRowActionOrganization, \
    BatchRowActionMeasure, BatchRowActionElectedOffice, BatchRowActionContestOffice, BatchRowActionPolitician, \
    BatchRowActionCandidate, \
    CLEAN_DATA_MANUALLY, CONTEST_OFFICE, ELECTED_OFFICE, POSITION, \
    CREATE, ADD_TO_EXISTING, QUERY_ERROR, \
    TO_BE_DETERMINED, DO_NOT_PROCESS, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES, BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_ELECTED_OFFICES, BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS
from candidate.models import CandidateCampaign, CandidateCampaignManager
from django.db.models import Q
from electoral_district.controllers import retrieve_electoral_district
from election.models import ElectionManager
from exception.models import handle_exception
from measure.models import ContestMeasure, ContestMeasureManager
from office.models import ContestOffice, ContestOfficeManager, ElectedOffice, ElectedOfficeManager
from organization.models import Organization, OrganizationManager, \
    NONPROFIT_501C3, NONPROFIT_501C4, POLITICAL_ACTION_COMMITTEE, \
    CORPORATION, NEWS_CORPORATION, UNKNOWN
from politician.models import Politician, PoliticianManager
from twitter.models import TwitterUserManager
from voter_guide.models import ORGANIZATION_WORD
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists, extract_twitter_handle_from_text_string


logger = wevote_functions.admin.get_logger(__name__)

# VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")


def create_batch_row_actions(batch_header_id, batch_row_id):
    """
    Cycle through all BatchRow entries for this batch_header_id and move the values we can find into
    the BatchRowActionYYY table so we can review it before importing it
    :param batch_header_id:
    :param batch_row_id:
    :return:
    """
    success = False
    update_success = False
    status = ""
    number_of_batch_actions_created = 0
    number_of_batch_actions_updated = 0
    number_of_batch_actions_failed = 0
    kind_of_batch = ""

    if not positive_value_exists(batch_header_id):
        status = "CREATE_BATCH_ROW_ACTIONS-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                          success,
            'status':                           status,
            'batch_header_id':                  batch_header_id,
            'kind_of_batch':                    kind_of_batch,
            'batch_actions_created':            success,
            'number_of_batch_actions_created':  number_of_batch_actions_created,
            'batch_actions_updated':            update_success,
            'number_of_batch_actions_updated':  number_of_batch_actions_updated
        }
        return results

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    batch_header_map_found = False
    if batch_description_found:
        kind_of_batch = batch_description.kind_of_batch

        try:
            batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
            batch_header_map_found = True
        except BatchHeaderMap.DoesNotExist:
            # This is fine
            batch_header_map = BatchHeaderMap()

    batch_row_list = []
    batch_row_list_found = False
    if batch_header_map_found:
        try:
            batch_row_list = BatchRow.objects.all()
            batch_row_list = batch_row_list.filter(batch_header_id=batch_header_id)
            if positive_value_exists(batch_row_id):
                batch_row_list = batch_row_list.filter(id=batch_row_id)

            if len(batch_row_list):
                batch_row_list_found = True
        except BatchRow.DoesNotExist:
            # This is fine
            pass

    if batch_description_found and batch_header_map_found and batch_row_list_found:
        for one_batch_row in batch_row_list:
            if kind_of_batch == CANDIDATE:
                results = create_batch_row_action_candidate(batch_description, batch_header_map, one_batch_row)

                if results['action_candidate_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['new_action_candidate_created']:
                    # for now, do not handle batch_row_action_candidate data
                    # batch_row_action_candidate = results['batch_row_action_candidate']
                    number_of_batch_actions_created += 1
                    success = True
                    # Now check for warnings (like "this is a duplicate"). If warnings are found,
                    # add the warning to batch_row_action_measure entry
                    # batch_row_action_measure.kind_of_action = "TEST"
            elif kind_of_batch == CONTEST_OFFICE:
                results = create_batch_row_action_contest_office(batch_description, batch_header_map, one_batch_row)

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
                    number_of_batch_actions_created += 1
                    success = True
            elif kind_of_batch == ELECTED_OFFICE:
                results = create_batch_row_action_elected_office(batch_description, batch_header_map, one_batch_row)

                if results['action_elected_office_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['new_action_elected_office_created']:
                    # for now, do not handle batch_row_action_elected_office data
                    # batch_row_action_elected_office = results['batch_row_action_elected_office']
                    number_of_batch_actions_created += 1
                    success = True
            elif kind_of_batch == MEASURE:
                results = create_batch_row_action_measure(batch_description, batch_header_map, one_batch_row)

                if results['action_measure_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['new_action_measure_created']:
                    # for now, do not handle batch_row_action_measure data
                    # batch_row_action_measure = results['batch_row_action_measure']
                    number_of_batch_actions_created += 1
                    success = True
            elif kind_of_batch == ORGANIZATION_WORD:
                results = create_batch_row_action_organization(batch_description, batch_header_map, one_batch_row)

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
                    number_of_batch_actions_created += 1
                    success = True
                else:
                    number_of_batch_actions_failed += 1
            elif kind_of_batch == POLITICIAN:
                results = create_batch_row_action_politician(batch_description, batch_header_map, one_batch_row)

                if results['action_politician_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['new_action_politician_created']:
                    # for now, do not handle batch_row_action_politician data
                    # batch_row_action_politician = results['batch_row_action_politician']
                    number_of_batch_actions_created += 1
                    success = True
            elif kind_of_batch == POSITION:
                results = create_batch_row_action_position(batch_description, batch_header_map, one_batch_row)

                if results['action_position_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['new_action_position_created']:
                    # for now, do not handle batch_row_action_politician data
                    # batch_row_action_politician = results['batch_row_action_politician']
                    number_of_batch_actions_created += 1
                    success = True

    results = {
        'success':                          success,
        'status':                           status,
        'batch_header_id':                  batch_header_id,
        'kind_of_batch':                    kind_of_batch,
        'batch_actions_created':            success,
        'number_of_batch_actions_created':  number_of_batch_actions_created,
        'batch_actions_updated':            update_success,
        'number_of_batch_actions_updated':  number_of_batch_actions_updated
    }
    return results


def create_batch_row_action_organization(batch_description, batch_header_map, one_batch_row):
    """

    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()
    success = False
    status = ""
    batch_row_action_updated = False
    batch_row_action_created = False
    kind_of_action = ""

    # Does a BatchRowActionOrganization entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_organization(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_organization = existing_results['batch_row_action_organization']
        batch_row_action_updated = True
    else:
        # If a BatchRowActionOrganization entry does not exist, create one
        try:
            batch_row_action_organization = BatchRowActionOrganization.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
            )
            batch_row_action_created = True
            success = True
            status = "BATCH_ROW_ACTION_ORGANIZATION_CREATED"
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_organization = BatchRowActionOrganization()
            success = False
            status = "BATCH_ROW_ACTION_ORGANIZATION_NOT_CREATED"

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_organization': batch_row_action_organization,
            }
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS

    # Find the column in the incoming batch_row with the header title specified (ex/ "organization_name"
    organization_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "organization_we_vote_id", batch_header_map, one_batch_row)
    organization_name = batch_manager.retrieve_value_from_batch_row(
        "organization_name", batch_header_map, one_batch_row)
    organization_twitter_handle_raw = batch_manager.retrieve_value_from_batch_row(
        "organization_twitter_handle", batch_header_map, one_batch_row)
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle_raw)
    organization_facebook = batch_manager.retrieve_value_from_batch_row(
        "organization_facebook", batch_header_map, one_batch_row)
    organization_instagram = batch_manager.retrieve_value_from_batch_row(
        "organization_instagram", batch_header_map, one_batch_row)
    organization_website = batch_manager.retrieve_value_from_batch_row(
        "organization_website", batch_header_map, one_batch_row)
    organization_phone1 = batch_manager.retrieve_value_from_batch_row(
        "organization_phone1", batch_header_map, one_batch_row)
    organization_address = batch_manager.retrieve_value_from_batch_row(
        "organization_address", batch_header_map, one_batch_row)
    organization_city = batch_manager.retrieve_value_from_batch_row(
        "organization_city", batch_header_map, one_batch_row)
    organization_state = batch_manager.retrieve_value_from_batch_row(
        "organization_state", batch_header_map, one_batch_row)
    organization_zip = batch_manager.retrieve_value_from_batch_row(
        "organization_zip", batch_header_map, one_batch_row)
    state_served_code = batch_manager.retrieve_value_from_batch_row("state_served_code", batch_header_map, one_batch_row)
    organization_type = batch_manager.retrieve_value_from_batch_row(
        "organization_type", batch_header_map, one_batch_row)
    organization_contact_name = batch_manager.retrieve_value_from_batch_row(
        "organization_contact_name", batch_header_map, one_batch_row)

    # Now check for warnings (like "this is a duplicate"). If warnings are found,
    # add the warning to batch_row_action_organization entry
    # batch_row_action_organization.kind_of_action = "TEST"
    keep_looking_for_duplicates = True
    if positive_value_exists(organization_we_vote_id):
        # If here, then we are updating an existing known record
        keep_looking_for_duplicates = False
        kind_of_action = ADD_TO_EXISTING
        # TODO We want to search the Organization table for the existing record with this organization_we_vote_id
        #  and describe what we will be updating.

    if keep_looking_for_duplicates and positive_value_exists(organization_twitter_handle):
        try:
            organization_query = Organization.objects.all()
            organization_query = organization_query.filter(
                organization_twitter_handle__iexact=organization_twitter_handle)

            organization_list = list(organization_query)
            if len(organization_list):
                # At least one entry exists
                status += 'BATCH_ROW_ACTION_ORGANIZATION_LIST_RETRIEVED '
                batch_row_action_found = True
                # if a single entry matches, update that entry
                if len(organization_list) == 1:
                    kind_of_action = ADD_TO_EXISTING
                    single_entry_found = True
                    multiple_entries_found = False
                    organization_we_vote_id = organization_list.first().we_vote_id
                else:
                    # more than one entry found with a match in Organization
                    kind_of_action = CLEAN_DATA_MANUALLY
                    single_entry_found = False
                    multiple_entries_found = True
                    keep_looking_for_duplicates = False  # Deal with multiple Twitter duplicates manually
            else:
                kind_of_action = CREATE
                single_entry_found = False
        except Organization.DoesNotExist:
            batch_row_action_found = False
            # success = True
            status += "BATCH_ROW_ACTION_EXISTING_ORGANIZATION_NOT_FOUND "
            kind_of_action = TO_BE_DETERMINED  # We want to use other criteria to see if there is a duplicate
        except Exception as e:
            keep_looking_for_duplicates = False
            kind_of_action = QUERY_ERROR
            pass
    # twitter handle does not exist, next look up against other data that might match

    # Transform data to our constants: BatchRowTranslationMap
    # ORGANIZATION_TYPE_CHOICES = (
    #     (NONPROFIT_501C3, 'Nonprofit 501c3'),
    #     (NONPROFIT_501C4, 'Nonprofit 501c4'),
    #     (POLITICAL_ACTION_COMMITTEE, 'Political Action Committee'),
    #     (CORPORATION, 'Corporation'),
    #     (NEWS_CORPORATION, 'News Corporation'),
    #     (UNKNOWN, 'Unknown'),
    # )
    organization_type_transformed = UNKNOWN  # Default to this
    if organization_type.lower() == "c3":
        organization_type_transformed = NONPROFIT_501C3
    elif organization_type.lower() == "c4":
        organization_type_transformed = NONPROFIT_501C4

    try:
        batch_row_action_organization.organization_we_vote_id = organization_we_vote_id
        batch_row_action_organization.organization_name = organization_name
        batch_row_action_organization.organization_twitter_handle = organization_twitter_handle
        batch_row_action_organization.organization_facebook = organization_facebook
        batch_row_action_organization.organization_instagram_handle = organization_instagram
        batch_row_action_organization.organization_website = organization_website
        batch_row_action_organization.organization_phone1 = organization_phone1
        batch_row_action_organization.organization_address = organization_address
        batch_row_action_organization.organization_city = organization_city
        batch_row_action_organization.organization_state = organization_state
        batch_row_action_organization.organization_zip = organization_zip
        batch_row_action_organization.state_served_code = state_served_code
        batch_row_action_organization.organization_type = organization_type_transformed
        batch_row_action_organization.organization_contact_name = organization_contact_name
        batch_row_action_organization.kind_of_action = kind_of_action
        batch_row_action_organization.save()
        success = True
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_ORGANIZATION_UNABLE_TO_SAVE "

    results = {
        'success': success,
        'status': status,
        'batch_row_action_created': batch_row_action_created,
        'batch_row_action_updated': batch_row_action_updated,
        'batch_row_action_organization': batch_row_action_organization,
    }
    return results


def create_batch_row_action_measure(batch_description, batch_header_map, one_batch_row):
    """
    Handle batch_row for measure type
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()

    new_action_measure_created = False
    action_measure_updated = False
    state_code = ''
    batch_row_action_measure_status = ''
    status = ''
    measure_we_vote_id = ''

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES

    # Find the column in the incoming batch_row with the header == measure_title
    measure_title = batch_manager.retrieve_value_from_batch_row("measure_title", batch_header_map, one_batch_row)
    # Find the column in the incoming batch_row with the header == state_code
    electoral_district_id = batch_manager.retrieve_value_from_batch_row("electoral_district_id", batch_header_map,
                                                                        one_batch_row)
    google_civic_election_id = str(batch_description.google_civic_election_id)

    # get state code from electoral_district_id
    results = retrieve_electoral_district(electoral_district_id)
    if results['electoral_district_found']:
        if results['state_code_found']:
            state_code = results['state_code']
            # state_code = results.values_list('state_code', flat=True).get()
    else:
        # state_code = ''
        batch_row_action_measure_status = 'ELECTORAL_DISTRICT_NOT_FOUND'
        # kind_of_action = 'TBD'

    measure_text = batch_manager.retrieve_value_from_batch_row("measure_name",
                                                               batch_header_map,
                                                               one_batch_row)
    measure_subtitle = batch_manager.retrieve_value_from_batch_row("measure_sub_title",
                                                                   batch_header_map,
                                                                   one_batch_row)
    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("ctcl_uuid", batch_header_map, one_batch_row)

    # Look up ContestMeasure to see if an entry exists
    contest_measure = ContestMeasure()
    # These three parameters are needed to look up in Contest Measure table for a match
    if positive_value_exists(measure_title) and positive_value_exists(state_code) and \
            positive_value_exists(google_civic_election_id):
        try:
            contest_measure_query = ContestMeasure.objects.all()
            contest_measure_item_list = contest_measure_query.filter(measure_title__iexact=measure_title,
                                                                     state_code__iexact=state_code,
                                                                     google_civic_election_id=google_civic_election_id)

            if contest_measure_item_list or len(contest_measure_item_list):
                # entry exists
                batch_row_action_measure_status = 'BATCH_ROW_ACTION_MEASURE_RETRIEVED'
                # batch_row_action_found = True
                # new_action_measure_created = False
                # success = True
                batch_row_action_measure = contest_measure_item_list
                # if a single entry matches, update that entry
                if len(contest_measure_item_list) == 1:
                    kind_of_action = ADD_TO_EXISTING
                    measure_we_vote_id = contest_measure_query.first().we_vote_id
                else:
                    # more than one entry found with a match in ContestMeasure
                    kind_of_action = 'DO_NOT_PROCESS'
            else:
                kind_of_action = CREATE
        except ContestMeasure.DoesNotExist:
            batch_row_action_measure = BatchRowActionMeasure()
            # batch_row_action_found = False
            # success = True
            batch_row_action_measure_status = "BATCH_ROW_ACTION_MEASURE_NOT_FOUND"
            kind_of_action = 'TBD'
    else:
        kind_of_action = 'TBD'
        batch_row_action_measure_status = "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_MEASURE_CREATE"

    try:
        # check for duplicate entries in the same data set
        # Check if measure_title, state_code match exists in BatchRowActionMeasure for this header_id
        existing_batch_row_action_measure_query = BatchRowActionMeasure.objects.all()
        existing_batch_row_action_measure_query = existing_batch_row_action_measure_query.filter(
            batch_header_id=batch_description.batch_header_id, measure_title__iexact=measure_title,
            state_code__iexact=state_code, google_civic_election_id=google_civic_election_id)
        existing_batch_row_action_measure_list = list(existing_batch_row_action_measure_query)
        number_of_existing_entries = len(existing_batch_row_action_measure_list)
        if not number_of_existing_entries:
            # no entry exists, create one
            updated_values = {
                'measure_title': measure_title,
                'state_code': state_code,
                'measure_text': measure_text,
                'measure_subtitle': measure_subtitle,
                'kind_of_action': kind_of_action,
                'measure_we_vote_id': measure_we_vote_id,
                'ctcl_uuid': ctcl_uuid,
                'google_civic_election_id': google_civic_election_id,
                'status': batch_row_action_measure_status
            }

            batch_row_action_measure, new_action_measure_created = BatchRowActionMeasure.objects.update_or_create(
                batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                defaults=updated_values)
            # new_action_measure_created = True
            success = True
            status += "CREATE_BATCH_ROW_ACTION_MEASURE-BATCH_ROW_ACTION_MEASURE_CREATED"
        else:
            # # if batch_header_id is same then it is a duplicate entry?
            existing_measure_entry = existing_batch_row_action_measure_query.first()
            if one_batch_row.id != existing_measure_entry.batch_row_id:
                # duplicate entry, create a new entry but set kind_of_action as DO_NOT_PROCESS and
                # set status as duplicate
                # kind_of_action = 'DO_NOT_PROCESS'
                updated_values = {
                    'measure_title': measure_title,
                    'state_code': state_code,
                    'measure_text': measure_text,
                    'measure_subtitle': measure_subtitle,
                    'measure_we_vote_id': measure_we_vote_id,
                    'kind_of_action': 'DO_NOT_PROCESS',
                    'ctcl_uuid': ctcl_uuid,
                    'google_civic_election_id': google_civic_election_id,
                    'status': 'DUPLICATE_ELECTED_OFFICE_ENTRY'
                }

                batch_row_action_measure, new_action_measure_created = BatchRowActionMeasure.objects.update_or_create(
                    batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                    defaults=updated_values)
                status += 'CREATE_BATCH_ROW_ACTION_MEASURE-BATCH_ROW_ACTION_MEASURE_DUPLICATE_ENTRY'
                success = True
                # TODO should duplicate entry be counted as updated?
                action_measure_updated = True
                # this is a duplicate entry, mark it's kind_of_action as DO_NOT_PROCESS and status as duplicate
            else:
                # existing entry but not duplicate
                status += 'CREATE_BATCH_ROW_ACTION_MEASURE-BATCH_ROW_ACTION_MEASURE_ENTRY_EXISTS'
                success = True
                # TODO update existing entry is not yet handled
                batch_row_action_measure = existing_batch_row_action_measure_query.get()
    except Exception as e:
        batch_row_action_measure = BatchRowActionMeasure()
        batch_row_action_found = False
        success = False
        new_action_measure_created = False
        status = "CREATE_BATCH_ROW_ACTION_MEASURE-BATCH_ROW_ACTION_MEASURE_RETRIEVE_ERROR"
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success':                      success,
        'status':                       status,
        'new_action_measure_created':   new_action_measure_created,
        'action_measure_updated':       action_measure_updated,
        'batch_row_action_measure':     batch_row_action_measure,
    }
    return results


def create_batch_row_action_elected_office(batch_description, batch_header_map, one_batch_row):
    """
    Handle batch_row for elected office
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()

    new_action_elected_office_created = False
    action_elected_office_updated = False
    state_code = ''
    batch_row_action_elected_office_status = ''
    elected_office_we_vote_id = ''
    success = False
    status = ''

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_ELECTED_OFFICES

    # Find the column in the incoming batch_row with the header == elected_office_name
    elected_office_name = batch_manager.retrieve_value_from_batch_row("elected_office_name",
                                                                      batch_header_map, one_batch_row)
    # Find the column in the incoming batch_row with the header == state_code
    electoral_district_id = batch_manager.retrieve_value_from_batch_row("electoral_district_id", batch_header_map,
                                                                        one_batch_row)
    google_civic_election_id = str(batch_description.google_civic_election_id)
    results = retrieve_electoral_district(electoral_district_id)
    if results['electoral_district_found']:
        if results['state_code_found']:
            state_code = results['state_code']
    else:
        # state_code = ''
        batch_row_action_office_status = 'ELECTORAL_DISTRICT_NOT_FOUND'
        kind_of_action = 'TBD'

    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("elected_office_ctcl_uuid", batch_header_map, one_batch_row)

    elected_office_description = batch_manager.retrieve_value_from_batch_row("elected_office_description",
                                                                             batch_header_map, one_batch_row)
    elected_office_is_partisan = batch_manager.retrieve_value_from_batch_row("elected_office_is_partisan",
                                                                             batch_header_map, one_batch_row)
    elected_office_name_es = batch_manager.retrieve_value_from_batch_row("elected_office_name_es", batch_header_map,
                                                                         one_batch_row)
    elected_office_description_es = batch_manager.retrieve_value_from_batch_row("elected_office_description_es",
                                                                                batch_header_map, one_batch_row)

    elected_office_ctcl_id = batch_manager.retrieve_value_from_batch_row("elected_office_batch_id", batch_header_map,
                                                                         one_batch_row)
    # Look up ElectedOffice to see if an entry exists
    # These three parameters are needed to look up in ElectedOffice table for a match
    if positive_value_exists(elected_office_name) and positive_value_exists(state_code) and \
            positive_value_exists(google_civic_election_id):
        try:
            elected_office_query = ElectedOffice.objects.all()
            elected_office_query = elected_office_query.filter(elected_office_name__iexact=elected_office_name,
                                                               state_code__iexact=state_code,
                                                               google_civic_election_id=google_civic_election_id)

            elected_office_item_list = list(elected_office_query)
            if len(elected_office_item_list):
                # entry exists
                batch_row_action_elected_office_status = 'ELECTED_OFFICE_ENTRY_EXISTS'
                batch_row_action_found = True
                new_action_elected_office_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(elected_office_item_list) == 1:
                    kind_of_action = ADD_TO_EXISTING
                    elected_office_we_vote_id = elected_office_query.first().we_vote_id
                else:
                    # more than one entry found with a match in ElectedOffice
                    kind_of_action = 'DO_NOT_PROCESS'
                    # elected_office_we_vote_id = elected_office_item_list.values('elected_office_we_vote_id')
            else:
                kind_of_action = CREATE
        except ElectedOffice.DoesNotExist:
            batch_row_action_elected_office = BatchRowActionElectedOffice()
            batch_row_action_found = False
            # success = True
            batch_row_action_elected_office_status = "BATCH_ROW_ACTION_ELECTED_OFFICE_NOT_FOUND"
            kind_of_action = 'TBD'
    else:
        kind_of_action = 'TBD'
        batch_row_action_elected_office_status = "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_ELECTED_OFFICE_CREATE"
    # Create a new entry in BatchRowActionElectedOffice
    try:

        # Check if elected_office_name, state_code match exists in BatchRowActionElectedOffice
        # for this header_id (Duplicate entries in the same data set
        existing_batch_row_action_elected_office_query = BatchRowActionElectedOffice.objects.all()
        existing_batch_row_action_elected_office_query = existing_batch_row_action_elected_office_query.filter(
            batch_header_id=batch_description.batch_header_id, elected_office_name__iexact=elected_office_name,
            state_code__iexact=state_code, google_civic_election_id=google_civic_election_id)
        existing_batch_row_action_elected_office_list = list(existing_batch_row_action_elected_office_query)
        number_of_existing_entries = len(existing_batch_row_action_elected_office_list)
        if not number_of_existing_entries:
            # no entry exists, create one
            updated_values = {
                'elected_office_name': elected_office_name,
                'state_code': state_code,
                'elected_office_description': elected_office_description,
                'ctcl_uuid': ctcl_uuid,
                'elected_office_is_partisan': elected_office_is_partisan,
                'elected_office_we_vote_id': elected_office_we_vote_id,
                'kind_of_action': kind_of_action,
                'google_civic_election_id': google_civic_election_id,
                'status': batch_row_action_elected_office_status,
                'elected_office_name_es': elected_office_name_es,
                'elected_office_description_es': elected_office_description_es,
                'elected_office_ctcl_id': elected_office_ctcl_id
            }

            batch_row_action_elected_office, new_action_elected_office_created = BatchRowActionElectedOffice.objects.\
                update_or_create(batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                                 defaults=updated_values)
            # new_action_elected_office_created = True
            success = True
            status += "CREATE_BATCH_ROW_ACTION_ELECTED_OFFICE-BATCH_ROW_ACTION_ELECTED_OFFICE_CREATED"
        else:
            # # if batch_header_id is same then it is a duplicate entry?
            existing_elected_office_entry = existing_batch_row_action_elected_office_query.first()
            if one_batch_row.id != existing_elected_office_entry.batch_row_id:
                # duplicate entry, create a new entry but set kind_of_action as DO_NOT_PROCESS and
                # set status as duplicate
                # kind_of_action = 'DO_NOT_PROCESS'
                updated_values = {
                    'elected_office_name': elected_office_name,
                    'state_code': state_code,
                    'elected_office_description': elected_office_description,
                    'ctcl_uuid': ctcl_uuid,
                    'elected_office_is_partisan': elected_office_is_partisan,
                    'elected_office_we_vote_id': elected_office_we_vote_id,
                    'kind_of_action': 'DO_NOT_PROCESS',
                    'google_civic_election_id': google_civic_election_id,
                    'status': 'DUPLICATE_ELECTED_OFFICE_ENTRY',
                    'elected_office_name_es': elected_office_name_es,
                    'elected_office_description_es': elected_office_description_es,
                    'elected_office_ctcl_id': elected_office_ctcl_id
                }

                batch_row_action_elected_office, new_action_elected_office_created = \
                    BatchRowActionElectedOffice.objects.update_or_create(
                        batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                        defaults=updated_values)
                status += 'CREATE_BATCH_ROW_ACTION_ELECTED_OFFICE-BATCH_ROW_ACTION_ELECTED_OFFICE_DUPLICATE_ENTRIES'
                success = True
                action_elected_office_updated = True
                # this is a duplicate entry, mark it's kind_of_action as DO_NOT_PROCESS and status as duplicate
            else:
                # existing entry but not duplicate
                status += 'BATCH_ROW_ACTION_ELECTED_OFFICE_ENTRY_EXISTS'
                success = True
                batch_row_action_elected_office = existing_elected_office_entry
    except Exception as e:
        batch_row_action_elected_office = BatchRowActionElectedOffice()
        batch_row_action_found = False
        success = False
        new_action_elected_office_created = False
        status = "CREATE_BATCH_ROW_ACTION_ELECTED_OFFICE_BATCH_ROW_ACTION_ELECTED_OFFICE_RETRIEVE_ERROR"
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success':                              success,
        'status':                               status,
        'new_action_elected_office_created':    new_action_elected_office_created,
        'action_elected_office_updated':        action_elected_office_updated,
        'batch_row_action_elected_office':      batch_row_action_elected_office,
    }
    return results


def create_batch_row_action_contest_office(batch_description, batch_header_map, one_batch_row):
    """
    Handle batch_row for contest office type
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()

    new_action_contest_office_created = False
    action_contest_office_updated = False
    batch_row_action_updated = False
    batch_row_action_created = False
    state_code = ''
    batch_row_action_contest_office_status = ''
    contest_office_name_mapped = False
    status = ''
    success = False

    # Does a BatchRowActionContestOffice entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_contest_office(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_contest_office = existing_results['batch_row_action_contest_office']
        batch_row_action_updated = True
    else:
        # If a BatchRowActionContestOffice entry does not exist, create one
        try:
            batch_row_action_contest_office = BatchRowActionContestOffice.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
            )
            batch_row_action_created = True
            status = "BATCH_ROW_ACTION_CONTEST_OFFICE_CREATED"
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_contest_office = BatchRowActionContestOffice()
            success = False
            status = "BATCH_ROW_ACTION_CONTEST_OFFICE_NOT_CREATED"

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_contest_office': batch_row_action_contest_office,
            }
            # 'new_action_contest_office_created':    new_action_contest_office_created,
            # 'action_contest_office_updated':        action_contest_office_updated,
            # 'batch_row_action_contest_office':      batch_row_action_contest_office,
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES

    contest_office_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "contest_office_we_vote_id", batch_header_map, one_batch_row)

    google_civic_election_id = str(batch_description.google_civic_election_id)

    electoral_district_id = batch_manager.retrieve_value_from_batch_row("electoral_district_id", batch_header_map,
                                                                        one_batch_row)
    results = retrieve_electoral_district(electoral_district_id)
    if results['electoral_district_found']:
        if results['state_code_found']:
            state_code = results['state_code']
    else:
        if positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code):
            # Check to see if there is a state served for the election
            election_manager = ElectionManager()
            results = election_manager.retrieve_election(google_civic_election_id)
            if results['election_found']:
                election = results['election']
                state_code = election.state_code
        else:
            # state_code = ''
            batch_row_action_contest_office_status = 'ELECTORAL_DISTRICT_NOT_FOUND'
            kind_of_action = 'TBD'

    # Find the column in the incoming batch_row with the header == contest_office_name
    contest_office_name = batch_manager.retrieve_value_from_batch_row("contest_office_name", batch_header_map,
                                                                      one_batch_row)

    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("contest_office_ctcl_uuid", batch_header_map, one_batch_row)

    contest_office_votes_allowed = batch_manager.retrieve_value_from_batch_row("contest_office_votes_allowed",
                                                                               batch_header_map, one_batch_row)
    contest_office_number_elected = batch_manager.retrieve_value_from_batch_row("contest_office_number_elected",
                                                                                batch_header_map, one_batch_row)
    elected_office_ctcl_id = batch_manager.retrieve_value_from_batch_row("elected_office_id", batch_header_map,
                                                                         one_batch_row)
    candidate_selection_id1 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id1", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id2 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id2", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id3 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id3", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id4 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id4", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id5 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id5", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id6 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id6", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id7 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id7", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id8 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id8", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id9 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id9", batch_header_map,
                                                                          one_batch_row)
    candidate_selection_id10 = batch_manager.retrieve_value_from_batch_row("candidate_selection_id10", batch_header_map,
                                                                           one_batch_row)

    batch_set_id = batch_description.batch_set_id

    # retrieve elected_office_name from elected_office_id
    # batch_manager = BatchManager()
    elected_office_name = batch_manager.fetch_elected_office_name_from_elected_office_ctcl_id(elected_office_ctcl_id,
                                                                                              batch_set_id)

    # Look up ContestOffice to see if an entry exists
    # contest_office = ContestOffice()
    keep_looking_for_duplicates = True
    if positive_value_exists(contest_office_we_vote_id):
        # If here, then we are updating an existing known record
        keep_looking_for_duplicates = False
        kind_of_action = ADD_TO_EXISTING
        # TODO We want to search the ContestOffice table for the existing record with this organization_we_vote_id
        #  and describe what we will be updating.

    # These three parameters are needed to look up in ContestOffice table for a match
    if keep_looking_for_duplicates:
        if not positive_value_exists(contest_office_name) or not positive_value_exists(state_code) or not \
                positive_value_exists(google_civic_election_id):
            kind_of_action = TO_BE_DETERMINED
            batch_row_action_contest_office_status += "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_CONTEST_OFFICE_CREATE "
            keep_looking_for_duplicates = False

    # These three parameters are needed to look up in ContestOffice table for a match
    if keep_looking_for_duplicates:
        try:
            contest_office_query = ContestOffice.objects.all()
            # TODO Is there a way to filter with "dash" insensitivity? - vs --
            contest_office_query = contest_office_query.filter(office_name__iexact=contest_office_name,
                                                               state_code__iexact=state_code,
                                                               google_civic_election_id=google_civic_election_id)

            contest_office_item_list = list(contest_office_query)
            if len(contest_office_item_list):
                keep_looking_for_duplicates = False
                batch_row_action_contest_office_status += 'CREATE_BATCH_ROW_ACTION_CONTEST_OFFICE-ROW_RETRIEVED '
                # if a single entry matches, update that entry
                if len(contest_office_item_list) == 1:
                    kind_of_action = ADD_TO_EXISTING
                    contest_office_we_vote_id = contest_office_query.first().we_vote_id
                else:
                    # more than one entry found with a match in ContestOffice
                    kind_of_action = DO_NOT_PROCESS
            else:
                # Existing entry couldn't be found in the contest office table. We should keep looking for
                #  close matches
                pass
        except ContestOffice.DoesNotExist:
            # Existing entry couldn't be found in the contest office table. We should keep looking for
            #  close matches
            pass

    # TODO To build
    # if keep_looking_for_duplicates:
    #     # Check to see if we have a BatchRowTranslationMap for the value in contest_office_name
    #     kind_of_batch = CONTEST_OFFICE
    #     batch_row_name = "contest_office_name"
    #     incoming_batch_row_value = contest_office_name
    #     mapped_value = batch_manager.fetch_batch_row_translation_map(kind_of_batch, batch_row_name,
    #                                                                  incoming_batch_row_value)
    #     if positive_value_exists(mapped_value):
    #         # Replace existing value with the
    #         contest_office_name = mapped_value
    #         contest_office_name_mapped = True
    #         kind_of_action = ADD_TO_EXISTING
    #         keep_looking_for_duplicates = False
    #
    # if keep_looking_for_duplicates:
    #     # Are there similar office names that we might want to map this value to?
    #     kind_of_batch = CONTEST_OFFICE
    #     batch_row_name = "contest_office_name"
    #     incoming_batch_row_value = contest_office_name
    #     office_results = batch_manager.find_possible_matches(kind_of_batch, batch_row_name, incoming_batch_row_value,
    #                                                          google_civic_election_id, state_code)
    #     if office_results['possible_matches_found']:
    #         pass
    #
    #     kind_of_action = TO_BE_DETERMINED
    #     batch_row_action_contest_office_status += "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_CONTEST_OFFICE_CREATE "

    if keep_looking_for_duplicates:
        kind_of_action = CREATE
        batch_row_action_contest_office_status += "EXISTING_CONTEST_OFFICE_ENTRY_NOT_FOUND-CREATE "

    # Now save the data
    try:
        batch_row_action_contest_office.contest_office_name = contest_office_name
        # TODO batch_row_action_contest_office.contest_office_name_mapped = contest_office_name_mapped
        batch_row_action_contest_office.state_code = state_code
        batch_row_action_contest_office.elected_office_name = elected_office_name
        batch_row_action_contest_office.ctcl_uuid = ctcl_uuid
        batch_row_action_contest_office.number_voting_for = contest_office_votes_allowed
        batch_row_action_contest_office.number_elected = contest_office_number_elected
        batch_row_action_contest_office.kind_of_action = kind_of_action
        batch_row_action_contest_office.contest_office_we_vote_id = contest_office_we_vote_id
        batch_row_action_contest_office.google_civic_election_id = google_civic_election_id
        batch_row_action_contest_office.status = batch_row_action_contest_office_status
        batch_row_action_contest_office.candidate_selection_id1 = candidate_selection_id1
        batch_row_action_contest_office.candidate_selection_id2 = candidate_selection_id2
        batch_row_action_contest_office.candidate_selection_id3 = candidate_selection_id3
        batch_row_action_contest_office.candidate_selection_id4 = candidate_selection_id4
        batch_row_action_contest_office.candidate_selection_id5 = candidate_selection_id5
        batch_row_action_contest_office.candidate_selection_id6 = candidate_selection_id6
        batch_row_action_contest_office.candidate_selection_id7 = candidate_selection_id7
        batch_row_action_contest_office.candidate_selection_id8 = candidate_selection_id8
        batch_row_action_contest_office.candidate_selection_id9 = candidate_selection_id9
        batch_row_action_contest_office.candidate_selection_id10 = candidate_selection_id10
        batch_row_action_contest_office.save()
        success = True
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_CONTEST_OFFICE_UNABLE_TO_SAVE "

    results = {
        'success':                          success,
        'status':                           status,
        'new_action_contest_office_created':    new_action_contest_office_created,
        'action_contest_office_updated':        action_contest_office_updated,
        'batch_row_action_updated':         batch_row_action_updated,
        'batch_row_action_created':         batch_row_action_created,
        'batch_row_action_contest_office':  batch_row_action_contest_office,
    }
    return results


def create_batch_row_action_politician(batch_description, batch_header_map, one_batch_row):
    """
    Handle batch_row for politician type
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()

    new_action_politician_created = False
    action_politician_updated = False
    batch_row_action_politician_status = ''
    status = ''
    politician_we_vote_id = ''
    state_code = ''

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS

    # Find the column in the incoming batch_row with the header == politician_full_name
    politician_name = batch_manager.retrieve_value_from_batch_row("politician_full_name", batch_header_map,
                                                                  one_batch_row)
    # Find the column in the incoming batch_row with the header == ctcl_uuid
    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("politician_ctcl_uuid", batch_header_map, one_batch_row)
    politician_twitter_url = batch_manager.retrieve_value_from_batch_row("politician_twitter_url", batch_header_map,
                                                                         one_batch_row)
    facebook_id = batch_manager.retrieve_value_from_batch_row("politician_facebook_id", batch_header_map, one_batch_row)
    party_name = batch_manager.retrieve_value_from_batch_row("politician_party_name", batch_header_map, one_batch_row)
    first_name = batch_manager.retrieve_value_from_batch_row("politician_first_name", batch_header_map, one_batch_row)
    middle_name = batch_manager.retrieve_value_from_batch_row("politician_middle_name", batch_header_map, one_batch_row)
    last_name = batch_manager.retrieve_value_from_batch_row("politician_last_name", batch_header_map, one_batch_row)
    website_url = batch_manager.retrieve_value_from_batch_row("politician_website_url", batch_header_map, one_batch_row)
    email_address = batch_manager.retrieve_value_from_batch_row("politician_email_address", batch_header_map,
                                                                one_batch_row)
    youtube_id = batch_manager.retrieve_value_from_batch_row("politician_youtube_id", batch_header_map, one_batch_row)
    googleplus_id = batch_manager.retrieve_value_from_batch_row("politician_googleplus_id", batch_header_map,
                                                                one_batch_row)
    phone_number = batch_manager.retrieve_value_from_batch_row("politician_phone_number", batch_header_map,
                                                               one_batch_row)

    # extract twitter handle from politician_twitter_url
    politician_twitter_handle = extract_twitter_handle_from_text_string(politician_twitter_url)

    # BatchRowActionCandidate has personId which is politician id. Match id with personId from Candidate and get the
    # state_code from BatchRowActionCandidate
    person_id = batch_manager.retrieve_value_from_batch_row("politician_batch_id", batch_header_map, one_batch_row)
    # get batch_set_id from batch_description
    batch_set_id = batch_description.batch_set_id
    # Lookup BatchRowActionCandidate with matching batch_set_id and person_id and get state code
    state_code = batch_manager.fetch_state_code_from_person_id_in_candidate(person_id, batch_set_id)
    kind_of_action = 'TBD'
    single_politician_found = False
    multiple_politicians_found = False
    # First look up Politician table to see if an entry exists based on twitter_handle
    if positive_value_exists(politician_twitter_handle):
        try:
            politician_query = Politician.objects.all()
            politician_query = politician_query.filter(politician_twitter_handle__iexact=politician_twitter_handle)

            politician_item_list = list(politician_query)
            if len(politician_item_list):
                # entry exists
                batch_row_action_politician_status = 'BATCH_ROW_ACTION_POLITICIAN_RETRIEVED'
                batch_row_action_found = True
                new_action_politician_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(politician_item_list) == 1:
                    kind_of_action = ADD_TO_EXISTING
                    single_politician_found = True
                    politician_we_vote_id = politician_query.first().we_vote_id
                else:
                    # more than one entry found with a match in Politician
                    kind_of_action = 'DO_NOT_PROCESS'
                    multiple_politicians_found = True
            else:
                # kind_of_action = CREATE
                single_politician_found = False
        except Politician.DoesNotExist:
            batch_row_action_politician = BatchRowActionPolitician()
            batch_row_action_found = False
            # success = True
            batch_row_action_politician_status = "BATCH_ROW_ACTION_POLITICIAN_NOT_FOUND"
            kind_of_action = 'TBD'
    # twitter handle does not exist, next look up politician based on politician_name
    if not single_politician_found and not multiple_politicians_found and positive_value_exists(politician_name):
        try:
            politician_query = Politician.objects.all()
            politician_query = politician_query.filter(politician_name__iexact=politician_name)

            politician_item_list = list(politician_query)
            if len(politician_item_list):
                # entry exists
                batch_row_action_politician_status = 'BATCH_ROW_ACTION_POLITICIAN_RETRIEVED'
                batch_row_action_found = True
                new_action_politician_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(politician_item_list) == 1:
                    single_politician_found = True
                    kind_of_action = ADD_TO_EXISTING
                else:
                    # more than one entry found with a match in Politician
                    kind_of_action = 'DO_NOT_PROCESS'
                    multiple_politicians_found = True
            else:
                single_politician_found = False
        except Politician.DoesNotExist:
            batch_row_action_politician = BatchRowActionPolitician()
            single_politician_found = True
            batch_row_action_found = False
            # success = True
            batch_row_action_politician_status = "BATCH_ROW_ACTION_POLITICIAN_NOT_FOUND"
            kind_of_action = 'TBD'
    if not positive_value_exists(politician_name) and not positive_value_exists(politician_twitter_handle):
        kind_of_action = 'TBD'
        batch_row_action_politician_status = "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_POLITICIAN_CREATE"
    if not single_politician_found and not multiple_politicians_found:
        kind_of_action = CREATE

    try:
        # Check if politician_name, state_code match exists in BatchRowActionElectedOffice
        # for this header_id (Duplicate entries in the same data set
        existing_batch_row_action_politician_query = BatchRowActionPolitician.objects.all()
        existing_batch_row_action_politician_query = existing_batch_row_action_politician_query.filter(
            batch_header_id=batch_description.batch_header_id, politician_name__iexact=politician_name)
        existing_batch_row_action_politician_list = list(existing_batch_row_action_politician_query)
        number_of_existing_entries = len(existing_batch_row_action_politician_list)
        if not number_of_existing_entries:
            # no entry exists, create one
            updated_values = {
                'politician_name': politician_name,
                'first_name': first_name,
                'middle_name': middle_name,
                'last_name': last_name,
                'political_party': party_name,
                'ctcl_uuid': ctcl_uuid,
                'politician_email_address': email_address,
                'politician_phone_number': phone_number,
                'politician_twitter_handle': politician_twitter_handle,
                'politician_facebook_id': facebook_id,
                'politician_googleplus_id': googleplus_id,
                'politician_youtube_id': youtube_id,
                'politician_url': website_url,
                'kind_of_action': kind_of_action,
                'status': batch_row_action_politician_status,
                'politician_we_vote_id': politician_we_vote_id
            }

            batch_row_action_politician, new_action_politician_created = BatchRowActionPolitician.objects.\
                update_or_create(batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                                 defaults=updated_values)
            # new_action_politician_created = True
            success = True
            status += "CREATE_BATCH_ROW_ACTION_POLITICIAN-BATCH_ROW_ACTION_POLITICIAN_CREATED"
        else:
            # # if batch_header_id is same then it is a duplicate entry?
            existing_politician_entry = existing_batch_row_action_politician_query.first()
            if one_batch_row.id != existing_politician_entry.batch_row_id:
                # duplicate entry, create a new entry but set kind_of_action as DO_NOT_PROCESS and
                # set status as duplicate
                # kind_of_action = 'DO_NOT_PROCESS'
                updated_values = {
                    'politician_name': politician_name,
                    'first_name': first_name,
                    'middle_name': middle_name,
                    'last_name': last_name,
                    'political_party': party_name,
                    'ctcl_uuid': ctcl_uuid,
                    'politician_we_vote_id': politician_we_vote_id,
                    'politician_email_address': email_address,
                    'politician_phone_number': phone_number,
                    'politician_twitter_handle': politician_twitter_handle,
                    'politician_facebook_id': facebook_id,
                    'politician_googleplus_id': googleplus_id,
                    'politician_youtube_id': youtube_id,
                    'politician_url': website_url,
                    'kind_of_action': 'DO_NOT_PROCESS',
                    'status': 'DUPLICATE_ELECTED_OFFICE_ENTRY',
                }

                batch_row_action_politician, new_action_politician_created = \
                    BatchRowActionPolitician.objects.update_or_create(
                        batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                        defaults=updated_values)
                status += 'CREATE_BATCH_ROW_ACTION_POLITICIAN-BATCH_ROW_ACTION_POLITICIAN_DUPLICATE_ENTRIES'
                success = True
                action_politician_updated = True
                # this is a duplicate entry, mark it's kind_of_action as DO_NOT_PROCESS and status as duplicate
            else:
                # existing entry but not duplicate
                status += 'CREATE_BATCH_ROW_ACTION_POLITICIAN_ENTRY_EXISTS'
                success = True
                batch_row_action_politician = existing_politician_entry
    except Exception as e:
        batch_row_action_politician = BatchRowActionPolitician()
        batch_row_action_found = False
        success = False
        new_action_politician_created = False
        status = "CREATE_BATCH_ROW_ACTION_POLITICIAN-BATCH_ROW_ACTION_POLITICIAN_RETRIEVE_ERROR"
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success':                          success,
        'status':                           status,
        'new_action_politician_created':    new_action_politician_created,
        'action_politician_updated':        action_politician_updated,
        'batch_row_action_politician':      batch_row_action_politician,
    }
    return results


def create_batch_row_action_candidate(batch_description, batch_header_map, one_batch_row):
    """
    Handle batch_row for candidate
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()

    new_action_candidate_created = False
    action_candidate_updated = False
    state_code = ''
    batch_row_action_candidate_status = ''
    candidate_we_vote_id = ''
    success = False
    status = ''

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES

    # Find the column in the incoming batch_row with the header == candidate_name
    candidate_name = batch_manager.retrieve_value_from_batch_row("candidate_name", batch_header_map, one_batch_row)
    google_civic_election_id = str(batch_description.google_civic_election_id)

    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("candidate_ctcl_uuid", batch_header_map, one_batch_row)

    candidate_person_id = batch_manager.retrieve_value_from_batch_row("candidate_person_id", batch_header_map,
                                                                      one_batch_row)
    candidate_is_top_ticket = batch_manager.retrieve_value_from_batch_row("candidate_is_top_ticket", batch_header_map,
                                                                          one_batch_row)
    candidate_party_name = batch_manager.retrieve_value_from_batch_row("candidate_party_name", batch_header_map,
                                                                       one_batch_row)
    candidate_temp_id = batch_manager.retrieve_value_from_batch_row("candidate_batch_id", batch_header_map,
                                                                    one_batch_row)

    # get batch_set_id from batch_description
    batch_set_id = str(batch_description.batch_set_id)
    # Look up batch_description with the given batch_set_id and kind_of_batch as CONTEST_OFFICE, get batch_header_id
    batch_header_id = get_batch_header_id_from_batch_description(batch_set_id, CONTEST_OFFICE)

    # state code look up: BatchRowActionContestOffice entry stores candidate_selection_ids.
    #  Get the state code from matching
    # candidate_selection_id BatchRowActionContestOffice entry. Eg: looking for 'can1' in candidate_selection_ids 1-10
    try:
        batch_row_action_contest_office_query = BatchRowActionContestOffice.objects.all()
        batch_row_action_contest_office_query = batch_row_action_contest_office_query.filter(
            Q(batch_header_id=batch_header_id) & Q(candidate_selection_id1=candidate_temp_id) |
            Q(candidate_selection_id2=candidate_temp_id) | Q(candidate_selection_id3=candidate_temp_id) |
            Q(candidate_selection_id4=candidate_temp_id) | Q(candidate_selection_id5=candidate_temp_id) |
            Q(candidate_selection_id6=candidate_temp_id) | Q(candidate_selection_id7=candidate_temp_id) |
            Q(candidate_selection_id8=candidate_temp_id) | Q(candidate_selection_id9=candidate_temp_id) |
            Q(candidate_selection_id10=candidate_temp_id))
        batch_row_action_contest_office_list = list(batch_row_action_contest_office_query)
        if len(batch_row_action_contest_office_list):
            state_code = batch_row_action_contest_office_query.first().state_code
    except BatchRowActionContestOffice.DoesNotExist:
        status = "BATCH_ROW_ACTION_CANDIDATE-CONTEST_OFFICE_NOT_FOUND"
        pass
    # Look up CandidateCampaign to see if an entry exists
    # These three parameters are needed to look up in ElectedOffice table for a match
    if positive_value_exists(candidate_name) and positive_value_exists(google_civic_election_id) and \
            positive_value_exists(state_code):
        try:
            candidate_query = CandidateCampaign.objects.all()
            candidate_query = candidate_query.filter(candidate_name__iexact=candidate_name,
                                                     state_code__iexact=state_code,
                                                     google_civic_election_id=google_civic_election_id)

            candidate_item_list = list(candidate_query)
            if len(candidate_item_list):
                # entry exists
                batch_row_action_candidate_status = 'CANDIDATE_ENTRY_EXISTS'
                batch_row_action_found = True
                new_action_candidate_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(candidate_item_list) == 1:
                    kind_of_action = ADD_TO_EXISTING
                    candidate_we_vote_id = candidate_query.first().we_vote_id
                else:
                    # more than one entry found with a match in CandidateCampaign
                    kind_of_action = 'DO_NOT_PROCESS'
                    # candidate_we_vote_id = candidate_item_list.values('candidate_we_vote_id')
            else:
                kind_of_action = CREATE
        except CandidateCampaign.DoesNotExist:
            batch_row_action_candidate = BatchRowActionCandidate()
            batch_row_action_found = False
            # success = True
            batch_row_action_candidate_status = "BATCH_ROW_ACTION_CANDIDATE_NOT_FOUND"
            kind_of_action = 'TBD'
    else:
        kind_of_action = 'TBD'
        batch_row_action_candidate_status = "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_CANDIDATE_CREATE"
    # Create a new entry in BatchRowActionCandidate
    try:

        # Check if candidate_name match exists in BatchRowActionCandidate
        # for this header_id (Duplicate entries in the same data set
        existing_batch_row_action_candidate_query = BatchRowActionCandidate.objects.all()
        existing_batch_row_action_candidate_query = existing_batch_row_action_candidate_query.filter(
            batch_header_id=batch_description.batch_header_id, candidate_name__iexact=candidate_name,
            state_code__iexact=state_code, google_civic_election_id=google_civic_election_id)
        existing_batch_row_action_candidate_list = list(existing_batch_row_action_candidate_query)
        number_of_existing_entries = len(existing_batch_row_action_candidate_list)
        if not number_of_existing_entries:
            # no entry exists, create one
            updated_values = {
                'candidate_name': candidate_name,
                'candidate_person_id': candidate_person_id,
                'ctcl_uuid': ctcl_uuid,
                'state_code': state_code,
                'candidate_is_top_ticket': candidate_is_top_ticket,
                'candidate_we_vote_id': candidate_we_vote_id,
                'kind_of_action': kind_of_action,
                'google_civic_election_id': google_civic_election_id,
                'status': batch_row_action_candidate_status,
                'party': candidate_party_name,
            }

            batch_row_action_candidate, new_action_candidate_created = BatchRowActionCandidate.objects.\
                update_or_create(batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                                 defaults=updated_values)
            success = True
            status += "CREATE_BATCH_ROW_ACTION_CANDIDATE-BATCH_ROW_ACTION_CANDIDATE_CREATED"
        else:
            # # if batch_header_id is same then it is a duplicate entry?
            existing_candidate_entry = existing_batch_row_action_candidate_query.first()
            if one_batch_row.id != existing_candidate_entry.batch_row_id:
                # duplicate entry, create a new entry but set kind_of_action as DO_NOT_PROCESS and
                # set status as duplicate
                # kind_of_action = 'DO_NOT_PROCESS'
                updated_values = {
                    'candidate_name': candidate_name,
                    'candidate_person_id': candidate_person_id,
                    'ctcl_uuid': ctcl_uuid,
                    'state_code': state_code,
                    'candidate_is_top_ticket': candidate_is_top_ticket,
                    'candidate_we_vote_id': candidate_we_vote_id,
                    'kind_of_action': 'DO_NOT_PROCESS',
                    'google_civic_election_id': google_civic_election_id,
                    'status': 'DUPLICATE_CANDIDATE_ENTRY',
                    'party': candidate_party_name,
                }

                batch_row_action_candidate, new_action_candidate_created = \
                    BatchRowActionCandidate.objects.update_or_create(
                        batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                        defaults=updated_values)
                status += 'CREATE_BATCH_ROW_ACTION_CANDIDATE-BATCH_ROW_ACTION_CANDIDATE_DUPLICATE_ENTRIES'
                success = True
                action_candidate_updated = True
                # this is a duplicate entry, mark it's kind_of_action as DO_NOT_PROCESS and status as duplicate
            else:
                # existing entry but not duplicate
                status += 'BATCH_ROW_ACTION_CANDIDATE_ENTRY_EXISTS'
                success = True
                batch_row_action_candidate = existing_candidate_entry
    except Exception as e:
        batch_row_action_candidate = BatchRowActionCandidate()
        batch_row_action_found = False
        success = False
        new_action_candidate_created = False
        status = "CREATE_BATCH_ROW_ACTION_CANDIDATE_BATCH_ROW_ACTION_CANDIDATE_RETRIEVE_ERROR"
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success':                      success,
        'status':                       status,
        'new_action_candidate_created': new_action_candidate_created,
        'action_candidate_updated':     action_candidate_updated,
        'batch_row_action_candidate':   batch_row_action_candidate,
    }
    return results


def create_batch_row_action_position(batch_description, batch_header_map, one_batch_row):  # TODO DALE Convert to position
    """

    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()
    success = False
    status = ""
    batch_row_action_updated = False
    batch_row_action_created = False
    kind_of_action = ""

    # Does a BatchRowActionOrganization entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_organization(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_organization = existing_results['batch_row_action_organization']
        batch_row_action_updated = True
    else:
        # If a BatchRowActionOrganization entry does not exist, create one
        try:
            batch_row_action_organization = BatchRowActionOrganization.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
            )
            batch_row_action_created = True
            success = True
            status = "BATCH_ROW_ACTION_ORGANIZATION_CREATED"
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_organization = BatchRowActionOrganization()
            success = False
            status = "BATCH_ROW_ACTION_ORGANIZATION_NOT_CREATED"

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_organization': batch_row_action_organization,
            }
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS

    # Find the column in the incoming batch_row with the header title specified (ex/ "organization_name"
    organization_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "organization_we_vote_id", batch_header_map, one_batch_row)
    organization_name = batch_manager.retrieve_value_from_batch_row(
        "organization_name", batch_header_map, one_batch_row)
    organization_twitter_handle_raw = batch_manager.retrieve_value_from_batch_row(
        "organization_twitter_handle", batch_header_map, one_batch_row)
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle_raw)
    organization_facebook = batch_manager.retrieve_value_from_batch_row(
        "organization_facebook", batch_header_map, one_batch_row)
    organization_instagram = batch_manager.retrieve_value_from_batch_row(
        "organization_instagram", batch_header_map, one_batch_row)
    organization_website = batch_manager.retrieve_value_from_batch_row(
        "organization_website", batch_header_map, one_batch_row)
    organization_phone1 = batch_manager.retrieve_value_from_batch_row(
        "organization_phone1", batch_header_map, one_batch_row)
    organization_address = batch_manager.retrieve_value_from_batch_row(
        "organization_address", batch_header_map, one_batch_row)
    organization_city = batch_manager.retrieve_value_from_batch_row(
        "organization_city", batch_header_map, one_batch_row)
    organization_state = batch_manager.retrieve_value_from_batch_row(
        "organization_state", batch_header_map, one_batch_row)
    organization_zip = batch_manager.retrieve_value_from_batch_row(
        "organization_zip", batch_header_map, one_batch_row)
    state_served_code = batch_manager.retrieve_value_from_batch_row("state_served_code", batch_header_map, one_batch_row)
    organization_type = batch_manager.retrieve_value_from_batch_row(
        "organization_type", batch_header_map, one_batch_row)
    organization_contact_name = batch_manager.retrieve_value_from_batch_row(
        "organization_contact_name", batch_header_map, one_batch_row)

    # Now check for warnings (like "this is a duplicate"). If warnings are found,
    # add the warning to batch_row_action_organization entry
    # batch_row_action_organization.kind_of_action = "TEST"
    keep_looking_for_duplicates = True
    if positive_value_exists(organization_we_vote_id):
        # If here, then we are updating an existing known record
        keep_looking_for_duplicates = False
        kind_of_action = ADD_TO_EXISTING
        # TODO We want to search the Organization table for the existing record with this organization_we_vote_id
        #  and describe what we will be updating.

    if keep_looking_for_duplicates and positive_value_exists(organization_twitter_handle):
        try:
            organization_query = Organization.objects.all()
            organization_query = organization_query.filter(
                organization_twitter_handle__iexact=organization_twitter_handle)

            organization_list = list(organization_query)
            if len(organization_list):
                # At least one entry exists
                status += 'BATCH_ROW_ACTION_ORGANIZATION_LIST_RETRIEVED '
                batch_row_action_found = True
                # if a single entry matches, update that entry
                if len(organization_list) == 1:
                    kind_of_action = ADD_TO_EXISTING
                    single_entry_found = True
                    multiple_entries_found = False
                    organization_we_vote_id = organization_list.first().we_vote_id
                else:
                    # more than one entry found with a match in Organization
                    kind_of_action = CLEAN_DATA_MANUALLY
                    single_entry_found = False
                    multiple_entries_found = True
                    keep_looking_for_duplicates = False  # Deal with multiple Twitter duplicates manually
            else:
                kind_of_action = CREATE
                single_entry_found = False
        except Organization.DoesNotExist:
            batch_row_action_found = False
            # success = True
            status += "BATCH_ROW_ACTION_EXISTING_ORGANIZATION_NOT_FOUND "
            kind_of_action = TO_BE_DETERMINED  # We want to use other criteria to see if there is a duplicate
        except Exception as e:
            keep_looking_for_duplicates = False
            kind_of_action = QUERY_ERROR
            pass
    # twitter handle does not exist, next look up against other data that might match

    # Transform data to our constants: BatchRowTranslationMap
    # ORGANIZATION_TYPE_CHOICES = (
    #     (NONPROFIT_501C3, 'Nonprofit 501c3'),
    #     (NONPROFIT_501C4, 'Nonprofit 501c4'),
    #     (POLITICAL_ACTION_COMMITTEE, 'Political Action Committee'),
    #     (CORPORATION, 'Corporation'),
    #     (NEWS_CORPORATION, 'News Corporation'),
    #     (UNKNOWN, 'Unknown'),
    # )
    organization_type_transformed = UNKNOWN  # Default to this
    if organization_type.lower() == "c3":
        organization_type_transformed = NONPROFIT_501C3
    elif organization_type.lower() == "c4":
        organization_type_transformed = NONPROFIT_501C4

    try:
        batch_row_action_organization.organization_we_vote_id = organization_we_vote_id
        batch_row_action_organization.organization_name = organization_name
        batch_row_action_organization.organization_twitter_handle = organization_twitter_handle
        batch_row_action_organization.organization_facebook = organization_facebook
        batch_row_action_organization.organization_instagram_handle = organization_instagram
        batch_row_action_organization.organization_website = organization_website
        batch_row_action_organization.organization_phone1 = organization_phone1
        batch_row_action_organization.organization_address = organization_address
        batch_row_action_organization.organization_city = organization_city
        batch_row_action_organization.organization_state = organization_state
        batch_row_action_organization.organization_zip = organization_zip
        batch_row_action_organization.state_served_code = state_served_code
        batch_row_action_organization.organization_type = organization_type_transformed
        batch_row_action_organization.organization_contact_name = organization_contact_name
        batch_row_action_organization.kind_of_action = kind_of_action
        batch_row_action_organization.save()
        success = True
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_ORGANIZATION_UNABLE_TO_SAVE "

    results = {
        'success': success,
        'status': status,
        'batch_row_action_created': batch_row_action_created,
        'batch_row_action_updated': batch_row_action_updated,
        'batch_row_action_organization': batch_row_action_organization,
    }
    return results


def import_elected_office_data_from_batch_row_actions(batch_header_id, batch_row_id, create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for elected office, CREATE or ADD_TO_EXISTING
    Process batch row entries in order to create or update ElectedOffice entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for CREATE
    :param update_entry_flag: set to True for ADD_TO_EXISTING
    :return: 
    """
    success = False
    status = ""
    number_of_elected_offices_created = 0
    number_of_elected_offices_updated = 0
    kind_of_batch = ""
    new_elected_office = ''
    new_elected_office_created = False
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_ELECTED_OFFICE_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_elected_offices_created':    number_of_elected_offices_created,
            'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
        return results

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    if not batch_description_found:
        status += "IMPORT_ELECTED_OFFICE_ENTRY-BATCH_DESCRIPTION_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_elected_offices_created':    number_of_elected_offices_created,
            'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
        return results

        # kind_of_batch = batch_description.kind_of_batch

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()
        batch_header_map_found = False

    if not batch_header_map_found:
        status += "IMPORT_ELECTED_OFFICE_ENTRY-BATCH_HEADER_MAP_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_elected_offices_created':    number_of_elected_offices_created,
            'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
        return results

    batch_row_list_found = False
    try:
        batch_row_action_list = BatchRowActionElectedOffice.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=CREATE)
            kind_of_action = CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=ADD_TO_EXISTING)
            kind_of_action = ADD_TO_EXISTING
        else:
            # error handling
            status += "IMPORT_ELECTED_OFFICE_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                              success,
                'status':                               status,
                'number_of_elected_offices_created':    number_of_elected_offices_created,
                'number_of_elected_offices_updated':    number_of_elected_offices_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionElectedOffice.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    # batch_manager = BatchManager()

    if not batch_row_action_list_found:
        status += "IMPORT_ELECTED_OFFICE_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_elected_offices_created':    number_of_elected_offices_created,
            'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
        return results

    for one_batch_row_action in batch_row_action_list:

        # Find the column in the incoming batch_row with the header == elected_office_name
        elected_office_name = one_batch_row_action.elected_office_name
        elected_office_name_es = one_batch_row_action.elected_office_name_es
        google_civic_election_id = str(batch_description.google_civic_election_id)
        ctcl_uuid = one_batch_row_action.ctcl_uuid
        elected_office_description = one_batch_row_action.elected_office_description
        elected_office_description_es = one_batch_row_action.elected_office_description_es
        elected_office_is_partisan = one_batch_row_action.elected_office_is_partisan
        state_code = one_batch_row_action.state_code

        # Look up ElectedOffice to see if an entry exists
        # These five parameters are needed to look up in ElectedOffice table for a match
        if (positive_value_exists(elected_office_name) or positive_value_exists(elected_office_name_es)) and \
                positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
            elected_office_manager = ElectedOfficeManager()
            if create_entry_flag:
                results = elected_office_manager.create_elected_office_row_entry(elected_office_name, state_code,
                                                                                 elected_office_description, ctcl_uuid,
                                                                                 elected_office_is_partisan,
                                                                                 google_civic_election_id,
                                                                                 elected_office_name_es,
                                                                                 elected_office_description_es)
                if results['new_elected_office_created']:
                    number_of_elected_offices_created += 1
                    success = True
                    # now update BatchRowActionElectedOffice table entry
                    try:
                        one_batch_row_action.kind_of_action = ADD_TO_EXISTING
                        new_elected_office = results['new_elected_office']
                        one_batch_row_action.elected_office_we_vote_id = new_elected_office.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "ELECTED_OFFICE_RETRIEVE_ERROR"
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                elected_office_we_vote_id = one_batch_row_action.elected_office_we_vote_id
                results = elected_office_manager.update_elected_office_row_entry(elected_office_name,
                                                                                 state_code, elected_office_description,
                                                                                 ctcl_uuid, elected_office_is_partisan,
                                                                                 google_civic_election_id,
                                                                                 elected_office_we_vote_id,
                                                                                 elected_office_name_es,
                                                                                 elected_office_description_es)
                if results['elected_office_updated']:
                    number_of_elected_offices_updated += 1
                    success = True
            else:
                # This is error, it shouldn't reach here, we are handling CREATE or UPDATE entries only.
                status += "IMPORT_ELECTED_OFFICE_ENTRY:NO_CREATE_OR_UPDATE_ERROR"
                results = {
                    'success':                              success,
                    'status':                               status,
                    'number_of_elected_offices_created':    number_of_elected_offices_created,
                    'number_of_elected_offices_updated':    number_of_elected_offices_updated,
                    'new_elected_office':                   new_elected_office,
                }
                return results

    if number_of_elected_offices_created:
        status += "IMPORT_ELECTED_OFFICE_ENTRY:ELECTED_OFFICE_CREATED"
    elif number_of_elected_offices_updated:
        status += "IMPORT_ELECTED_OFFICE_ENTRY:ELECTED_OFFICE_UPDATED"

    results = {
        'success':                              success,
        'status':                               status,
        'number_of_elected_offices_created':    number_of_elected_offices_created,
        'number_of_elected_offices_updated':    number_of_elected_offices_updated,
        'new_elected_office':                   new_elected_office,
    }
    return results


def create_or_update_batch_header_mapping(batch_header_id, kind_of_batch, incoming_header_map_values):
    success = False
    status = ""

    # Filter out header values that aren't We Vote approved
    if kind_of_batch == CANDIDATE:
        modified_header_map_values = incoming_header_map_values
    elif kind_of_batch == CONTEST_OFFICE:
        modified_header_map_values = incoming_header_map_values
    elif kind_of_batch == ELECTED_OFFICE:
        modified_header_map_values = incoming_header_map_values
    elif kind_of_batch == MEASURE:
        modified_header_map_values = incoming_header_map_values
    elif kind_of_batch == ORGANIZATION_WORD:
        modified_header_map_values = incoming_header_map_values
    elif kind_of_batch == POLITICIAN:
        modified_header_map_values = incoming_header_map_values
    elif kind_of_batch == POSITION:
        modified_header_map_values = incoming_header_map_values
    else:
        modified_header_map_values = incoming_header_map_values

    try:
        batch_header_map, created = BatchHeaderMap.objects.update_or_create(
            batch_header_id=batch_header_id, defaults=modified_header_map_values)
        success = True
        status += "BATCH_HEADER_MAP_SAVED "
    except Exception as e:
        success = False
        status += "BATCH_HEADER_MAP_SAVE_FAILED "

    results = {
        'success':                              success,
        'status':                               status,
    }
    return results


def create_batch_header_translation_suggestions(batch_header, kind_of_batch, incoming_header_map_values):
    """

    :param batch_header:
    :param kind_of_batch:
    :param incoming_header_map_values:
    :return:
    """
    success = False
    status = ""
    suggestions_created = 0

    batch_manager = BatchManager()

    if kind_of_batch == CANDIDATE:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES
    elif kind_of_batch == CONTEST_OFFICE:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES
    elif kind_of_batch == ELECTED_OFFICE:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_ELECTED_OFFICES
    elif kind_of_batch == MEASURE:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES
    elif kind_of_batch == ORGANIZATION_WORD:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS
    elif kind_of_batch == POLITICIAN:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS
    elif kind_of_batch == POSITION:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS
    else:
        kind_of_batch_recognized = False
        batch_import_keys_accepted_dict = {}

    if kind_of_batch_recognized:
        if incoming_header_map_values['batch_header_map_000'] in batch_import_keys_accepted_dict:
            # We deal with empty values and make values lowercase within this function
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_000'], batch_header.batch_header_column_000)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_001'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_001'], batch_header.batch_header_column_001)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_002'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_002'], batch_header.batch_header_column_002)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_003'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_003'], batch_header.batch_header_column_003)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_004'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_004'], batch_header.batch_header_column_004)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_005'] in batch_import_keys_accepted_dict:
            batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_005'], batch_header.batch_header_column_005)
        suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_006'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_006'], batch_header.batch_header_column_006)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_007'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_007'], batch_header.batch_header_column_007)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_008'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_008'], batch_header.batch_header_column_008)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_009'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_009'], batch_header.batch_header_column_009)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_010'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_010'], batch_header.batch_header_column_010)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_011'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_011'], batch_header.batch_header_column_011)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_012'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_012'], batch_header.batch_header_column_012)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_013'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_013'], batch_header.batch_header_column_013)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_014'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_014'], batch_header.batch_header_column_014)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_015'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_015'], batch_header.batch_header_column_015)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_016'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_016'], batch_header.batch_header_column_016)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_017'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_017'], batch_header.batch_header_column_017)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_018'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_018'], batch_header.batch_header_column_018)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_019'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_019'], batch_header.batch_header_column_019)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created
        if incoming_header_map_values['batch_header_map_020'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_020'], batch_header.batch_header_column_020)
            suggestions_created = suggestions_created + 1 if results['success'] else suggestions_created

    results = {
        'success':              success,
        'status':               status,
        'suggestions_created':  suggestions_created,
    }
    return results


def import_contest_office_data_from_batch_row_actions(batch_header_id, batch_row_id, create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for contest office, CREATE or ADD_TO_EXISTING
    Process batch row entries in order to create or update ContestOffice entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for CREATE
    :param update_entry_flag: set to True for ADD_TO_EXISTING
    :return: 
    """
    success = False
    status = ""
    number_of_contest_offices_created = 0
    number_of_contest_offices_updated = 0
    kind_of_batch = ""
    new_contest_office = ''
    new_contest_office_created = False
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_CONTEST_OFFICE_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_contest_offices_created':    number_of_contest_offices_created,
            'number_of_contest_offices_updated':    number_of_contest_offices_updated
        }
        return results

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    if not batch_description_found:
        status += "IMPORT_CONTEST_OFFICE_ENTRY-BATCH_DESCRIPTION_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_contest_offices_created':    number_of_contest_offices_created,
            'number_of_contest_offices_updated':    number_of_contest_offices_updated
        }
        return results

        # kind_of_batch = batch_description.kind_of_batch

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()
        batch_header_map_found = False

    if not batch_header_map_found:
        status += "IMPORT_CONTEST_OFFICE_ENTRY-BATCH_HEADER_MAP_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_contest_offices_created':    number_of_contest_offices_created,
            'number_of_contest_offices_updated':    number_of_contest_offices_updated
        }
        return results

    batch_row_list_found = False
    try:
        batch_row_action_list = BatchRowActionContestOffice.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=CREATE)
            kind_of_action = CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=ADD_TO_EXISTING)
            kind_of_action = ADD_TO_EXISTING
        else:
            # error handling
            status += "IMPORT_CONTEST_OFFICE_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                              success,
                'status':                               status,
                'number_of_contest_offices_created':    number_of_contest_offices_created,
                'number_of_contest_offices_updated':    number_of_contest_offices_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionContestOffice.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    # batch_manager = BatchManager()

    if not batch_row_action_list_found:
        status += "IMPORT_CONTEST_OFFICE_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_contest_offices_created':    number_of_contest_offices_created,
            'number_of_contest_offices_updated':    number_of_contest_offices_updated
        }
        return results

    for one_batch_row_action in batch_row_action_list:

        # Find the column in the incoming batch_row with the header == contest_office_name
        contest_office_name = one_batch_row_action.contest_office_name
        google_civic_election_id = str(batch_description.google_civic_election_id)
        ctcl_uuid = one_batch_row_action.ctcl_uuid
        contest_office_votes_allowed = one_batch_row_action.number_voting_for
        contest_office_number_elected = one_batch_row_action.number_elected
        state_code = one_batch_row_action.state_code

        # Look up ContestOffice to see if an entry exists
        # These five parameters are needed to look up in ContestOffice table for a match
        if positive_value_exists(contest_office_name) and positive_value_exists(state_code) and \
                positive_value_exists(google_civic_election_id):
            contest_office_manager = ContestOfficeManager()
            if create_entry_flag:
                results = contest_office_manager.create_contest_office_row_entry(contest_office_name,
                                                                                 contest_office_votes_allowed,
                                                                                 ctcl_uuid,
                                                                                 contest_office_number_elected,
                                                                                 google_civic_election_id, state_code)
                if results['new_contest_office_created']:
                    number_of_contest_offices_created += 1
                    success = True
                    # now update BatchRowActionContestOffice table entry
                    try:
                        one_batch_row_action.kind_of_action = ADD_TO_EXISTING
                        new_contest_office = results['new_contest_office']
                        one_batch_row_action.contest_office_we_vote_id = new_contest_office.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "CONTEST_OFFICE_RETRIEVE_ERROR"
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                contest_office_we_vote_id = one_batch_row_action.contest_office_we_vote_id
                results = contest_office_manager.update_contest_office_row_entry(contest_office_name,
                                                                                 contest_office_votes_allowed,
                                                                                 ctcl_uuid,
                                                                                 contest_office_number_elected,
                                                                                 contest_office_we_vote_id,
                                                                                 google_civic_election_id,
                                                                                 state_code)
                if results['contest_office_updated']:
                    number_of_contest_offices_updated += 1
                    success = True
            else:
                # This is error, it shouldn't reach here, we are handling CREATE or UPDATE entries only.
                status += "IMPORT_CONTEST_OFFICE_ENTRY:NO_CREATE_OR_UPDATE_ERROR"
                results = {
                    'success':                              success,
                    'status':                               status,
                    'number_of_contest_offices_created':    number_of_contest_offices_created,
                    'number_of_contest_offices_updated':    number_of_contest_offices_updated,
                    'new_contest_office':                   new_contest_office,
                }
                return results

    if number_of_contest_offices_created:
        status += "IMPORT_CONTEST_OFFICE_ENTRY:CONTEST_OFFICE_CREATED"
    elif number_of_contest_offices_updated:
        status += "IMPORT_CONTEST_OFFICE_ENTRY:CONTEST_OFFICE_UPDATED"

    results = {
        'success':                              success,
        'status':                               status,
        'number_of_contest_offices_created':    number_of_contest_offices_created,
        'number_of_contest_offices_updated':    number_of_contest_offices_updated,
        'new_contest_office':                   new_contest_office,
    }
    return results


def import_measure_data_from_batch_row_actions(batch_header_id, batch_row_id, create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for measure, CREATE or ADD_TO_EXISTING
    Process batch row entries in order to create or update contestmeasure entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for CREATE
    :param update_entry_flag: set to True for ADD_TO_EXISTING
    :return: 
    """
    success = False
    status = ""
    number_of_measures_created = 0
    number_of_measures_updated = 0
    kind_of_batch = ""
    new_measure = ''
    new_measure_created = False
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_MEASURE_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_measures_created':    number_of_measures_created,
            'number_of_measures_updated':    number_of_measures_updated
        }
        return results

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    if not batch_description_found:
        status += "IMPORT_MEASURE_ENTRY-BATCH_DESCRIPTION_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_measures_created':    number_of_measures_created,
            'number_of_measures_updated':    number_of_measures_updated
        }
        return results

        # kind_of_batch = batch_description.kind_of_batch

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()
        batch_header_map_found = False

    if not batch_header_map_found:
        status += "IMPORT_MEASURE_ENTRY-BATCH_HEADER_MAP_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_measures_created':    number_of_measures_created,
            'number_of_measures_updated':    number_of_measures_updated
        }
        return results

    batch_row_list_found = False
    try:
        batch_row_action_list = BatchRowActionMeasure.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=CREATE)
            kind_of_action = CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=ADD_TO_EXISTING)
            kind_of_action = ADD_TO_EXISTING
        else:
            # error handling
            status += "IMPORT_MEASURE_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                       success,
                'status':                        status,
                'number_of_measures_created':    number_of_measures_created,
                'number_of_measures_updated':    number_of_measures_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionMeasure.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    # batch_manager = BatchManager()

    if not batch_row_action_list_found:
        status += "IMPORT_MEASURE_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_measures_created':    number_of_measures_created,
            'number_of_measures_updated':    number_of_measures_updated
        }
        return results

    for one_batch_row_action in batch_row_action_list:

        # Find the column in the incoming batch_row with the header == elected_office_name
        measure_title = one_batch_row_action.measure_title
        measure_subtitle = one_batch_row_action.measure_subtitle
        google_civic_election_id = str(batch_description.google_civic_election_id)
        ctcl_uuid = one_batch_row_action.ctcl_uuid
        measure_text = one_batch_row_action.measure_text
        state_code = one_batch_row_action.state_code

        # Look up ContestMeasure to see if an entry exists
        # These five parameters are needed to look up in Measure table for a match
        if positive_value_exists(measure_title) and positive_value_exists(state_code) and \
                positive_value_exists(google_civic_election_id):
            contest_measure_manager = ContestMeasureManager()
            if create_entry_flag:
                results = contest_measure_manager.create_measure_row_entry(measure_title, measure_subtitle,
                                                                           measure_text, state_code, ctcl_uuid,
                                                                           google_civic_election_id)
                if results['new_measure_created']:
                    number_of_measures_created += 1
                    success = True
                    # now update BatchRowActionMeasure table entry
                    try:
                        one_batch_row_action.kind_of_action = ADD_TO_EXISTING
                        new_measure = results['new_measure']
                        one_batch_row_action.measure_we_vote_id = new_measure.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "MEASURE_RETRIEVE_ERROR"
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                measure_we_vote_id = one_batch_row_action.measure_we_vote_id
                results = contest_measure_manager.update_measure_row_entry(measure_title, measure_subtitle,
                                                                           measure_text, state_code, ctcl_uuid,
                                                                           google_civic_election_id, measure_we_vote_id)
                if results['measure_updated']:
                    number_of_measures_updated += 1
                    success = True
            else:
                # This is error, it shouldn't reach here, we are handling CREATE or UPDATE entries only.
                status += "IMPORT_MEASURE_ENTRY:NO_CREATE_OR_UPDATE_ERROR"
                results = {
                    'success':                      success,
                    'status':                       status,
                    'number_of_measures_created':   number_of_measures_created,
                    'number_of_measures_updated':   number_of_measures_updated,
                    'new_measure':                  new_measure,
                }
                return results

    if number_of_measures_created:
        status += "IMPORT_MEASURE_ENTRY:MEASURE_CREATED"
    elif number_of_measures_updated:
        status += "IMPORT_MEASURE_ENTRY:MEASURE_UPDATED"

    results = {
        'success':                       success,
        'status':                        status,
        'number_of_measures_created':    number_of_measures_created,
        'number_of_measures_updated':    number_of_measures_updated,
        'new_measure':                   new_measure,
    }
    return results


def import_candidate_data_from_batch_row_actions(batch_header_id, batch_row_id, create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for candidate, CREATE or ADD_TO_EXISTING
    Process batch row entries in order to create or update CandidateCampaign entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for CREATE
    :param update_entry_flag: set to True for ADD_TO_EXISTING
    :return: 
    """
    success = False
    status = ""
    number_of_candidates_created = 0
    number_of_candidates_updated = 0
    kind_of_batch = ""
    new_candidate = ''
    new_candidate_created = False
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_CANDIDATE_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_candidates_created':     number_of_candidates_created,
            'number_of_candidates_updated':     number_of_candidates_updated
        }
        return results

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    if not batch_description_found:
        status += "IMPORT_CANDIDATE_ENTRY-BATCH_DESCRIPTION_MISSING"
        results = {
            'success':                      success,
            'status':                       status,
            'number_of_candidates_created': number_of_candidates_created,
            'number_of_candidates_updated': number_of_candidates_updated
        }
        return results

        # kind_of_batch = batch_description.kind_of_batch

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()
        batch_header_map_found = False

    if not batch_header_map_found:
        status += "IMPORT_CANDIDATE_ENTRY-BATCH_HEADER_MAP_MISSING"
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_candidates_created':      number_of_candidates_created,
            'number_of_candidates_updated':      number_of_candidates_updated
        }
        return results

    batch_row_list_found = False
    try:
        batch_row_action_list = BatchRowActionCandidate.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=CREATE)
            kind_of_action = CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=ADD_TO_EXISTING)
            kind_of_action = ADD_TO_EXISTING
        else:
            # error handling
            status += "IMPORT_CANDIDATE_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_candidates_created':     number_of_candidates_created,
                'number_of_candidates_updated':     number_of_candidates_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionCandidate.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    # batch_manager = BatchManager()

    if not batch_row_action_list_found:
        status += "IMPORT_CANDIDATE_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_candidates_created':     number_of_candidates_created,
            'number_of_candidates_updated':     number_of_candidates_updated
        }
        return results

    for one_batch_row_action in batch_row_action_list:

        # Find the column in the incoming batch_row with the header == candidate_name
        candidate_name = one_batch_row_action.candidate_name
        candidate_person_id = one_batch_row_action.candidate_person_id
        google_civic_election_id = str(batch_description.google_civic_election_id)
        ctcl_uuid = one_batch_row_action.ctcl_uuid
        candidate_party_name = one_batch_row_action.party
        candidate_is_top_ticket = one_batch_row_action.candidate_is_top_ticket
        state_code = one_batch_row_action.state_code

        # Look up CandidateCampaign to see if an entry exists
        # These five parameters are needed to look up in CandidateCampaign table for a match
        if positive_value_exists(candidate_name) and positive_value_exists(google_civic_election_id) and \
                positive_value_exists(state_code):
            candidate_manager = CandidateCampaignManager()
            if create_entry_flag:
                results = candidate_manager.create_candidate_row_entry(candidate_name, candidate_party_name,
                                                                       candidate_is_top_ticket, ctcl_uuid,
                                                                       google_civic_election_id, state_code)
                if results['new_candidate_created']:
                    number_of_candidates_created += 1
                    success = True
                    # now update BatchRowActionCandidate table entry
                    try:
                        one_batch_row_action.kind_of_action = ADD_TO_EXISTING
                        new_candidate = results['new_candidate']
                        one_batch_row_action.candidate_we_vote_id = new_candidate.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "CANDIDATE_RETRIEVE_ERROR"
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                candidate_we_vote_id = one_batch_row_action.candidate_we_vote_id
                results = candidate_manager.update_candidate_row_entry(candidate_name,candidate_party_name,
                                                                            candidate_is_top_ticket, ctcl_uuid,
                                                                            google_civic_election_id, state_code,
                                                                            candidate_we_vote_id)
                if results['candidate_updated']:
                    number_of_candidates_updated += 1
                    success = True
            else:
                # This is error, it shouldn't reach here, we are handling CREATE or UPDATE entries only.
                status += "IMPORT_CANDIDATE_ENTRY:NO_CREATE_OR_UPDATE_ERROR"
                results = {
                    'success':                          success,
                    'status':                           status,
                    'number_of_candidates_created':     number_of_candidates_created,
                    'number_of_candidates_updated':     number_of_candidates_updated,
                    'new_candidate':                    new_candidate,
                }
                return results

    if number_of_candidates_created:
        status += "IMPORT_CANDIDATE_ENTRY:ELECTED_OFFICE_CREATED"
    elif number_of_candidates_updated:
        status += "IMPORT_CANDIDATE_ENTRY:CANDIDATE_UPDATED"

    results = {
        'success':                          success,
        'status':                           status,
        'number_of_candidates_created':     number_of_candidates_created,
        'number_of_candidates_updated':     number_of_candidates_updated,
        'new_candidate':                    new_candidate,
    }
    return results


def import_politician_data_from_batch_row_actions(batch_header_id, batch_row_id, create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for politician, CREATE or ADD_TO_EXISTING
    Process batch row entries in order to create or update Politician entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for CREATE
    :param update_entry_flag: set to True for ADD_TO_EXISTING
    :return: 
    """
    success = False
    status = ""
    number_of_politicians_created = 0
    number_of_politicians_updated = 0
    kind_of_batch = ""
    new_politician = ''
    new_politician_created = False
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_POLITICIAN_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_politicians_created':    number_of_politicians_created,
            'number_of_politicians_updated':    number_of_politicians_updated
        }
        return results

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    if not batch_description_found:
        status += "IMPORT_POLITICIAN_ENTRY-BATCH_DESCRIPTION_MISSING"
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_politicians_created':    number_of_politicians_created,
            'number_of_politicians_updated':    number_of_politicians_updated
        }
        return results

        # kind_of_batch = batch_description.kind_of_batch

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()
        batch_header_map_found = False

    if not batch_header_map_found:
        status += "IMPORT_POLITICIAN_ENTRY-BATCH_HEADER_MAP_MISSING"
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_politicians_created':    number_of_politicians_created,
            'number_of_politicians_updated':    number_of_politicians_updated
        }
        return results

    batch_row_list_found = False
    try:
        batch_row_action_list = BatchRowActionPolitician.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=CREATE)
            kind_of_action = CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=ADD_TO_EXISTING)
            kind_of_action = ADD_TO_EXISTING
        else:
            # error handling
            status += "IMPORT_POLITICIAN_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_politicians_created':    number_of_politicians_created,
                'number_of_politicians_updated':    number_of_politicians_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionPolitician.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    if not batch_row_action_list_found:
        status += "IMPORT_POLITICIAN_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_politicians_created':    number_of_politicians_created,
            'number_of_politicians_updated':    number_of_politicians_updated
        }
        return results

    for one_batch_row_action in batch_row_action_list:

        # Find the column in the incoming batch_row with the header == politician_name
        politician_name = one_batch_row_action.politician_name
        politician_first_name = one_batch_row_action.first_name
        politician_middle_name = one_batch_row_action.middle_name
        politician_last_name = one_batch_row_action.last_name
        ctcl_uuid = one_batch_row_action.ctcl_uuid
        political_party = one_batch_row_action.political_party
        politician_email_address = one_batch_row_action.politician_email_address
        politician_phone_number = one_batch_row_action.politician_phone_number
        politician_twitter_handle = one_batch_row_action.politician_twitter_handle
        politician_facebook_id = one_batch_row_action.politician_facebook_id
        politician_googleplus_id = one_batch_row_action.politician_googleplus_id
        politician_youtube_id = one_batch_row_action.politician_youtube_id
        politician_website_url = one_batch_row_action.politician_url

        # Look up Politician to see if an entry exists
        # Look up in Politician table for a match
        # TODO should below condition be OR or AND? In certain ctcl data sets, twitter_handle is not provided for
        # politician
        if positive_value_exists(politician_name) or positive_value_exists(politician_twitter_handle):
            politician_manager = PoliticianManager()
            if create_entry_flag:
                results = politician_manager.create_politician_row_entry(politician_name, politician_first_name,
                                                                         politician_middle_name, politician_last_name,
                                                                         ctcl_uuid, political_party,
                                                                         politician_email_address,
                                                                         politician_phone_number,
                                                                         politician_twitter_handle,
                                                                         politician_facebook_id,
                                                                         politician_googleplus_id,
                                                                         politician_youtube_id, politician_website_url)
                if results['new_politician_created']:
                    number_of_politicians_created += 1
                    success = True
                    # now update BatchRowActionPolitician table entry
                    try:
                        one_batch_row_action.kind_of_action = ADD_TO_EXISTING
                        new_politician = results['new_politician']
                        one_batch_row_action.politician_we_vote_id = new_politician.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "POLITICIAN_RETRIEVE_ERROR "
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                politician_we_vote_id = one_batch_row_action.politician_we_vote_id
                results = politician_manager.update_politician_row_entry(politician_name, politician_first_name,
                                                                         politician_middle_name, politician_last_name,
                                                                         ctcl_uuid,political_party,
                                                                         politician_email_address,
                                                                         politician_twitter_handle,
                                                                         politician_phone_number,
                                                                         politician_facebook_id,
                                                                         politician_googleplus_id,
                                                                         politician_youtube_id, politician_website_url,
                                                                         politician_we_vote_id)
                if results['politician_updated']:
                    number_of_politicians_updated += 1
                    success = True
            else:
                # This is error, it shouldn't reach here, we are handling CREATE or UPDATE entries only.
                status += "IMPORT_POLITICIAN_ENTRY:NO_CREATE_OR_UPDATE_ERROR"
                results = {
                    'success':                          success,
                    'status':                           status,
                    'number_of_politicians_created':    number_of_politicians_created,
                    'number_of_politicians_updated':    number_of_politicians_updated,
                    'new_politician':                   new_politician,
                }
                return results

    if number_of_politicians_created:
        status += "IMPORT_POLITICIAN_ENTRY:POLITICIAN_CREATED"
    elif number_of_politicians_updated:
        status += "IMPORT_POLITICIAN_ENTRY:POLITICIAN_UPDATED"

    results = {
        'success':                          success,
        'status':                           status,
        'number_of_politicians_created':    number_of_politicians_created,
        'number_of_politicians_updated':    number_of_politicians_updated,
        'new_politician':                   new_politician,
    }
    return results


def import_organization_data_from_batch_row_actions(
        batch_header_id, batch_row_id, create_entry_flag=False, update_entry_flag=False):
    success = False
    status = ""
    number_of_organizations_created = 0
    number_of_organizations_updated = 0
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_ORGANIZATION_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_organizations_created':    number_of_organizations_created,
            'number_of_organizations_updated':    number_of_organizations_updated
        }
        return results

    try:
        batch_row_action_list = BatchRowActionOrganization.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=CREATE)
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=ADD_TO_EXISTING)
        else:
            # error handling
            status += "IMPORT_ORGANIZATION_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_organizations_created':  number_of_organizations_created,
                'number_of_organizations_updated':  number_of_organizations_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionOrganization.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    if not batch_row_action_list_found:
        status += "IMPORT_ORGANIZATION_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_organizations_created':    number_of_organizations_created,
            'number_of_organizations_updated':    number_of_organizations_updated
        }
        return results

    if update_entry_flag:
        status += "ORGANIZATION_UPDATE_NOT_WORKING YET "

    organization_manager = OrganizationManager()
    twitter_user_manager = TwitterUserManager()
    for one_batch_row_action in batch_row_action_list:
        if create_entry_flag:
            twitter_link_to_organization_exists = False
            twitter_id_for_new_organization = 0
            temp_org_image = ""
            if one_batch_row_action.organization_twitter_handle:
                twitter_retrieve_results = \
                    twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
                        one_batch_row_action.organization_twitter_handle)
                if twitter_retrieve_results['twitter_link_to_organization_found']:
                    # twitter_link_to_organization = twitter_retrieve_results['twitter_link_to_organization']
                    twitter_link_to_organization_exists = True  # Twitter handle already taken
                else:
                    # If a twitter_link_to_organization is NOT found, we look up the twitter_id and use it when
                    #  creating the org so we pull over the twitter data (like twitter_description)
                    twitter_id_for_new_organization = twitter_user_manager.fetch_twitter_id_from_twitter_handle(
                        one_batch_row_action.organization_twitter_handle)

            results = organization_manager.create_organization(
                one_batch_row_action.organization_name, one_batch_row_action.organization_website,
                one_batch_row_action.organization_twitter_handle, one_batch_row_action.organization_email,
                one_batch_row_action.organization_facebook, temp_org_image, twitter_id_for_new_organization)

            if not results['organization_created']:
                continue

            number_of_organizations_created += 1
            organization = results['organization']
            success = True

            # now update BatchRowActionOrganization table entry
            try:
                one_batch_row_action.kind_of_action = ADD_TO_EXISTING
                one_batch_row_action.organization_we_vote_id = organization.we_vote_id
                one_batch_row_action.save()
            except Exception as e:
                success = False
                status += "BATCH_ROW_ACTION_ORGANIZATION_SAVE_ERROR "
                handle_exception(e, logger=logger, exception_message=status)

            if positive_value_exists(one_batch_row_action.organization_twitter_handle) and not \
                    twitter_link_to_organization_exists:
                # Create TwitterLinkToOrganization
                if not positive_value_exists(twitter_id_for_new_organization):
                    twitter_id_for_new_organization = twitter_user_manager.fetch_twitter_id_from_twitter_handle(
                        one_batch_row_action.organization_twitter_handle)
                if positive_value_exists(twitter_id_for_new_organization):
                    results = twitter_user_manager.create_twitter_link_to_organization(
                        twitter_id_for_new_organization, organization.we_vote_id)

            try:
                # Now update organization with additional fields
                organization.organization_instagram_handle = one_batch_row_action.organization_instagram_handle
                organization.organization_address = one_batch_row_action.organization_address
                organization.organization_city = one_batch_row_action.organization_city
                organization.organization_state = one_batch_row_action.organization_state
                organization.organization_zip = one_batch_row_action.organization_zip
                organization.organization_phone1 = one_batch_row_action.organization_phone1
                organization.organization_type = one_batch_row_action.organization_type
                organization.state_served_code = one_batch_row_action.state_served_code
                organization.organization_contact_name = one_batch_row_action.organization_contact_name
                organization.save()
            except Exception as e:
                pass
        elif update_entry_flag:
            pass
            # organization_we_vote_id = one_batch_row_action.organization_we_vote_id
            # results = organization_manager.update_organization_row_entry(organization_title, organization_subtitle,
            #                                                            organization_text, state_code, ctcl_uuid,
            #                                                         google_civic_election_id, organization_we_vote_id)
            # if results['organization_updated']:
            #     number_of_organizations_updated += 1
            #     success = True
        else:
            # This is error, it shouldn't reach here, we are handling CREATE or UPDATE entries only.
            status += "IMPORT_ORGANIZATION_ENTRY:NO_CREATE_OR_UPDATE_ERROR "
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_organizations_created':  number_of_organizations_created,
                'number_of_organizations_updated':  number_of_organizations_updated,
            }
            return results

    if number_of_organizations_created:
        status += "IMPORT_ORGANIZATION_ENTRY: ORGANIZATIONS_CREATED "
    elif number_of_organizations_updated:
        status += "IMPORT_ORGANIZATION_ENTRY: ORGANIZATIONS_UPDATED "

    results = {
        'success':                       success,
        'status':                        status,
        'number_of_organizations_created':    number_of_organizations_created,
        'number_of_organizations_updated':    number_of_organizations_updated,
    }
    return results


def import_position_data_from_batch_row_actions(  # TODO DALE Convert for positions
        batch_header_id, batch_row_id, create_entry_flag=False, update_entry_flag=False):
    success = False
    status = ""
    number_of_organizations_created = 0
    number_of_organizations_updated = 0
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_ORGANIZATION_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_organizations_created':    number_of_organizations_created,
            'number_of_organizations_updated':    number_of_organizations_updated
        }
        return results

    try:
        batch_row_action_list = BatchRowActionOrganization.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=CREATE)
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=ADD_TO_EXISTING)
        else:
            # error handling
            status += "IMPORT_ORGANIZATION_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_organizations_created':  number_of_organizations_created,
                'number_of_organizations_updated':  number_of_organizations_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionOrganization.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    if not batch_row_action_list_found:
        status += "IMPORT_ORGANIZATION_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_organizations_created':    number_of_organizations_created,
            'number_of_organizations_updated':    number_of_organizations_updated
        }
        return results

    if update_entry_flag:
        status += "ORGANIZATION_UPDATE_NOT_WORKING YET "

    organization_manager = OrganizationManager()
    twitter_user_manager = TwitterUserManager()
    for one_batch_row_action in batch_row_action_list:
        if create_entry_flag:
            twitter_link_to_organization_exists = False
            twitter_id_for_new_organization = 0
            temp_org_image = ""
            if one_batch_row_action.organization_twitter_handle:
                twitter_retrieve_results = \
                    twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
                        one_batch_row_action.organization_twitter_handle)
                if twitter_retrieve_results['twitter_link_to_organization_found']:
                    # twitter_link_to_organization = twitter_retrieve_results['twitter_link_to_organization']
                    twitter_link_to_organization_exists = True  # Twitter handle already taken
                else:
                    # If a twitter_link_to_organization is NOT found, we look up the twitter_id and use it when
                    #  creating the org so we pull over the twitter data (like twitter_description)
                    twitter_id_for_new_organization = twitter_user_manager.fetch_twitter_id_from_twitter_handle(
                        one_batch_row_action.organization_twitter_handle)

            results = organization_manager.create_organization(
                one_batch_row_action.organization_name, one_batch_row_action.organization_website,
                one_batch_row_action.organization_twitter_handle, one_batch_row_action.organization_email,
                one_batch_row_action.organization_facebook, temp_org_image, twitter_id_for_new_organization)

            if not results['organization_created']:
                continue

            number_of_organizations_created += 1
            organization = results['organization']
            success = True

            # now update BatchRowActionOrganization table entry
            try:
                one_batch_row_action.kind_of_action = ADD_TO_EXISTING
                one_batch_row_action.organization_we_vote_id = organization.we_vote_id
                one_batch_row_action.save()
            except Exception as e:
                success = False
                status += "BATCH_ROW_ACTION_ORGANIZATION_SAVE_ERROR "
                handle_exception(e, logger=logger, exception_message=status)

            if positive_value_exists(one_batch_row_action.organization_twitter_handle) and not \
                    twitter_link_to_organization_exists:
                # Create TwitterLinkToOrganization
                if not positive_value_exists(twitter_id_for_new_organization):
                    twitter_id_for_new_organization = twitter_user_manager.fetch_twitter_id_from_twitter_handle(
                        one_batch_row_action.organization_twitter_handle)
                if positive_value_exists(twitter_id_for_new_organization):
                    results = twitter_user_manager.create_twitter_link_to_organization(
                        twitter_id_for_new_organization, organization.we_vote_id)

            try:
                # Now update organization with additional fields
                organization.organization_instagram_handle = one_batch_row_action.organization_instagram_handle
                organization.organization_address = one_batch_row_action.organization_address
                organization.organization_city = one_batch_row_action.organization_city
                organization.organization_state = one_batch_row_action.organization_state
                organization.organization_zip = one_batch_row_action.organization_zip
                organization.organization_phone1 = one_batch_row_action.organization_phone1
                organization.organization_type = one_batch_row_action.organization_type
                organization.state_served_code = one_batch_row_action.state_served_code
                organization.organization_contact_name = one_batch_row_action.organization_contact_name
                organization.save()
            except Exception as e:
                pass
        elif update_entry_flag:
            pass
            # organization_we_vote_id = one_batch_row_action.organization_we_vote_id
            # results = organization_manager.update_organization_row_entry(organization_title, organization_subtitle,
            #                                                            organization_text, state_code, ctcl_uuid,
            #                                                         google_civic_election_id, organization_we_vote_id)
            # if results['organization_updated']:
            #     number_of_organizations_updated += 1
            #     success = True
        else:
            # This is error, it shouldn't reach here, we are handling CREATE or UPDATE entries only.
            status += "IMPORT_ORGANIZATION_ENTRY:NO_CREATE_OR_UPDATE_ERROR "
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_organizations_created':  number_of_organizations_created,
                'number_of_organizations_updated':  number_of_organizations_updated,
            }
            return results

    if number_of_organizations_created:
        status += "IMPORT_ORGANIZATION_ENTRY: ORGANIZATIONS_CREATED "
    elif number_of_organizations_updated:
        status += "IMPORT_ORGANIZATION_ENTRY: ORGANIZATIONS_UPDATED "

    results = {
        'success':                       success,
        'status':                        status,
        'number_of_organizations_created':    number_of_organizations_created,
        'number_of_organizations_updated':    number_of_organizations_updated,
    }
    return results


def import_create_or_update_elected_office_entry(batch_header_id, batch_row_id):
    """
    Either create or update ElectedOffice table entry with batch_row elected_office details 
    
    :param batch_header_id: 
    :param batch_row_id: 
    :return: 
    """
    success = False
    status = ""
    elected_office_updated = False
    new_elected_office_created = False
    new_elected_office = ''
    number_of_elected_offices_created = 0
    number_of_elected_offices_updated = 0
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status += "IMPORT_CREATE_OR_UPDATE_ELECTED_OFFICE_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_elected_offices_created':    number_of_elected_offices_created,
            'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
        return results

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    if not batch_description_found:
        status += "IMPORT_CREATE_OR_UPDATE_ELECTED_OFFICE_ENTRY-BATCH_DESCRIPTION_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_elected_offices_created':    number_of_elected_offices_created,
            'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
        return results

        # kind_of_batch = batch_description.kind_of_batch

    try:
        batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map = BatchHeaderMap()
        batch_header_map_found = False

    if not batch_header_map_found:
        status += "IMPORT_CREATE_OR_UPDATE_ELECTED_OFFICE_ENTRY-BATCH_HEADER_MAP_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_elected_offices_created':    number_of_elected_offices_created,
            'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
        return results

    batch_row_action_list_found = False
    try:
        batch_row_action_elected_office_list = BatchRowActionElectedOffice.objects.all()
        batch_row_action_elected_office_list = batch_row_action_elected_office_list.filter(
            batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_elected_office_list = batch_row_action_elected_office_list.filter(
                batch_row_id=batch_row_id)

        if len(batch_row_action_elected_office_list):
            batch_row_action_list_found = True
            # TODO assumption is that length of this list is going to be one, single record match
            batch_row_action_elected_office = batch_row_action_elected_office_list.first()
    except BatchRowActionElectedOffice.DoesNotExist:
        # batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    # batch_manager = BatchManager()

    if not batch_row_action_list_found:
        status += "IMPORT_CREATE_OR_UPDATE_ELECTED_OFFICE_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_elected_offices_created':    number_of_elected_offices_created,
            'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
        return results

    if batch_description_found and batch_header_map_found and batch_row_action_list_found:

        state_code = batch_row_action_elected_office.state_code
        elected_office_name = batch_row_action_elected_office.elected_office_name
        google_civic_election_id = str(batch_description.google_civic_election_id)
        ctcl_uuid = batch_row_action_elected_office.ctcl_uuid
        elected_office_description = batch_row_action_elected_office.elected_office_description
        elected_office_is_partisan = batch_row_action_elected_office.elected_office_is_partisan
        elected_office_name_es = batch_row_action_elected_office.elected_office_name_es
        elected_office_description_es = batch_row_action_elected_office.elected_office_description_es

        # Look up ElectedOffice to see if an entry exists

        kind_of_action = batch_row_action_elected_office.kind_of_action
        # Only add entries with kind_of_action set to either CREATE or ADD_TO_EXISTING.
        elected_office_manager = ElectedOfficeManager()
        if kind_of_action == CREATE:
            # call create_elected_office_row_entry
            results = elected_office_manager.create_elected_office_row_entry(elected_office_name, state_code,
                                                                             elected_office_description, ctcl_uuid,
                                                                             elected_office_is_partisan,
                                                                             google_civic_election_id)

            if results['new_elected_office_created']:
                success = True
                number_of_elected_offices_created += 1

                # now update BatchRowActionElectedOffice table entry
                try:
                    batch_row_action_elected_office.kind_of_action = ADD_TO_EXISTING
                    batch_row_action_elected_office.elected_office_we_vote_id = \
                        results['new_elected_office'].we_vote_id
                    batch_row_action_elected_office.save()
                except Exception as e:
                    success = False
                    new_elected_office_created = False
                    status += "IMPORT_UPDATE_OR_CREATE_ELECTED_OFFICE_ENTRY-ELECTED_OFFICE_RETRIEVE_ERROR"
                    handle_exception(e, logger=logger, exception_message=status)
        elif kind_of_action == ADD_TO_EXISTING:
            # call update_elected_office_row_entry
            elected_office_we_vote_id = batch_row_action_elected_office.elected_office_we_vote_id
            results = elected_office_manager.update_elected_office_row_entry(elected_office_name, state_code,
                                                                             elected_office_description,
                                                                             ctcl_uuid,
                                                                             elected_office_is_partisan,
                                                                             google_civic_election_id,
                                                                             elected_office_we_vote_id,
                                                                             elected_office_name_es,
                                                                             elected_office_description_es)
            if results['elected_office_updated']:
                success = True
                elected_office_updated = True
                number_of_elected_offices_updated += 1

            try:
                # store elected_we_vote_id from ElectedOffice table
                updated_elected_office = results['updated_elected_office']
                batch_row_action_elected_office.elected_office_we_vote_id = updated_elected_office.we_vote_id
                batch_row_action_elected_office.save()
            except Exception as e:
                success = False
                new_elected_office_created = False
                status += "IMPORT_CREATE_OR_UPDATE_ELECTED_OFFICE_ENTRY-ELECTED_OFFICE_RETRIEVE_ERROR"
                handle_exception(e, logger=logger, exception_message=status)
        else:
            # kind_of_action is either TBD or DO_NOT_PROCESS, do nothing
            success = True
            status = "IMPORT_CREATE_OR_UPDATE_ELECTED_OFFICE_ENTRY-ACTION_TBD_OR_DO_NOT_PROCESS"
    if number_of_elected_offices_created:
        status = "IMPORT_CREATE_OR_UPDATE_ELECTED_OFFICE_ENTRY-ELECTED_OFFICE_CREATED"
    elif number_of_elected_offices_updated:
        status = "IMPORT_CREATE_OR_UPDATE_ELECTED_OFFICE_ENTRY-ELECTED_OFFICE_UPDATED"
    results = {
        'success':                              success,
        'status':                               status,
        'new_elected_office_created':           new_elected_office_created,
        'elected_office_updated':               elected_office_updated,
        'new_elected_office':                   new_elected_office,
        'number_of_elected_offices_created':    number_of_elected_offices_created,
        'number_of_elected_offices_updated':    number_of_elected_offices_updated
        }
    return results


def import_data_from_batch_row_actions(kind_of_batch, kind_of_action, batch_header_id, batch_row_id=0):
    """
    Cycle through batch_row_action entries for one kind_of_batch + kind_of_action + batch_header_id, OR
    for one particular batch_row_id. The kind_of_action is either CREATE or ADD_TO_EXISTING.
    :param kind_of_batch:
    :param kind_of_action:
    :param batch_header_id:
    :param batch_row_id:
    :return:
    """
    success = False
    status = ''
    number_of_table_rows_created = 0
    number_of_table_rows_updated = 0
    create_flag = False
    update_flag = False

    # for one_batch_row in batch_row_list:
    if kind_of_action == CREATE:
        create_flag = True
    elif kind_of_action == ADD_TO_EXISTING:
        update_flag = True
    else:
        # this is error
        status += 'IMPORT_BATCH_ACTION_ROWS_INCORRECT_ACTION '
        results = {
            'success':                      success,
            'status':                       status,
            'batch_header_id':              batch_header_id,
            'kind_of_batch':                kind_of_batch,
            'table_rows_created':           success,
            'number_of_table_rows_created': number_of_table_rows_created,
            'number_of_table_rows_updated': number_of_table_rows_updated
        }
        return results

    if kind_of_batch == CANDIDATE:
        results = import_candidate_data_from_batch_row_actions(batch_header_id, batch_row_id, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_candidates_created']:
                # for now, do not handle batch_row_action_candidate data
                # batch_row_action_candidate = results['batch_row_action_candidate']
                number_of_table_rows_created = results['number_of_candidates_created']
            elif results['number_of_candidates_updated']:
                number_of_table_rows_updated = results['number_of_candidates_updated']
            success = True
    elif kind_of_batch == CONTEST_OFFICE:
        results = import_contest_office_data_from_batch_row_actions(
            batch_header_id, batch_row_id, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_contest_offices_created']:
                # for now, do not handle batch_row_action_contest_office data
                # batch_row_action_contest_office = results['batch_row_action_contest_office']
                number_of_table_rows_created = results['number_of_contest_offices_created']
            elif results['number_of_contest_offices_updated']:
                number_of_table_rows_updated = results['number_of_contest_offices_updated']
            success = True
    elif kind_of_batch == ELECTED_OFFICE:
        results = import_elected_office_data_from_batch_row_actions(
            batch_header_id, batch_row_id, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_elected_offices_created']:
                # for now, do not handle batch_row_action_elected_office data
                # batch_row_action_elected_office = results['batch_row_action_elected_office']
                number_of_table_rows_created = results['number_of_elected_offices_created']
            elif results['number_of_elected_offices_updated']:
                number_of_table_rows_updated = results['number_of_elected_offices_updated']
            success = True
    elif kind_of_batch == MEASURE:
        results = import_measure_data_from_batch_row_actions(batch_header_id, batch_row_id, create_flag,
                                                             update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_measures_created']:
                # for now, do not handle batch_row_action_measure data
                # batch_row_action_elected_office = results['batch_row_action_elected_office']
                number_of_table_rows_created = results['number_of_measures_created']
            elif results['number_of_measures_updated']:
                number_of_table_rows_updated = results['number_of_measures_updated']
            success = True
    elif kind_of_batch == ORGANIZATION_WORD:
        results = import_organization_data_from_batch_row_actions(
            batch_header_id, batch_row_id, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_organizations_created']:
                number_of_table_rows_created = results['number_of_organizations_created']
            elif results['number_of_organizations_updated']:
                number_of_table_rows_updated = results['number_of_organizations_updated']
            success = True
    elif kind_of_batch == POLITICIAN:
        results = import_politician_data_from_batch_row_actions(batch_header_id, batch_row_id, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_politicians_created']:
                # for now, do not handle batch_row_action_politician data
                # batch_row_action_politician = results['batch_row_action_politician']
                number_of_table_rows_created = results['number_of_politicians_created']
            elif results['number_of_politicians_updated']:
                number_of_table_rows_updated = results['number_of_politicians_updated']
            success = True
    elif kind_of_batch == POSITION:
        results = import_position_data_from_batch_row_actions(batch_header_id, batch_row_id, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_politicians_created']:
                # for now, do not handle batch_row_action_politician data
                # batch_row_action_politician = results['batch_row_action_politician']
                number_of_table_rows_created = results['number_of_politicians_created']
            elif results['number_of_politicians_updated']:
                number_of_table_rows_updated = results['number_of_politicians_updated']
            success = True

    results = {
        'success':                      success,
        'status':                       status,
        'batch_header_id':              batch_header_id,
        'kind_of_batch':                kind_of_batch,
        'table_rows_created':           success,
        'number_of_table_rows_created': number_of_table_rows_created,
        'number_of_table_rows_updated': number_of_table_rows_updated
    }
    return results


def get_batch_header_id_from_batch_description(batch_set_id, kind_of_batch):
    """
    Look up batch_description table for a given batch_set_id and kind_of_batch
    :param batch_set_id: 
    :param kind_of_batch: 
    :return: 
    """
    batch_header_id = 0
    try:
        if positive_value_exists(batch_set_id):
            batch_description_on_stage = BatchDescription.objects.get(batch_set_id=batch_set_id,
                                                                      kind_of_batch=kind_of_batch)
            if batch_description_on_stage:
                batch_header_id = batch_description_on_stage.batch_header_id
    except BatchDescription.DoesNotExist:
        pass

    return batch_header_id
