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
    BatchRowActionMeasure
from .models import KIND_OF_ACTION_CHOICES
from measure.models import ContestMeasure
from electoral_district.controllers import retrieve_state_code

logger = wevote_functions.admin.get_logger(__name__)

# VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")

def create_batch_row_actions(batch_header_id, batch_row_id):
    """
    Cycle through all BatchRow entries for this batch_header_id and move the values we can find into
    the BatchRowActionYYY table so we can review it before importing it
    :param batch_header_id:
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
                results = create_batch_row_action_measure(batch_header_id, batch_description, batch_header_map,
                                                          one_batch_row)

                if results['new_action_measure_created']:
                    batch_row_action_measure = results['batch_row_action_measure']
                    number_of_batch_actions_created += 1
                    success = True
                # # Now check for warnings (like "this is a duplicate"). If warnings are found,
                # # add the warning to batch_row_action_measure entry
                # # batch_row_action_measure.kind_of_action = "TEST"
                # batch_row_action_measure.save()

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

    results = {
        'success': success,
        'status': status,
        'batch_row_action_created': batch_row_action_created,
        'batch_row_action_organization': batch_row_action_organization,
    }
    return results


def create_batch_row_action_measure(batch_header_id, batch_description, batch_header_map, one_batch_row):
    """
    Handle batch_row for measure type
    :param batch_header_id:
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()

    new_action_measure_created = False
    # Find the column in the incoming batch_row with the header == measure_title
    measure_title = batch_manager.retrieve_value_from_batch_row("measure_title", batch_header_map, one_batch_row)
    # Find the column in the incoming batch_row with the header == state_code
    electoral_district_id = batch_manager.retrieve_value_from_batch_row("electoral_district_id", batch_header_map,
                                                                        one_batch_row)
    google_civic_election_id = str(batch_description.google_civic_election_id)

    state_code_results = retrieve_state_code(electoral_district_id)
    if state_code_results or len(state_code_results):
        # TODO can this query return more than one entry?
        state_code = state_code_results.values_list('state_code', flat=True).get()
    else:
        state_code = ''

    measure_text = batch_manager.retrieve_value_from_batch_row("measure_name",
                                                               batch_header_map,
                                                               one_batch_row)
    measure_subtitle = batch_manager.retrieve_value_from_batch_row("measure_sub_title",
                                                                   batch_header_map,
                                                                   one_batch_row)

    # Look up ContestMeasure to see if an entry exists
    contest_measure = ContestMeasure()
    try:
        contest_measure_query = ContestMeasure.objects.order_by('id')
        contest_measure_item_list = contest_measure_query.filter(measure_title__iexact=measure_title,
                                                                 state_code__iexact=state_code,
                                                                 google_civic_election_id=google_civic_election_id)

        if contest_measure_item_list or len(contest_measure_item_list):
            # entry exists
            status = 'BATCH_ROW_ACTION_MEASURE_RETRIEVED'
            batch_row_action_found = True
            new_action_measure_created = False
            success = True
            batch_row_action_measure = contest_measure_item_list
            # if a single entry matches, update that entry
            if len(contest_measure_item_list) == 1:
                kind_of_action = 'ADD_TO_EXISTING'
            else:
                # more than one entry found with a match in ContestMeasure
                kind_of_action = 'DO_NOT_PROCESS'
        else:
            kind_of_action = 'CREATE'
            # Create a new entry
        try:
            # TODO for now use create instead of create_or_update
            batch_row_action_measure = BatchRowActionMeasure.objects.create(
                batch_header_id=batch_description.batch_header_id, batch_row_id=one_batch_row.id,
                measure_title=measure_title, state_code=state_code, measure_text=measure_text,
                measure_subtitle=measure_subtitle, kind_of_action=kind_of_action,
                google_civic_election_id=google_civic_election_id)
            new_action_measure_created = True
            success = True
            status = "BATCH_ROW_ACTION_MEASURE_CREATED"

            batch_row_action_measure.save()

        # except Exception as e:
        #     new_action_measure_created = False
        #     batch_row_action_measure = BatchRowActionMeasure()
        #     success = False
        #     status = "BATCH_ROW_ACTION_MEASURE_NOT_CREATED"
            #
            # if created:
            #     batch_row_action_measure = new_row_action_measure['batch_row_action_measure']
            #     number_of_batch_actions_created += 1
        except Exception as e:
            batch_row_action_measure = BatchRowActionMeasure()
            batch_row_action_found = False
            success = False
            new_action_measure_created = False
            status = "BATCH_ROW_ACTION_MEASURE_RETRIEVE_ERROR"


    except ContestMeasure.DoesNotExist:
        batch_row_action_measure = BatchRowActionMeasure()
        batch_row_action_found = False
        success = True
        status = "BATCH_ROW_ACTION_MEASURE_NOT_FOUND"
        kind_of_action  = 'TBD'

        # else:
        #     # Move on to the next batch row
        #     continue
    # Now check for warnings (like "this is a duplicate"). If warnings are found,
    # add the warning to batch_row_action_measure entry
    # batch_row_action_measure.kind_of_action = "TEST"
    # batch_row_action_measure.save()

    results = {
        'success': success,
        'status': status,
        'new_action_measure_created': new_action_measure_created,
        'batch_row_action_measure': batch_row_action_measure,
    }
    return results

