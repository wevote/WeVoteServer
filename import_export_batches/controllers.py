# import_export_batches/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from ballot.models import MEASURE, OFFICE, CANDIDATE, POLITICIAN
from candidate.models import CandidateCampaignManager
from config.base import get_environment_variable
import copy
from exception.models import handle_record_found_more_than_one_exception
from position.models import PositionManager, PERCENT_RATING
import requests
from voter_guide.models import ORGANIZATION_WORD
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from .models import BatchManager, BatchDescription, BatchHeaderMap, BatchRow, BatchRowActionOrganization, \
    BatchRowActionMeasure, BatchRowActionOffice
from measure.models import ContestMeasure
from office.models import ContestOffice
from electoral_district.controllers import retrieve_electoral_district
from exception.models import handle_exception

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
    status = ""
    number_of_batch_actions_created = 0
    kind_of_batch = ""

    if not positive_value_exists(batch_header_id):
        status = "CREATE_BATCH_ROW_ACTIONS-BATCH_HEADER_ID_MISSING"
        results = {
            'success': success,
            'status': status,
            'batch_header_id': batch_header_id,
            'kind_of_batch': kind_of_batch,
            'batch_actions_created': success,
            'number_of_batch_actions_created': number_of_batch_actions_created,
        }
        return results

    try:
        batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    if batch_description_found:
        kind_of_batch = batch_description.kind_of_batch

        try:
            batch_header_map = BatchHeaderMap.objects.get(batch_header_id=batch_header_id)
            batch_header_map_found = True
        except BatchHeaderMap.DoesNotExist:
            # This is fine
            batch_header_map = BatchHeaderMap()
            batch_header_map_found = False

    if batch_header_map_found:
        batch_row_list_found = False
        try:
            batch_row_list = BatchRow.objects.order_by('id')
            batch_row_list = batch_row_list.filter(batch_header_id=batch_header_id)
            if positive_value_exists(batch_row_id):
                batch_row_list = batch_row_list.filter(id=batch_row_id)

            if len(batch_row_list):
                batch_row_list_found = True
        except BatchDescription.DoesNotExist:
            # This is fine
            batch_row_list = []
            batch_row_list_found = False
            pass

    if batch_description_found and batch_header_map_found and batch_row_list_found:
        for one_batch_row in batch_row_list:
            if kind_of_batch == ORGANIZATION_WORD:
                batch_row_action_organization = BatchRowActionOrganization()
                # Does a BatchRowActionOrganization entry already exist?
                existing_results = batch_row_action_organization.retrieve_batch_row_action_organization(
                    batch_header_id, one_batch_row.id)
                if existing_results['batch_row_action_found']:
                    batch_row_action_organization = existing_results['batch_row_action_organization']
                else:
                    # If a BatchRowActionOrganization entry does not exist, create one
                    new_results = create_batch_row_action_organization(batch_description, batch_header_map,
                                                                       one_batch_row)
                    if new_results['batch_row_action_created']:
                        batch_row_action_organization = new_results['batch_row_action_organization']
                        number_of_batch_actions_created += 1
                    else:
                        # Move on to the next batch_row
                        continue
                # Now check for warnings (like "this is a duplicate"). If warnings are found,
                # add the warning to batch_row_action_organization entry
                # batch_row_action_organization.kind_of_action = "TEST"
                batch_row_action_organization.save()

            elif kind_of_batch == MEASURE:
                results = create_batch_row_action_measure(batch_description, batch_header_map, one_batch_row)

                if results['new_action_measure_created']:
                    # for now, do not handle batch_row_action_measure data
                    # batch_row_action_measure = results['batch_row_action_measure']
                    number_of_batch_actions_created += 1
                    success = True
            elif kind_of_batch == OFFICE:
                results = create_batch_row_action_office(batch_description, batch_header_map, one_batch_row)

                if results['new_action_office_created']:
                    # for now, do not handle batch_row_action_office data
                    # batch_row_action_office = results['batch_row_action_office']
                    number_of_batch_actions_created += 1
                    success = True

                # Now check for warnings (like "this is a duplicate"). If warnings are found,
                # add the warning to batch_row_action_measure entry
                # batch_row_action_measure.kind_of_action = "TEST"

    results = {
        'success': success,
        'status': status,
        'batch_header_id': batch_header_id,
        'kind_of_batch': kind_of_batch,
        'batch_actions_created': success,
        'number_of_batch_actions_created': number_of_batch_actions_created,
    }
    return results


def create_batch_row_action_organization(batch_description, batch_header_map, one_batch_row):
    batch_row_action_organization = BatchRowActionOrganization()
    # Find the column in the incoming batch_row with the header == organization_name
    organization_name = batch_row_action_organization.retrieve_value_from_batch_row("organization_name",
                                                                                    batch_header_map, one_batch_row)
    # Find the column in the incoming batch_row with the header == state_code
    state_served_code = batch_row_action_organization.retrieve_value_from_batch_row("state_code", batch_header_map,
                                                                                    one_batch_row)

    try:
        batch_row_action_organization = BatchRowActionOrganization.objects.create(
            batch_header_id=batch_description.batch_header_id,
            batch_row_id=one_batch_row.id,
            state_served_code=state_served_code,
            organization_name=organization_name,
        )
        batch_row_action_created = True
        success = True
        status = "BATCH_ROW_ACTION_ORGANIZATION_CREATED"
    except Exception as e:
        batch_row_action_created = False
        batch_row_action_organization = BatchRowActionOrganization()
        success = False
        status = "BATCH_ROW_ACTION_ORGANIZATION_NOT_CREATED"
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'batch_row_action_created': batch_row_action_created,
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
    state_code = ''
    batch_row_action_measure_status = ''

    # Find the column in the incoming batch_row with the header == measure_title
    measure_title = batch_manager.retrieve_value_from_batch_row("measure_title", batch_header_map, one_batch_row)
    # Find the column in the incoming batch_row with the header == state_code
    electoral_district_id = batch_manager.retrieve_value_from_batch_row("electoral_district_id", batch_header_map,
                                                                        one_batch_row)
    google_civic_election_id = str(batch_description.google_civic_election_id)

    results = retrieve_electoral_district(electoral_district_id)
    if results['electoral_district_found']:
        if results['state_code_found']:
            state_code = results['state_code']
            # state_code = results.values_list('state_code', flat=True).get()
    else:
        # state_code = ''
        batch_row_action_measure_status = 'ELECTORAL_DISTRICT_NOT_FOUND'
        kind_of_action = 'TBD'

    measure_text = batch_manager.retrieve_value_from_batch_row("measure_name",
                                                               batch_header_map,
                                                               one_batch_row)
    measure_subtitle = batch_manager.retrieve_value_from_batch_row("measure_sub_title",
                                                                   batch_header_map,
                                                                   one_batch_row)

    # Look up ContestMeasure to see if an entry exists
    contest_measure = ContestMeasure()
    # These three parameters are needed to look up in Contest Measure table for a match
    if positive_value_exists(measure_title) and positive_value_exists(state_code) and \
            positive_value_exists(google_civic_election_id):
        try:
            contest_measure_query = ContestMeasure.objects.order_by('id')
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
                    kind_of_action = 'ADD_TO_EXISTING'
                else:
                    # more than one entry found with a match in ContestMeasure
                    kind_of_action = 'DO_NOT_PROCESS'
            else:
                kind_of_action = 'CREATE'
        except ContestMeasure.DoesNotExist:
            batch_row_action_measure = BatchRowActionMeasure()
            # batch_row_action_found = False
            # success = True
            batch_row_action_measure_status = "BATCH_ROW_ACTION_MEASURE_NOT_FOUND"
            kind_of_action = 'TBD'
    else:
        kind_of_action = 'TBD'
        batch_row_action_measure_status = "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_MEASURE_CREATE"
    # Create a new entry in BatchRowActionMeasure
    try:
        updated_values = {
            'measure_title': measure_title,
            'state_code': state_code,
            'measure_text': measure_text,
            'measure_subtitle': measure_subtitle,
            'kind_of_action': kind_of_action,
            'google_civic_election_id': google_civic_election_id,
            'status': batch_row_action_measure_status
        }

        batch_row_action_measure, new_action_measure_created = BatchRowActionMeasure.objects.update_or_create(
            batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
            defaults=updated_values)
        # new_action_measure_created = True
        success = True
        status = "BATCH_ROW_ACTION_MEASURE_CREATED"

    except Exception as e:
        batch_row_action_measure = BatchRowActionMeasure()
        batch_row_action_found = False
        success = False
        new_action_measure_created = False
        status = "BATCH_ROW_ACTION_MEASURE_RETRIEVE_ERROR"
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'new_action_measure_created': new_action_measure_created,
        'batch_row_action_measure': batch_row_action_measure,
    }
    return results


def create_batch_row_action_office(batch_description, batch_header_map, one_batch_row):
    """
    Handle batch_row for office type
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()

    new_action_office_created = False
    state_code = ''
    batch_row_action_office_status = ''

    # Find the column in the incoming batch_row with the header == office_name
    office_name = batch_manager.retrieve_value_from_batch_row("office_name", batch_header_map, one_batch_row)
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

    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("office_ctcl_uuid", batch_header_map, one_batch_row)

    office_description = batch_manager.retrieve_value_from_batch_row("office_description", batch_header_map,
                                                                     one_batch_row)
    office_is_partisan = batch_manager.retrieve_value_from_batch_row("office_is_partisan", batch_header_map,
                                                                     one_batch_row)

    # Look up ContestOffice to see if an entry exists
    # contest_office = ContestOffice()
    # These three parameters are needed to look up in ContestOffice table for a match
    if positive_value_exists(office_name) and positive_value_exists(state_code) and \
            positive_value_exists(google_civic_election_id):
        try:
            contest_office_query = ContestOffice.objects.all()
            contest_office_query = contest_office_query.filter(office_name__iexact=office_name,
                                                               state_code__iexact=state_code,
                                                               google_civic_election_id=google_civic_election_id)

            contest_office_item_list = list(contest_office_query)
            if len(contest_office_item_list):
                # entry exists
                batch_row_action_office_status = 'BATCH_ROW_ACTION_OFFICE_RETRIEVED'
                batch_row_action_found = True
                new_action_office_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(contest_office_item_list) == 1:
                    kind_of_action = 'ADD_TO_EXISTING'
                else:
                    # more than one entry found with a match in ContestOffice
                    kind_of_action = 'DO_NOT_PROCESS'
            else:
                kind_of_action = 'CREATE'
        except ContestOffice.DoesNotExist:
            batch_row_action_office = BatchRowActionOffice()
            batch_row_action_found = False
            # success = True
            batch_row_action_office_status = "BATCH_ROW_ACTION_OFFICE_NOT_FOUND"
            kind_of_action = 'TBD'
    else:
        kind_of_action = 'TBD'
        batch_row_action_office_status = "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_OFFICE_CREATE"
    # Create a new entry in BatchRowActionOffice
    try:
        updated_values = {
            'office_name': office_name,
            'state_code': state_code,
            'office_description': office_description,
            'ctcl_uuid': ctcl_uuid,
            'office_is_partisan': office_is_partisan,
            'kind_of_action': kind_of_action,
            'google_civic_election_id': google_civic_election_id,
            'status': batch_row_action_office_status
        }

        batch_row_action_office, new_action_office_created = BatchRowActionOffice.objects.update_or_create(
            batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
            defaults=updated_values)
        # new_action_office_created = True
        success = True
        status = "BATCH_ROW_ACTION_OFFICE_CREATED"

    except Exception as e:
        batch_row_action_office = BatchRowActionOffice()
        batch_row_action_found = False
        success = False
        new_action_office_created = False
        status = "BATCH_ROW_ACTION_OFFICE_RETRIEVE_ERROR"
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success': success,
        'status': status,
        'new_action_office_created': new_action_office_created,
        'batch_row_action_office': batch_row_action_office,
    }
    return results

