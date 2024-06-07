# import_export_batches/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import BatchManager, BatchDescription, BatchHeaderMap, BatchRow, BatchRowActionOrganization, \
    BatchRowActionMeasure, BatchRowActionOfficeHeld, BatchRowActionContestOffice, BatchRowActionPolitician, \
    BatchRowActionCandidate, BatchRowActionPollingLocation, BatchRowActionPosition, BatchRowActionBallotItem, \
    CLEAN_DATA_MANUALLY, POSITION, IMPORT_DELETE, IMPORT_ALREADY_DELETED, \
    IMPORT_CREATE, IMPORT_ADD_TO_EXISTING, IMPORT_DATA_ALREADY_MATCHING, IMPORT_QUERY_ERROR, \
    IMPORT_TO_BE_DETERMINED, DO_NOT_PROCESS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES, BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_OFFICES_HELD, BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLLING_LOCATIONS, BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS, \
    BATCH_IMPORT_KEYS_ACCEPTED_FOR_REPRESENTATIVES
from ballot.models import BallotItem, BallotItemListManager, BallotItemManager, BallotReturnedManager
from candidate.controllers import retrieve_next_or_most_recent_office_for_candidate
from candidate.models import CandidateCampaign, CandidateListManager, CandidateManager
# from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now
from office_held.models import OfficeHeld, OfficeHeldManager
from electoral_district.controllers import retrieve_electoral_district
from election.models import ElectionManager
from exception.models import handle_exception, print_to_log
from image.controllers import retrieve_and_save_ballotpedia_candidate_images
from measure.models import ContestMeasure, ContestMeasureManager, ContestMeasureListManager
from office.models import ContestOffice, ContestOfficeListManager, ContestOfficeManager
from organization.models import Organization, OrganizationListManager, OrganizationManager, \
    NONPROFIT_501C3, NONPROFIT_501C4, POLITICAL_ACTION_COMMITTEE, PUBLIC_FIGURE, \
    CORPORATION, NEWS_ORGANIZATION, UNKNOWN
from politician.models import Politician, PoliticianManager
from polling_location.models import PollingLocationManager
from position.models import PositionManager, INFORMATION_ONLY, OPPOSE, SUPPORT
from twitter.models import TwitterUserManager
from volunteer_task.models import VOLUNTEER_ACTION_CANDIDATE_CREATED, VOLUNTEER_ACTION_POSITION_SAVED, \
    VolunteerTaskManager
from voter.models import fetch_voter_from_voter_device_link, VoterManager
from voter_guide.controllers import refresh_existing_voter_guides
from voter_guide.models import ORGANIZATION_WORD
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)

# VOTE_SMART_API_KEY = get_environment_variable("VOTE_SMART_API_KEY")
CANDIDATE = 'CANDIDATE'
CONTEST_OFFICE = 'CONTEST_OFFICE'
OFFICE_HELD = 'OFFICE_HELD'
IMPORT_BALLOT_ITEM = 'IMPORT_BALLOT_ITEM'
IMPORT_POLLING_LOCATION = 'IMPORT_POLLING_LOCATION'
IMPORT_VOTER = 'IMPORT_VOTER'
MEASURE = 'MEASURE'
POLITICIAN = 'POLITICIAN'
REPRESENTATIVES = 'REPRESENTATIVES'


def create_batch_row_actions(
        batch_header_id,
        batch_description=None,
        batch_row_id=0,
        state_code="",
        delete_analysis_only=False,
        election_objects_dict={},
        measure_objects_dict={},
        office_objects_dict={}):
    """
    Cycle through all BatchRow entries for this batch_header_id and move the values we can find into
    the BatchRowActionYYY table, so we can review it before importing it
    :param batch_header_id:
    :param batch_description:
    :param batch_row_id:
    :param state_code:
    :param delete_analysis_only:
    :param election_objects_dict:
    :param measure_objects_dict:
    :param office_objects_dict:
    :return:
    """
    success = False
    update_success = False
    status = ""
    number_of_batch_actions_created = 0
    number_of_batch_actions_updated = 0
    number_of_batch_actions_failed = 0
    kind_of_batch = ""
    polling_location_we_vote_id = ""
    voter_id = 0

    if not positive_value_exists(batch_header_id):
        status += "CREATE_BATCH_ROW_ACTIONS-BATCH_HEADER_ID_MISSING "
        results = {
            'success':                          success,
            'status':                           status,
            'batch_header_id':                  batch_header_id,
            'kind_of_batch':                    kind_of_batch,
            'batch_actions_created':            success,
            'number_of_batch_actions_created':  number_of_batch_actions_created,
            'batch_actions_updated':            update_success,
            'number_of_batch_actions_updated':  number_of_batch_actions_updated,
            'election_objects_dict':            election_objects_dict,
            'measure_objects_dict':             measure_objects_dict,
            'office_objects_dict':              office_objects_dict,
            'polling_location_we_vote_id':      polling_location_we_vote_id,
            'voter_id':                         voter_id,
        }
        return results

    try:
        if batch_description is not None:
            batch_description_found = True
        else:
            batch_description = BatchDescription.objects.get(batch_header_id=batch_header_id)  # read_only=False
            batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = None
        batch_description_found = False
    except Exception as e:
        status += "FAILURE_RETRIEVING_BATCH_DESCRIPTION: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)
        batch_description = None
        batch_description_found = False

    batch_header_map_found = False
    batch_header_map = None
    if batch_description_found:
        kind_of_batch = batch_description.kind_of_batch

        try:
            batch_header_map = BatchHeaderMap.objects.using('readonly').get(batch_header_id=batch_header_id)
            batch_header_map_found = True
        except BatchHeaderMap.DoesNotExist:
            # This is fine
            pass
        except Exception as e:
            status += "FAILURE_RETRIEVING_BATCH_HEADER_MAP: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

    batch_row_list = []
    batch_row_action_list_found = False
    if batch_description_found and batch_header_map_found and not delete_analysis_only:
        try:
            batch_row_query = BatchRow.objects.all()  # We need to be able to save the batch_row entries we retrieve
            batch_row_query = batch_row_query.filter(batch_header_id=batch_header_id)
            if positive_value_exists(batch_row_id):
                batch_row_query = batch_row_query.filter(id=batch_row_id)
            elif positive_value_exists(state_code):
                batch_row_query = batch_row_query.filter(state_code__iexact=state_code)
            # We Vote uses Postgres, and we want the False values to be returned first
            # https://groups.google.com/forum/#!topic/django-developers/h5ok_KeXYW4
            # This is because we want to make sure BatchRows that have NOT been analyzed get analyzed first,
            # and BatchRowAction entries that are set to "Create" get updated before those that are set to "Update"
            # batch_row_query = batch_row_query.order_by("-batch_row_created", "-batch_row_analyzed")

            batch_row_list = list(batch_row_query)
            if len(batch_row_list):
                batch_row_action_list_found = True
        except BatchRow.DoesNotExist:
            # This is fine
            status += "COULD_NOT_FIND_ANY_BATCH_ROW_ENTRY "
        except Exception as e:
            status += "ERROR_RETRIEVING_BATCH_ROW_ENTRIES: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)
    else:
        status += "ELSE [if batch_description_found and batch_header_map_found and not delete_analysis_only] "

    batch_row_action_list = []
    start_create_batch_row_action_time_tracker = []
    if batch_description_found and batch_header_map_found and batch_row_action_list_found and not delete_analysis_only:
        for one_batch_row in batch_row_list:
            start_create_batch_row_action_time_tracker.append(now().strftime("%H:%M:%S:%f"))
            if kind_of_batch == CANDIDATE:
                results = create_batch_row_action_candidate(batch_description, batch_header_map, one_batch_row)

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
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
            elif kind_of_batch == OFFICE_HELD:
                results = create_batch_row_action_office_held(batch_description, batch_header_map, one_batch_row)

                if results['action_office_held_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['new_action_office_held_created']:
                    # for now, do not handle batch_row_action_office_held data
                    # batch_row_action_office_held = results['batch_row_action_office_held']
                    number_of_batch_actions_created += 1
                    success = True
            elif kind_of_batch == MEASURE:
                results = create_batch_row_action_measure(batch_description, batch_header_map, one_batch_row)

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
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

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
                    # for now, do not handle batch_row_action_politician data
                    # batch_row_action_politician = results['batch_row_action_politician']
                    number_of_batch_actions_created += 1
                    success = True
            elif kind_of_batch == IMPORT_POLLING_LOCATION:
                results = create_batch_row_action_polling_location(batch_description, batch_header_map, one_batch_row)

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
                    number_of_batch_actions_created += 1
                    success = True
            elif kind_of_batch == POSITION:
                results = create_batch_row_action_position(batch_description, batch_header_map, one_batch_row)

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
                    # for now, do not handle batch_row_action_politician data
                    # batch_row_action_politician = results['batch_row_action_politician']
                    number_of_batch_actions_created += 1
                    success = True
                elif not results['success']:
                    status += results['status']
                status += "CREATE_BATCH_ROW_ACTION_POSITION-START: "
                status += results['status']
                print_to_log(logger=logger, exception_message_optional=status)
            elif kind_of_batch == IMPORT_BALLOT_ITEM:
                results = create_batch_row_action_ballot_item(
                    batch_description=batch_description,
                    batch_header_map=batch_header_map,
                    one_batch_row=one_batch_row,
                    election_objects_dict=election_objects_dict,
                    measure_objects_dict=measure_objects_dict,
                    office_objects_dict=office_objects_dict,
                )
                election_objects_dict = results['election_objects_dict']
                measure_objects_dict = results['measure_objects_dict']
                office_objects_dict = results['office_objects_dict']

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
                    number_of_batch_actions_created += 1
                    success = True
                elif results['batch_row_action_delete_created']:
                    number_of_batch_actions_created += 1
                    success = True

                batch_row_action_ballot_item = results['batch_row_action_ballot_item']
                polling_location_we_vote_id = batch_row_action_ballot_item.polling_location_we_vote_id
                voter_id = batch_row_action_ballot_item.voter_id

                batch_row_action_list.append(batch_row_action_ballot_item)
            elif kind_of_batch == REPRESENTATIVES:
                results = create_batch_row_action_ballot_item(
                    batch_description=batch_description,
                    batch_header_map=batch_header_map,
                    one_batch_row=one_batch_row,
                    election_objects_dict=election_objects_dict,
                    measure_objects_dict=measure_objects_dict,
                    office_objects_dict=office_objects_dict,
                )
                election_objects_dict = results['election_objects_dict']
                measure_objects_dict = results['measure_objects_dict']
                office_objects_dict = results['office_objects_dict']

                if results['batch_row_action_updated']:
                    number_of_batch_actions_updated += 1
                    success = True
                elif results['batch_row_action_created']:
                    number_of_batch_actions_created += 1
                    success = True
                elif results['batch_row_action_delete_created']:
                    number_of_batch_actions_created += 1
                    success = True

                batch_row_action_ballot_item = results['batch_row_action_ballot_item']
                polling_location_we_vote_id = batch_row_action_ballot_item.polling_location_we_vote_id
                voter_id = batch_row_action_ballot_item.voter_id

                batch_row_action_list.append(batch_row_action_ballot_item)
    else:
        status += "CREATE_BATCH_ROW_CONDITIONS_NOT_MET " \
                  "[batch_description_found and batch_header_map_found and batch_row_action_list_found " \
                  "and not delete_analysis_only] "

    existing_ballot_item_list = []
    number_of_batch_action_deletes_created = 0
    if kind_of_batch == IMPORT_BALLOT_ITEM:
        # Only deal with deleting ballot items if we are NOT looking at just one batch row
        if not positive_value_exists(batch_row_id):
            if delete_analysis_only:
                # If here we need to retrieve existing batch_row_actions
                batch_manager = BatchManager()
                results = batch_manager.retrieve_batch_row_action_ballot_item_list(
                    batch_header_id, limit_to_kind_of_action_list=[IMPORT_CREATE, IMPORT_ADD_TO_EXISTING])
                if results['batch_row_action_list_found']:
                    batch_row_action_list = results['batch_row_action_list']
                    if positive_value_exists(batch_description.polling_location_we_vote_id):
                        polling_location_we_vote_id = batch_description.polling_location_we_vote_id
                    elif len(batch_row_action_list):
                        batch_row_action_ballot_item = batch_row_action_list[0]
                        polling_location_we_vote_id = batch_row_action_ballot_item.polling_location_we_vote_id
                        voter_id = batch_row_action_ballot_item.voter_id

            if batch_description_found and batch_header_map_found:
                # Start by retrieving existing ballot items for this map point
                if positive_value_exists(polling_location_we_vote_id) and \
                        positive_value_exists(batch_description.google_civic_election_id):
                    ballot_item_list_manager = BallotItemListManager()
                    google_civic_election_id_list = [batch_description.google_civic_election_id]
                    results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        google_civic_election_id_list=google_civic_election_id_list,
                        read_only=False)
                    if results['ballot_item_list_found']:
                        existing_ballot_item_list = results['ballot_item_list']
            else:
                status += "COULD_NOT_RETRIEVE_EXISTING_BALLOT_ITEMS " \
                          "[ELSE if batch_description_found and batch_header_map_found] "

        if existing_ballot_item_list and len(existing_ballot_item_list):
            # If we are here, then we are checking to see if there were previous ballot items
            # that have since been deleted
            # Note that we should not be here if we are looking at only one batch row
            election_manager = ElectionManager()
            for existing_ballot_item in existing_ballot_item_list:
                batch_row_action_found = False
                batch_row_action_delete_exists = False
                for batch_row_action in batch_row_action_list:
                    if batch_row_action_found:
                        continue
                    elif positive_value_exists(batch_row_action.contest_measure_we_vote_id) and \
                            batch_row_action.contest_measure_we_vote_id == \
                            existing_ballot_item.contest_measure_we_vote_id:
                        batch_row_action_found = True
                    elif positive_value_exists(batch_row_action.contest_office_we_vote_id) and \
                            batch_row_action.contest_office_we_vote_id == \
                            existing_ballot_item.contest_office_we_vote_id:
                        batch_row_action_found = True
                    else:
                        # Doesn't match this existing_ballot_item
                        pass
                if not positive_value_exists(batch_row_action_found):
                    # If here we know that a ballot item already exists, and the current data would NOT be
                    #  creating/updating a ballot item. Create a delete action.
                    ballot_item_deleting_turned_on = True
                    election = None
                    election_found = False
                    google_civic_election_id = ''
                    if hasattr(existing_ballot_item, 'google_civic_election_id'):
                        google_civic_election_id = existing_ballot_item.google_civic_election_id
                    state_code = ''
                    if hasattr(existing_ballot_item, 'state_code'):
                        state_code = existing_ballot_item.state_code
                    if google_civic_election_id in election_objects_dict:
                        election = election_objects_dict[google_civic_election_id]
                        election_found = True
                    else:
                        results = election_manager.retrieve_election(google_civic_election_id)
                        if results['election_found']:
                            election = results['election']
                            election_found = True
                            election_objects_dict[google_civic_election_id] = election
                    if positive_value_exists(state_code) and \
                            election_found and \
                            hasattr(election, 'use_ctcl_as_data_source_by_state_code') and \
                            positive_value_exists(election.use_ctcl_as_data_source_by_state_code):
                        # If we are pulling from two data sources, we don't want to delete ballot item entries
                        if state_code.lower() in election.use_ctcl_as_data_source_by_state_code.lower():
                            ballot_item_deleting_turned_on = False
                    # Only schedule the deletion of the ballot_item when we are only using one data source
                    #  (Like Vote USA, or CTCL exclusively)
                    if positive_value_exists(ballot_item_deleting_turned_on):
                        results = create_batch_row_action_ballot_item_delete(batch_description, existing_ballot_item)
                        batch_row_action_delete_exists = results['batch_row_action_delete_exists']

                if positive_value_exists(batch_row_action_delete_exists):
                    number_of_batch_action_deletes_created += 1
        else:
            status += "EXISTING_BALLOT_ITEM_LIST_EMPTY "
    elif kind_of_batch == REPRESENTATIVES:
        # Only deal with deleting ballot items if we are NOT looking at just one batch row
        if not positive_value_exists(batch_row_id):
            if delete_analysis_only:
                # If here we need to retrieve existing batch_row_actions
                batch_manager = BatchManager()
                results = batch_manager.retrieve_batch_row_action_ballot_item_list(
                    batch_header_id, limit_to_kind_of_action_list=[IMPORT_CREATE, IMPORT_ADD_TO_EXISTING])
                if results['batch_row_action_list_found']:
                    batch_row_action_list = results['batch_row_action_list']
                    if positive_value_exists(batch_description.polling_location_we_vote_id):
                        polling_location_we_vote_id = batch_description.polling_location_we_vote_id
                    elif len(batch_row_action_list):
                        batch_row_action_ballot_item = batch_row_action_list[0]
                        polling_location_we_vote_id = batch_row_action_ballot_item.polling_location_we_vote_id
                        voter_id = batch_row_action_ballot_item.voter_id

            if batch_description_found and batch_header_map_found:
                # Start by retrieving existing ballot items for this map point
                if positive_value_exists(polling_location_we_vote_id) and \
                        positive_value_exists(batch_description.google_civic_election_id):
                    ballot_item_list_manager = BallotItemListManager()
                    google_civic_election_id_list = [batch_description.google_civic_election_id]
                    results = ballot_item_list_manager.retrieve_all_ballot_items_for_polling_location(
                        polling_location_we_vote_id=polling_location_we_vote_id,
                        google_civic_election_id_list=google_civic_election_id_list,
                        read_only=False)
                    if results['ballot_item_list_found']:
                        existing_ballot_item_list = results['ballot_item_list']
            else:
                status += "COULD_NOT_RETRIEVE_EXISTING_BALLOT_ITEMS " \
                          "[ELSE if batch_description_found and batch_header_map_found] "

        if existing_ballot_item_list and len(existing_ballot_item_list):
            # If we are here, then we are checking to see if there were previous ballot items
            # that have since been deleted
            # Note that we should not be here if we are looking at only one batch row
            election_manager = ElectionManager()
            for existing_ballot_item in existing_ballot_item_list:
                batch_row_action_found = False
                batch_row_action_delete_exists = False
                for batch_row_action in batch_row_action_list:
                    if batch_row_action_found:
                        continue
                    elif positive_value_exists(batch_row_action.contest_measure_we_vote_id) and \
                            batch_row_action.contest_measure_we_vote_id == \
                            existing_ballot_item.contest_measure_we_vote_id:
                        batch_row_action_found = True
                    elif positive_value_exists(batch_row_action.contest_office_we_vote_id) and \
                            batch_row_action.contest_office_we_vote_id == \
                            existing_ballot_item.contest_office_we_vote_id:
                        batch_row_action_found = True
                    else:
                        # Doesn't match this existing_ballot_item
                        pass
                if not positive_value_exists(batch_row_action_found):
                    # If here we know that a ballot item already exists, and the current data would NOT be
                    #  creating/updating a ballot item. Create a delete action.
                    ballot_item_deleting_turned_on = True
                    election = None
                    election_found = False
                    google_civic_election_id = ''
                    if hasattr(existing_ballot_item, 'google_civic_election_id'):
                        google_civic_election_id = existing_ballot_item.google_civic_election_id
                    state_code = ''
                    if hasattr(existing_ballot_item, 'state_code'):
                        state_code = existing_ballot_item.state_code
                    if google_civic_election_id in election_objects_dict:
                        election = election_objects_dict[google_civic_election_id]
                        election_found = True
                    else:
                        results = election_manager.retrieve_election(google_civic_election_id)
                        if results['election_found']:
                            election = results['election']
                            election_found = True
                            election_objects_dict[google_civic_election_id] = election
                    if positive_value_exists(state_code) and \
                            election_found and \
                            hasattr(election, 'use_ctcl_as_data_source_by_state_code') and \
                            positive_value_exists(election.use_ctcl_as_data_source_by_state_code):
                        # If we are pulling from two data sources, we don't want to delete ballot item entries
                        if state_code.lower() in election.use_ctcl_as_data_source_by_state_code.lower():
                            ballot_item_deleting_turned_on = False
                    # Only schedule the deletion of the ballot_item when we are only using one data source
                    #  (Like Vote USA, or CTCL exclusively)
                    if positive_value_exists(ballot_item_deleting_turned_on):
                        results = create_batch_row_action_ballot_item_delete(batch_description, existing_ballot_item)
                        batch_row_action_delete_exists = results['batch_row_action_delete_exists']

                if positive_value_exists(batch_row_action_delete_exists):
                    number_of_batch_action_deletes_created += 1
        else:
            status += "EXISTING_BALLOT_ITEM_LIST_EMPTY "

    # Record that this batch_description has been analyzed, and the source for the ballot_item
    if batch_description_found and success:
        try:
            # If BatchRowAction's were created for BatchDescription, this batch_description was analyzed
            batch_description_changed = False
            if not positive_value_exists(batch_description.polling_location_we_vote_id) and \
                    positive_value_exists(polling_location_we_vote_id):
                batch_description.polling_location_we_vote_id = polling_location_we_vote_id
                batch_description_changed = True
            if not positive_value_exists(batch_description.voter_id) and \
                    positive_value_exists(voter_id):
                batch_description.voter_id = voter_id
                batch_description_changed = True
            if not positive_value_exists(batch_description.batch_description_analyzed) \
                    and not positive_value_exists(batch_row_id):
                # We only want to mark this batch_description as analyzed if we are looking at all rows
                batch_description.batch_description_analyzed = True
                batch_description_changed = True
            if batch_description_changed:
                batch_description.save()
        except Exception as e:
            status += "ANALYZE-COULD_NOT_SAVE_BATCH_DESCRIPTION: " + str(e) + " "
    else:
        status += "BATCH_DESCRIPTION_NOT_FOUND_OR_NOT_SUCCESS-CANNOT_LABEL_ANALYZED "

    results = {
        'success':                          success,
        'status':                           status,
        'batch_header_id':                  batch_header_id,
        'kind_of_batch':                    kind_of_batch,
        'batch_actions_created':            success,
        'number_of_batch_actions_created':  number_of_batch_actions_created,
        'batch_actions_updated':            update_success,
        'number_of_batch_actions_updated':  number_of_batch_actions_updated,
        'number_of_batch_action_deletes_created':  number_of_batch_action_deletes_created,
        'election_objects_dict':            election_objects_dict,
        'measure_objects_dict':             measure_objects_dict,
        'office_objects_dict':              office_objects_dict,
        'polling_location_we_vote_id':      polling_location_we_vote_id,
        'start_create_batch_row_action_time_tracker':   start_create_batch_row_action_time_tracker,
        'voter_id':                         voter_id,
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
        status += "BATCH_ROW_ACTION_ORGANIZATION_UPDATE "
    else:
        # If a BatchRowActionOrganization entry does not exist, create one
        try:
            batch_row_action_organization = BatchRowActionOrganization.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
                batch_set_id=batch_description.batch_set_id,
            )
            batch_row_action_created = True
            success = True
            status += "BATCH_ROW_ACTION_ORGANIZATION_CREATE "
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_organization = BatchRowActionOrganization()
            success = False
            status += "BATCH_ROW_ACTION_ORGANIZATION_NOT_CREATED "

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
    organization_contact_form_url = batch_manager.retrieve_value_from_batch_row(
        "organization_contact_form_url", batch_header_map, one_batch_row)
    organization_contact_name = batch_manager.retrieve_value_from_batch_row(
        "organization_contact_name", batch_header_map, one_batch_row)

    # Now check for warnings (like "this is a duplicate"). If warnings are found,
    # add the warning to batch_row_action_organization entry
    # batch_row_action_organization.kind_of_action = "TEST"
    keep_looking_for_duplicates = True
    if positive_value_exists(organization_we_vote_id):
        # If here, then we are updating an existing known record
        keep_looking_for_duplicates = False
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if organization_results['organization_found']:
            organization = organization_results['organization']
            kind_of_action = IMPORT_ADD_TO_EXISTING
        else:
            kind_of_action = CLEAN_DATA_MANUALLY
            status += "ORGANIZATION_NOT_FOUND_BY_WE_VOTE_ID "

    if positive_value_exists(keep_looking_for_duplicates):
        organization_list_manager = OrganizationListManager()
        matching_results = organization_list_manager.retrieve_organizations_from_twitter_handle(
            twitter_handle=organization_twitter_handle, read_only=True)

        if matching_results['organization_found']:
            organization = matching_results['organization']
            organization_we_vote_id = organization.we_vote_id
            kind_of_action = IMPORT_ADD_TO_EXISTING
        elif matching_results['multiple_entries_found']:
            kind_of_action = CLEAN_DATA_MANUALLY
            status += "MULTIPLE_ORGANIZATIONS_FOUND "
        elif not matching_results['success']:
            kind_of_action = IMPORT_QUERY_ERROR
        else:
            kind_of_action == IMPORT_CREATE

    # Transform data to our constants: BatchRowTranslationMap
    organization_type_transformed = UNKNOWN  # Default to this
    if organization_type.lower() == "c3":
        organization_type_transformed = NONPROFIT_501C3
    elif organization_type.lower() == "c4":
        organization_type_transformed = NONPROFIT_501C4

    try:
        batch_row_action_organization.batch_set_id = batch_description.batch_set_id
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
        batch_row_action_organization.organization_contact_form_url = organization_contact_form_url
        batch_row_action_organization.organization_contact_name = organization_contact_name
        batch_row_action_organization.kind_of_action = kind_of_action
        batch_row_action_organization.save()
        success = True
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_ORGANIZATION_UNABLE_TO_SAVE "

    try:
        if batch_row_action_created or batch_row_action_updated:
            # If BatchRowAction was created, this batch_row was analyzed
            one_batch_row.batch_row_analyzed = True
            one_batch_row.save()
    except Exception as e:
        pass

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

    # new_action_measure_created = False
    # action_measure_updated = False
    batch_row_action_updated = False
    batch_row_action_created = False
    state_code = ''
    status = ''
    success = True
    kind_of_action = IMPORT_TO_BE_DETERMINED
    keep_looking_for_duplicates = True

    # Does a BatchRowActionContestOffice entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_measure(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        status += "BATCH_ROW_ACTION_MEASURE_FOUND "
        batch_row_action_measure = existing_results['batch_row_action_measure']
        batch_row_action_updated = True
    else:
        # If a BatchRowActionMeasure entry does not exist, create one
        try:
            batch_row_action_measure = BatchRowActionMeasure.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
                batch_set_id=batch_description.batch_set_id,
            )
            batch_row_action_created = True
            status += "BATCH_ROW_ACTION_MEASURE_CREATED "
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_measure = BatchRowActionMeasure()
            success = False
            status += "BATCH_ROW_ACTION_MEASURE_NOT_CREATED "

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_measure': batch_row_action_measure,
            }
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_MEASURES

    if positive_value_exists(one_batch_row.google_civic_election_id):
        google_civic_election_id = str(one_batch_row.google_civic_election_id)
    else:
        google_civic_election_id = str(batch_description.google_civic_election_id)

    measure_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "measure_we_vote_id", batch_header_map, one_batch_row)
    # Find the column in the incoming batch_row with the header == measure_title
    measure_title = batch_manager.retrieve_value_from_batch_row("measure_title", batch_header_map, one_batch_row)
    # Find the column in the incoming batch_row with the header == state_code
    electoral_district_id = batch_manager.retrieve_value_from_batch_row(
        "electoral_district_id", batch_header_map, one_batch_row)
    measure_text = batch_manager.retrieve_value_from_batch_row(
        "measure_name", batch_header_map, one_batch_row)
    measure_url = batch_manager.retrieve_value_from_batch_row(
        "measure_url", batch_header_map, one_batch_row)
    measure_subtitle = batch_manager.retrieve_value_from_batch_row(
        "measure_subtitle", batch_header_map, one_batch_row)
    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("ctcl_uuid", batch_header_map, one_batch_row)
    ballotpedia_district_id = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_district_id", batch_header_map, one_batch_row)
    ballotpedia_election_id = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_election_id", batch_header_map, one_batch_row)
    ballotpedia_measure_id = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_measure_id", batch_header_map, one_batch_row)
    ballotpedia_measure_name = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_measure_name", batch_header_map, one_batch_row)
    ballotpedia_measure_status = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_measure_status", batch_header_map, one_batch_row)
    ballotpedia_measure_summary = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_measure_summary", batch_header_map, one_batch_row)
    ballotpedia_measure_text = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_measure_text", batch_header_map, one_batch_row)
    ballotpedia_measure_url = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_measure_url", batch_header_map, one_batch_row)
    ballotpedia_yes_vote_description = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_yes_vote_description", batch_header_map, one_batch_row)
    ballotpedia_no_vote_description = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia_no_vote_description", batch_header_map, one_batch_row)
    election_day_text = batch_manager.retrieve_value_from_batch_row(
        "election_day_text", batch_header_map, one_batch_row)
    state_code = batch_manager.retrieve_value_from_batch_row(
        "state_code", batch_header_map, one_batch_row)

    if not positive_value_exists(state_code):
        # get state code from electoral_district_id
        results = retrieve_electoral_district(electoral_district_id)
        if results['electoral_district_found']:
            if results['state_code_found']:
                state_code = results['state_code']
        else:
            # state_code = ''
            # status += 'MEASURE-ELECTORAL_DISTRICT_NOT_FOUND '
            # kind_of_action = 'TBD'
            pass

    if not positive_value_exists(measure_title):
        measure_title = ballotpedia_measure_name

    if not positive_value_exists(measure_text):
        measure_text = ballotpedia_measure_text

    if not positive_value_exists(measure_subtitle):
        measure_subtitle = ballotpedia_measure_summary

    if not positive_value_exists(measure_url):
        measure_url = ballotpedia_measure_url

    # Look up ContestMeasure to see if an entry exists
    if positive_value_exists(ballotpedia_measure_id):
        try:
            contest_measure = ContestMeasure.objects.get(ballotpedia_measure_id=ballotpedia_measure_id)
            kind_of_action = IMPORT_ADD_TO_EXISTING
            measure_we_vote_id = contest_measure.we_vote_id
            keep_looking_for_duplicates = False
        except ContestMeasure.DoesNotExist:
            keep_looking_for_duplicates = True

    if keep_looking_for_duplicates:
        # These three parameters are needed to look up in Contest Measure table for a match
        if positive_value_exists(measure_title) and positive_value_exists(state_code) and \
                positive_value_exists(google_civic_election_id):
            try:
                contest_measure_query = ContestMeasure.objects.all()
                contest_measure_item_list = contest_measure_query.filter(
                    measure_title__iexact=measure_title,
                    state_code__iexact=state_code,
                    google_civic_election_id=google_civic_election_id)

                if contest_measure_item_list or len(contest_measure_item_list):
                    # entry exists
                    status += 'BATCH_ROW_ACTION_MEASURE_RETRIEVED'
                    # batch_row_action_found = True
                    # new_action_measure_created = False
                    # success = True
                    batch_row_action_measure = contest_measure_item_list
                    # if a single entry matches, update that entry
                    if len(contest_measure_item_list) == 1:
                        kind_of_action = IMPORT_ADD_TO_EXISTING
                        measure_we_vote_id = contest_measure_item_list[0].we_vote_id
                    else:
                        # more than one entry found with a match in ContestMeasure
                        kind_of_action = 'DO_NOT_PROCESS'
                else:
                    keep_looking_for_duplicates = True
            except ContestMeasure.DoesNotExist:
                batch_row_action_measure = BatchRowActionMeasure()
                # batch_row_action_found = False
                # success = True
                status += "CONTEST_MEASURE_NOT_FOUND "
                keep_looking_for_duplicates = True
        else:
            kind_of_action = 'TBD'
            status = "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_MEASURE_CREATE "
            keep_looking_for_duplicates = False

    if keep_looking_for_duplicates:
        kind_of_action = IMPORT_CREATE

    # If we are missing required variables, don't create
    if kind_of_action == IMPORT_CREATE:
        if not positive_value_exists(measure_title) or not positive_value_exists(state_code) or not \
                positive_value_exists(google_civic_election_id):
            kind_of_action = IMPORT_TO_BE_DETERMINED
            status += "COULD_NOT_CREATE_MEASURE_ENTRY-MISSING_REQUIRED_VARIABLES "

    # Now save the data
    try:
        batch_row_action_measure.batch_set_id = batch_description.batch_set_id
        batch_row_action_measure.ballotpedia_district_id = convert_to_int(ballotpedia_district_id)
        batch_row_action_measure.ballotpedia_election_id = convert_to_int(ballotpedia_election_id)
        batch_row_action_measure.ballotpedia_measure_id = convert_to_int(ballotpedia_measure_id)
        batch_row_action_measure.ballotpedia_measure_name = ballotpedia_measure_name
        batch_row_action_measure.ballotpedia_measure_status = ballotpedia_measure_status
        batch_row_action_measure.ballotpedia_measure_summary = ballotpedia_measure_summary
        batch_row_action_measure.ballotpedia_measure_text = ballotpedia_measure_text
        batch_row_action_measure.ballotpedia_measure_url = ballotpedia_measure_url
        batch_row_action_measure.ballotpedia_yes_vote_description = ballotpedia_yes_vote_description
        batch_row_action_measure.ballotpedia_no_vote_description = ballotpedia_no_vote_description
        batch_row_action_measure.ctcl_uuid = ctcl_uuid
        batch_row_action_measure.election_day_text = election_day_text
        batch_row_action_measure.electoral_district_id = electoral_district_id
        batch_row_action_measure.google_civic_election_id = google_civic_election_id
        batch_row_action_measure.measure_text = measure_text
        batch_row_action_measure.measure_title = measure_title
        batch_row_action_measure.measure_url = measure_url
        batch_row_action_measure.measure_we_vote_id = measure_we_vote_id
        batch_row_action_measure.measure_subtitle = measure_subtitle
        batch_row_action_measure.state_code = state_code
        batch_row_action_measure.status = status
        batch_row_action_measure.kind_of_action = kind_of_action
        batch_row_action_measure.save()
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_MEASURE_UNABLE_TO_SAVE: " + str(e) + " "

    # If a state was figured out, then update the batch_row with the state_code so we can use that for filtering
    if positive_value_exists(state_code) and state_code.lower() != one_batch_row.state_code:
        try:
            one_batch_row.state_code = state_code
            one_batch_row.save()
        except Exception as e:
            status += "BATCH_ROW_STATE_UPDATE_FAILED: " + str(e) + " "
            success = False

    try:
        batch_row_changed = False
        if positive_value_exists(state_code) and state_code.lower() != one_batch_row.state_code:
            one_batch_row.state_code = state_code
            batch_row_changed = True
        if batch_row_action_created or batch_row_action_updated:
            # If BatchRowAction was created, this batch_row was analyzed
            one_batch_row.batch_row_analyzed = True
            batch_row_changed = True
        if batch_row_changed:
            one_batch_row.save()
    except Exception as e:
        status += "BATCH_ROW_ANALYZED_OR_STATE_UPDATE_FAILED: " + str(e) + " "
        success = False

    results = {
        'success':                      success,
        'status':                       status,
        # 'new_action_measure_created':   new_action_measure_created,
        # 'action_measure_updated':       action_measure_updated,
        'batch_row_action_updated':     batch_row_action_updated,
        'batch_row_action_created':     batch_row_action_created,
        'batch_row_action_measure':     batch_row_action_measure,
    }
    return results


def create_batch_row_action_office_held(batch_description, batch_header_map, one_batch_row):
    """
    Handle batch_row for office held
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()

    new_action_office_held_created = False
    action_office_held_updated = False
    state_code = ''
    batch_row_action_office_held_status = ''
    office_held_we_vote_id = ''
    success = False
    status = ''

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_OFFICES_HELD

    # Find the column in the incoming batch_row with the header == office_held_name
    office_held_name = batch_manager.retrieve_value_from_batch_row("office_held_name",
                                                                   batch_header_map, one_batch_row)
    # Find the column in the incoming batch_row with the header == state_code
    electoral_district_id = batch_manager.retrieve_value_from_batch_row("electoral_district_id", batch_header_map,
                                                                        one_batch_row)
    if positive_value_exists(one_batch_row.google_civic_election_id):
        google_civic_election_id = str(one_batch_row.google_civic_election_id)
    else:
        google_civic_election_id = str(batch_description.google_civic_election_id)
    results = retrieve_electoral_district(electoral_district_id)
    if results['electoral_district_found']:
        if results['state_code_found']:
            state_code = results['state_code']
    else:
        # state_code = ''
        batch_row_action_office_status = 'ELECTORAL_DISTRICT_NOT_FOUND'
        kind_of_action = 'TBD'

    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("office_held_ctcl_uuid", batch_header_map, one_batch_row)

    office_held_description = batch_manager.retrieve_value_from_batch_row("office_held_description",
                                                                             batch_header_map, one_batch_row)
    office_held_is_partisan = batch_manager.retrieve_value_from_batch_row("office_held_is_partisan",
                                                                             batch_header_map, one_batch_row)
    office_held_name_es = batch_manager.retrieve_value_from_batch_row("office_held_name_es", batch_header_map,
                                                                         one_batch_row)
    office_held_description_es = batch_manager.retrieve_value_from_batch_row("office_held_description_es",
                                                                                batch_header_map, one_batch_row)

    office_held_ctcl_id = batch_manager.retrieve_value_from_batch_row("office_held_batch_id", batch_header_map,
                                                                         one_batch_row)
    # Look up OfficeHeld to see if an entry exists
    # These three parameters are needed to look up in OfficeHeld table for a match
    if positive_value_exists(office_held_name) and positive_value_exists(state_code) and \
            positive_value_exists(google_civic_election_id):
        try:
            office_held_query = OfficeHeld.objects.all()
            office_held_query = office_held_query.filter(
                office_held_name__iexact=office_held_name,
                state_code__iexact=state_code,
                google_civic_election_id=google_civic_election_id)

            office_held_item_list = list(office_held_query)
            if len(office_held_item_list):
                # entry exists
                batch_row_action_office_held_status = 'OFFICE_HELD_ENTRY_EXISTS'
                batch_row_action_found = True
                new_action_office_held_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(office_held_item_list) == 1:
                    kind_of_action = IMPORT_ADD_TO_EXISTING
                    office_held_we_vote_id = office_held_item_list[0].we_vote_id
                else:
                    # more than one entry found with a match in OfficeHeld
                    kind_of_action = 'DO_NOT_PROCESS'
                    # office_held_we_vote_id = office_held_item_list.values('office_held_we_vote_id')
            else:
                kind_of_action = IMPORT_CREATE
        except OfficeHeld.DoesNotExist:
            batch_row_action_office_held = BatchRowActionOfficeHeld()
            batch_row_action_found = False
            # success = True
            batch_row_action_office_held_status = "BATCH_ROW_ACTION_OFFICE_HELD_NOT_FOUND"
            kind_of_action = 'TBD'
    else:
        kind_of_action = 'TBD'
        batch_row_action_office_held_status = "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_OFFICE_HELD_CREATE"
    # Create a new entry in BatchRowActionOfficeHeld
    try:

        # Check if office_held_name, state_code match exists in BatchRowActionOfficeHeld
        # for this header_id (Duplicate entries in the same data set
        existing_batch_row_action_office_held_query = BatchRowActionOfficeHeld.objects.all()
        existing_batch_row_action_office_held_query = existing_batch_row_action_office_held_query.filter(
            batch_header_id=batch_description.batch_header_id, office_held_name__iexact=office_held_name,
            state_code__iexact=state_code, google_civic_election_id=google_civic_election_id)
        existing_batch_row_action_office_held_list = list(existing_batch_row_action_office_held_query)
        number_of_existing_entries = len(existing_batch_row_action_office_held_list)
        if not number_of_existing_entries:
            # no entry exists, create one
            updated_values = {
                'office_held_name': office_held_name,
                'state_code': state_code,
                'office_held_description': office_held_description,
                'ctcl_uuid': ctcl_uuid,
                'office_held_is_partisan': office_held_is_partisan,
                'office_held_we_vote_id': office_held_we_vote_id,
                'kind_of_action': kind_of_action,
                'google_civic_election_id': google_civic_election_id,
                'status': batch_row_action_office_held_status,
                'office_held_name_es': office_held_name_es,
                'office_held_description_es': office_held_description_es,
                'office_held_ctcl_id': office_held_ctcl_id
            }

            batch_row_action_office_held, new_action_office_held_created = BatchRowActionOfficeHeld.objects.\
                update_or_create(batch_header_id=batch_description.batch_header_id,
                                 batch_row_id=one_batch_row.id,
                                 batch_set_id=batch_description.batch_set_id,
                                 defaults=updated_values)
            # new_action_office_held_created = True
            success = True
            status += "CREATE_BATCH_ROW_ACTION_OFFICE_HELD-BATCH_ROW_ACTION_OFFICE_HELD_CREATED"
        else:
            # # if batch_header_id is same then it is a duplicate entry?
            existing_office_held_entry = existing_batch_row_action_office_held_query.first()
            if one_batch_row.id != existing_office_held_entry.batch_row_id:
                # duplicate entry, create a new entry but set kind_of_action as DO_NOT_PROCESS and
                # set status as duplicate
                # kind_of_action = 'DO_NOT_PROCESS'
                updated_values = {
                    'office_held_name': office_held_name,
                    'state_code': state_code,
                    'office_held_description': office_held_description,
                    'ctcl_uuid': ctcl_uuid,
                    'office_held_is_partisan': office_held_is_partisan,
                    'office_held_we_vote_id': office_held_we_vote_id,
                    'kind_of_action': 'DO_NOT_PROCESS',
                    'google_civic_election_id': google_civic_election_id,
                    'status': 'DUPLICATE_OFFICE_HELD_ENTRY',
                    'office_held_name_es': office_held_name_es,
                    'office_held_description_es': office_held_description_es,
                    'office_held_ctcl_id': office_held_ctcl_id
                }

                batch_row_action_office_held, new_action_office_held_created = \
                    BatchRowActionOfficeHeld.objects.update_or_create(
                        batch_header_id=batch_description.batch_header_id,
                        batch_row_id=one_batch_row.id,
                        batch_set_id=batch_description.batch_set_id,
                        defaults=updated_values)
                status += 'CREATE_BATCH_ROW_ACTION_OFFICE_HELD-BATCH_ROW_ACTION_OFFICE_HELD_DUPLICATE_ENTRIES'
                success = True
                action_office_held_updated = True
                # this is a duplicate entry, mark it's kind_of_action as DO_NOT_PROCESS and status as duplicate
            else:
                # existing entry but not duplicate
                status += 'BATCH_ROW_ACTION_OFFICE_HELD_ENTRY_EXISTS'
                success = True
                batch_row_action_office_held = existing_office_held_entry
    except Exception as e:
        batch_row_action_office_held = BatchRowActionOfficeHeld()
        batch_row_action_found = False
        success = False
        new_action_office_held_created = False
        status = "CREATE_BATCH_ROW_ACTION_OFFICE_HELD_BATCH_ROW_ACTION_OFFICE_HELD_RETRIEVE_ERROR"
        handle_exception(e, logger=logger, exception_message=status)

    try:
        if new_action_office_held_created or action_office_held_updated:
            # If BatchRowAction was created, this batch_row was analyzed
            one_batch_row.batch_row_analyzed = True
            one_batch_row.save()
    except Exception as e:
        pass

    results = {
        'success':                              success,
        'status':                               status,
        'new_action_office_held_created':    new_action_office_held_created,
        'action_office_held_updated':        action_office_held_updated,
        'batch_row_action_office_held':      batch_row_action_office_held,
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
    contest_office_name_mapped = False
    status = ''
    success = True
    kind_of_action = IMPORT_TO_BE_DETERMINED
    # Does a BatchRowActionContestOffice entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_contest_office(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        status += "BATCH_ROW_ACTION_CONTEST_OFFICE_FOUND "
        batch_row_action_contest_office = existing_results['batch_row_action_contest_office']
        batch_row_action_updated = True
    else:
        # If a BatchRowActionContestOffice entry does not exist, create one
        try:
            batch_row_action_contest_office = BatchRowActionContestOffice.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
                batch_set_id=batch_description.batch_set_id,
            )
            batch_row_action_created = True
            status += "BATCH_ROW_ACTION_CONTEST_OFFICE_CREATED "
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_contest_office = BatchRowActionContestOffice()
            success = False
            status += "BATCH_ROW_ACTION_CONTEST_OFFICE_NOT_CREATED: " + str(e) + " "

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_contest_office': batch_row_action_contest_office,
            }
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_CONTEST_OFFICES

    contest_office_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "contest_office_we_vote_id", batch_header_map, one_batch_row)

    if positive_value_exists(one_batch_row.google_civic_election_id):
        google_civic_election_id = str(one_batch_row.google_civic_election_id)
    else:
        google_civic_election_id = str(batch_description.google_civic_election_id)

    # check if state_code is given in batch_header_map
    state_code = batch_manager.retrieve_value_from_batch_row("state_code", batch_header_map, one_batch_row)

    # if google_civic_election_id is null, get it from election_day and/or state_code
    if not positive_value_exists(google_civic_election_id):
        election_day = batch_manager.retrieve_value_from_batch_row("election_day", batch_header_map, one_batch_row)
        election_results = batch_manager.retrieve_election_details_from_election_day_or_state_code(
            election_day, state_code, read_only=False)
        if election_results['success']:
            google_civic_election_id = election_results['google_civic_election_id']

    district_id = ""
    district_name = ""
    district_scope = ""
    ocd_division_id = ""

    if not state_code:
        electoral_district_id = batch_manager.retrieve_value_from_batch_row("electoral_district_id", batch_header_map,
                                                                            one_batch_row)
        results = retrieve_electoral_district(electoral_district_id)
        if results['electoral_district_found']:
            electoral_district = results['electoral_district']
            district_id = electoral_district.electoral_district_number
            district_name = electoral_district.electoral_district_name
            district_scope = electoral_district.electoral_district_type
            ocd_division_id = electoral_district.ocd_id_external_id
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
                status += 'ELECTORAL_DISTRICT_NOT_FOUND'
                kind_of_action = 'TBD'

    # Find the column in the incoming batch_row with the header == contest_office_name
    ballotpedia_district_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_district_id", batch_header_map,
                                                                          one_batch_row)
    ballotpedia_election_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_election_id", batch_header_map,
                                                                          one_batch_row)
    ballotpedia_is_marquee = batch_manager.retrieve_value_from_batch_row("ballotpedia_is_marquee", batch_header_map,
                                                                         one_batch_row)
    ballotpedia_office_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_office_id", batch_header_map,
                                                                        one_batch_row)
    ballotpedia_office_name = batch_manager.retrieve_value_from_batch_row("ballotpedia_office_name", batch_header_map,
                                                                          one_batch_row)
    ballotpedia_office_url = batch_manager.retrieve_value_from_batch_row("ballotpedia_office_url", batch_header_map,
                                                                         one_batch_row)
    ballotpedia_race_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_race_id", batch_header_map,
                                                                      one_batch_row)
    ballotpedia_race_office_level = batch_manager.retrieve_value_from_batch_row("ballotpedia_race_office_level",
                                                                                batch_header_map, one_batch_row)
    candidate_name = batch_manager.retrieve_value_from_batch_row("candidate_name", batch_header_map, one_batch_row)
    contest_office_district_name = batch_manager.retrieve_value_from_batch_row("contest_office_district_name",
                                                                               batch_header_map, one_batch_row)
    contest_office_name = batch_manager.retrieve_value_from_batch_row("contest_office_name", batch_header_map,
                                                                      one_batch_row)
    contest_office_votes_allowed = batch_manager.retrieve_value_from_batch_row("contest_office_votes_allowed",
                                                                               batch_header_map, one_batch_row)
    contest_office_number_elected = batch_manager.retrieve_value_from_batch_row("contest_office_number_elected",
                                                                                batch_header_map, one_batch_row)
    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("contest_office_ctcl_uuid", batch_header_map, one_batch_row)
    office_held_ctcl_id = batch_manager.retrieve_value_from_batch_row("office_held_id", batch_header_map,
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
    is_ballotpedia_general_election = batch_manager.retrieve_value_from_batch_row(
        "is_ballotpedia_general_election", batch_header_map, one_batch_row)
    is_ballotpedia_general_runoff_election = batch_manager.retrieve_value_from_batch_row(
        "is_ballotpedia_general_runoff_election", batch_header_map, one_batch_row)
    is_ballotpedia_primary_election = batch_manager.retrieve_value_from_batch_row(
        "is_ballotpedia_primary_election", batch_header_map, one_batch_row)
    is_ballotpedia_primary_runoff_election = batch_manager.retrieve_value_from_batch_row(
        "is_ballotpedia_primary_runoff_election", batch_header_map, one_batch_row)

    vote_usa_office_id = batch_manager.retrieve_value_from_batch_row(
        "voteusa office id", batch_header_map, one_batch_row)
    vote_usa_office_name = batch_manager.retrieve_value_from_batch_row("office", batch_header_map, one_batch_row)
    vote_usa_state_code = batch_manager.retrieve_value_from_batch_row("state code", batch_header_map, one_batch_row)
    if positive_value_exists(vote_usa_state_code):
        state_code = vote_usa_state_code
    vote_usa_district_number = batch_manager.retrieve_value_from_batch_row("district", batch_header_map, one_batch_row)
    vote_usa_jurisdiction_filtered = None
    vote_usa_jurisdiction = batch_manager.retrieve_value_from_batch_row("jurisdiction", batch_header_map, one_batch_row)
    # if not positive_value_exists(vote_usa_jurisdiction):
    #     vote_usa_jurisdiction = batch_manager.retrieve_value_from_batch_row(
    #         "\"jurisdiction\"", batch_header_map, one_batch_row)
    if positive_value_exists(vote_usa_jurisdiction):
        if vote_usa_jurisdiction in ['Federal']:
            vote_usa_jurisdiction_filtered = "Federal"
        elif vote_usa_jurisdiction in ['State']:
            vote_usa_jurisdiction_filtered = "State"
        elif vote_usa_jurisdiction in ['Measure']:
            vote_usa_jurisdiction_filtered = "Measure"
        else:
            vote_usa_jurisdiction_filtered = "Local"

    batch_set_id = batch_description.batch_set_id

    if not positive_value_exists(contest_office_district_name):
        contest_office_district_name = district_name

    # retrieve office_held_name from office_held_id
    if positive_value_exists(office_held_ctcl_id):
        office_held_name = batch_manager.fetch_office_held_name_from_office_held_ctcl_id(
            office_held_ctcl_id, batch_set_id)
    else:
        office_held_name = ""

    # Look up ContestOffice to see if an entry exists
    # contest_office = ContestOffice()
    keep_looking_for_duplicates = True
    contest_office_manager = ContestOfficeManager()
    if positive_value_exists(contest_office_we_vote_id):
        # If here, then we are updating an existing known record
        keep_looking_for_duplicates = False
        kind_of_action = IMPORT_ADD_TO_EXISTING
        results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office_we_vote_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            contest_office_name = contest_office.office_name

    if positive_value_exists(ctcl_uuid):
        # If we are looking at a record with a ctcl_uuid, the we want to skip over a search by non unique
        #  identifiers.
        results = contest_office_manager.retrieve_contest_office_from_ctcl_uuid(ctcl_uuid)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_name = contest_office.office_name
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_ADD_TO_EXISTING
        else:
            kind_of_action = IMPORT_CREATE
    elif positive_value_exists(vote_usa_office_id) and positive_value_exists(google_civic_election_id):
        # If we are looking at a record with a vote_usa_office_id, the we want to skip over a search by non unique
        #  identifiers.
        results = contest_office_manager.retrieve_contest_office(
            vote_usa_office_id=vote_usa_office_id,
            google_civic_election_id=google_civic_election_id)
        if results['contest_office_found']:
            contest_office = results['contest_office']
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_name = contest_office.office_name
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_ADD_TO_EXISTING
        else:
            kind_of_action = IMPORT_CREATE
            if positive_value_exists(vote_usa_office_name):
                contest_office_name = vote_usa_office_name
    else:
        if not positive_value_exists(contest_office_name) and positive_value_exists(ballotpedia_office_name):
            contest_office_name = ballotpedia_office_name

        if positive_value_exists(vote_usa_office_name):
            contest_office_name = vote_usa_office_name

        # These three parameters are needed to look up in ContestOffice table for a match
        if keep_looking_for_duplicates:
            if not positive_value_exists(contest_office_name) or not positive_value_exists(state_code) or not \
                    positive_value_exists(google_civic_election_id):
                kind_of_action = IMPORT_TO_BE_DETERMINED
                status += "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_CONTEST_OFFICE_CREATE "
                keep_looking_for_duplicates = False

        # DALE 2018-07-10 Still considering this...
        # if keep_looking_for_duplicates and positive_value_exists(ballotpedia_office_id):
        #     contest_office_manager = ContestOfficeManager()
        #     matching_results = contest_office_manager.retrieve_contest_office_from_ballotpedia_office_id(
        #         ballotpedia_office_id, google_civic_election_id)
        #     if matching_results['contest_office_found']:
        #         contest_office = matching_results['contest_office']
        #         keep_looking_for_duplicates = False
        #         contest_office_we_vote_id = contest_office.we_vote_id
        #         kind_of_action = IMPORT_ADD_TO_EXISTING
        #     elif matching_results['MultipleObjectsReturned']:
        #         keep_looking_for_duplicates = False
        #         kind_of_action = IMPORT_TO_BE_DETERMINED
        #         status += "MORE_THAN_ONE_OFFICE_WITH_SAME_BALLOTPEDIA_OFFICE_ID "

        if keep_looking_for_duplicates and positive_value_exists(ballotpedia_race_id):
            contest_office_manager = ContestOfficeManager()
            matching_results = contest_office_manager.retrieve_contest_office_from_ballotpedia_race_id(
                ballotpedia_race_id, google_civic_election_id)
            if matching_results['contest_office_found']:
                contest_office = matching_results['contest_office']
                keep_looking_for_duplicates = False
                contest_office_we_vote_id = contest_office.we_vote_id
                kind_of_action = IMPORT_ADD_TO_EXISTING
            elif matching_results['MultipleObjectsReturned']:
                keep_looking_for_duplicates = False
                kind_of_action = IMPORT_TO_BE_DETERMINED
                status += "MORE_THAN_ONE_OFFICE_WITH_SAME_BALLOTPEDIA_RACE_ID "

        if keep_looking_for_duplicates and not positive_value_exists(ballotpedia_race_id):
            contest_office_list_manager = ContestOfficeListManager()
            matching_results = contest_office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
                contest_office_name=contest_office_name,
                google_civic_election_id=google_civic_election_id,
                incoming_state_code=state_code,
                district_id=district_id,
                district_name=contest_office_district_name)
            if matching_results['contest_office_found']:
                contest_office = matching_results['contest_office']
                contest_office_name = contest_office.office_name
                contest_office_we_vote_id = contest_office.we_vote_id
                kind_of_action = IMPORT_ADD_TO_EXISTING
                keep_looking_for_duplicates = False
            elif matching_results['contest_office_list_found']:
                kind_of_action = IMPORT_CREATE
                status += "RETRIEVE_OFFICE_FROM_NON_UNIQUE-MULTIPLE_POSSIBLE_OFFICES_FOUND "
                keep_looking_for_duplicates = True
            elif not matching_results['success']:
                kind_of_action = IMPORT_TO_BE_DETERMINED
                status += "RETRIEVE_OFFICE_FROM_NON_UNIQUE-NO_SUCCESS "
                status += matching_results['status']
                keep_looking_for_duplicates = False
            else:
                kind_of_action = IMPORT_CREATE

        # we haven't found contest_office yet. Look up for existing contest_office using candidate_name & state_code
        if keep_looking_for_duplicates:
            if positive_value_exists(candidate_name) and not positive_value_exists(ballotpedia_race_id):
                candidate_list_manager = CandidateListManager()
                google_civic_election_id_list = [google_civic_election_id]
                matching_results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
                    google_civic_election_id_list=google_civic_election_id_list,
                    state_code=state_code,
                    candidate_name=candidate_name,
                    read_only=True)

                if matching_results['candidate_found']:
                    candidate = matching_results['candidate']
                    contest_office_we_vote_id = candidate.contest_office_we_vote_id
                    contest_office_name = candidate.contest_office_name
                    kind_of_action = IMPORT_ADD_TO_EXISTING
                    keep_looking_for_duplicates = False
                elif matching_results['multiple_entries_found']:
                    kind_of_action = IMPORT_CREATE
                    status += "CREATE_BATCH_ROW_ACTION_OFFICE-MULTIPLE_CANDIDATES_FOUND "
                    keep_looking_for_duplicates = True
                elif not positive_value_exists(matching_results['success']):
                    kind_of_action = IMPORT_TO_BE_DETERMINED
                    status += "RETRIEVE_CANDIDATE_FROM_NON_UNIQUE-NO_SUCCESS "
                    status += matching_results['status']
                    keep_looking_for_duplicates = False
                else:
                    kind_of_action = IMPORT_CREATE

        if keep_looking_for_duplicates:
            # If we are here, then we have exhausted all of the ways we match offices, so we can assume the
            #  office needs to be created
            kind_of_action = IMPORT_CREATE

    # If we are missing required variables, don't create
    if kind_of_action == IMPORT_CREATE:
        if not positive_value_exists(contest_office_name) or not positive_value_exists(state_code) or not \
                positive_value_exists(google_civic_election_id):
            kind_of_action = IMPORT_TO_BE_DETERMINED
            status += "COULD_NOT_CREATE_CONTEST_OFFICE_ENTRY-MISSING_REQUIRED_VARIABLES "

    # Now save the data
    try:
        batch_row_action_contest_office.batch_set_id = batch_description.batch_set_id
        batch_row_action_contest_office.ballotpedia_district_id = convert_to_int(ballotpedia_district_id)
        batch_row_action_contest_office.ballotpedia_election_id = convert_to_int(ballotpedia_election_id)
        batch_row_action_contest_office.ballotpedia_is_marquee = positive_value_exists(ballotpedia_is_marquee)
        batch_row_action_contest_office.ballotpedia_office_id = convert_to_int(ballotpedia_office_id)
        batch_row_action_contest_office.ballotpedia_office_name = ballotpedia_office_name
        batch_row_action_contest_office.ballotpedia_office_url = ballotpedia_office_url
        batch_row_action_contest_office.ballotpedia_race_id = convert_to_int(ballotpedia_race_id)
        if positive_value_exists(vote_usa_jurisdiction_filtered):
            batch_row_action_contest_office.ballotpedia_race_office_level = vote_usa_jurisdiction_filtered
        else:
            batch_row_action_contest_office.ballotpedia_race_office_level = ballotpedia_race_office_level
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
        batch_row_action_contest_office.contest_office_name = contest_office_name
        batch_row_action_contest_office.contest_office_we_vote_id = contest_office_we_vote_id
        batch_row_action_contest_office.ctcl_uuid = ctcl_uuid
        batch_row_action_contest_office.district_name = contest_office_district_name
        if positive_value_exists(vote_usa_district_number):
            batch_row_action_contest_office.district_id = vote_usa_district_number
        else:
            batch_row_action_contest_office.district_id = district_id
        batch_row_action_contest_office.district_scope = district_scope
        batch_row_action_contest_office.office_held_name = office_held_name
        batch_row_action_contest_office.google_civic_election_id = google_civic_election_id
        batch_row_action_contest_office.is_ballotpedia_general_election = \
            positive_value_exists(is_ballotpedia_general_election)
        batch_row_action_contest_office.is_ballotpedia_general_runoff_election = \
            positive_value_exists(is_ballotpedia_general_runoff_election)
        batch_row_action_contest_office.is_ballotpedia_primary_election = \
            positive_value_exists(is_ballotpedia_primary_election)
        batch_row_action_contest_office.is_ballotpedia_primary_runoff_election = \
            positive_value_exists(is_ballotpedia_primary_runoff_election)
        batch_row_action_contest_office.kind_of_action = kind_of_action
        batch_row_action_contest_office.number_voting_for = contest_office_votes_allowed
        batch_row_action_contest_office.number_elected = contest_office_number_elected
        batch_row_action_contest_office.ocd_division_id = ocd_division_id
        batch_row_action_contest_office.state_code = state_code
        batch_row_action_contest_office.status = status
        if positive_value_exists(vote_usa_office_id):
            batch_row_action_contest_office.vote_usa_office_id = vote_usa_office_id
        batch_row_action_contest_office.save()
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_CONTEST_OFFICE_UNABLE_TO_SAVE: " + str(e) + " "

    # If a state was figured out, then update the batch_row with the state_code so we can use that for filtering
    if positive_value_exists(state_code) and state_code.lower() != one_batch_row.state_code:
        try:
            if batch_row_action_created or batch_row_action_updated:
                # If BatchRowAction was created, this batch_row was analyzed
                one_batch_row.batch_row_analyzed = True
            one_batch_row.state_code = state_code
            one_batch_row.save()
        except Exception as e:
            status += "COULD_NOT_SAVE_ONE_BATCH_ROW: " + str(e) + ' '
            success = False

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

    status = ''
    politician_we_vote_id = ''
    batch_row_action_created = False
    batch_row_action_updated = False

    # Does a BatchRowActionPolitician entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_politician(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_politician = existing_results['batch_row_action_politician']
        batch_row_action_updated = True
    else:
        # If a BatchRowActionPolitician entry does not exist, create one
        try:
            batch_row_action_politician = BatchRowActionPolitician.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
                batch_set_id=batch_description.batch_set_id,
            )
            batch_row_action_created = True
            status += "BATCH_ROW_ACTION_CANDIDATE_CREATED "
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_politician = BatchRowActionPolitician()
            success = False
            status += "BATCH_ROW_ACTION_POLITICIAN_NOT_CREATED "

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_politician': batch_row_action_politician,
            }
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLITICIANS

    # Find the column in the incoming batch_row with the header == politician_full_name
    politician_name = batch_manager.retrieve_value_from_batch_row("politician_full_name", batch_header_map,
                                                                  one_batch_row)
    # Find the column in the incoming batch_row with the header == ctcl_uuid
    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("politician_ctcl_uuid", batch_header_map, one_batch_row)
    politician_twitter_url = batch_manager.retrieve_value_from_batch_row("politician_twitter_url", batch_header_map,
                                                                         one_batch_row)
    politician_twitter_url2 = batch_manager.retrieve_value_from_batch_row("politician_twitter_url2", batch_header_map,
                                                                          one_batch_row)
    politician_twitter_url3 = batch_manager.retrieve_value_from_batch_row("politician_twitter_url3", batch_header_map,
                                                                          one_batch_row)
    politician_twitter_url4 = batch_manager.retrieve_value_from_batch_row("politician_twitter_url4", batch_header_map,
                                                                          one_batch_row)
    politician_twitter_url5 = batch_manager.retrieve_value_from_batch_row("politician_twitter_url5", batch_header_map,
                                                                          one_batch_row)
    facebook_id = batch_manager.retrieve_value_from_batch_row("politician_facebook_id", batch_header_map, one_batch_row)
    party_name = batch_manager.retrieve_value_from_batch_row("politician_party_name", batch_header_map, one_batch_row)
    first_name = batch_manager.retrieve_value_from_batch_row("politician_first_name", batch_header_map, one_batch_row)
    middle_name = batch_manager.retrieve_value_from_batch_row("politician_middle_name", batch_header_map, one_batch_row)
    last_name = batch_manager.retrieve_value_from_batch_row("politician_last_name", batch_header_map, one_batch_row)
    website_url = batch_manager.retrieve_value_from_batch_row("politician_website_url", batch_header_map, one_batch_row)
    # FORMERLY politician_email_address
    # email_address = batch_manager.retrieve_value_from_batch_row("politician_email_address", batch_header_map,
    #                                                             one_batch_row)
    politician_email = batch_manager.retrieve_value_from_batch_row("politician_email", batch_header_map, one_batch_row)
    politician_email2 = batch_manager.retrieve_value_from_batch_row("politician_email2", batch_header_map, one_batch_row)
    politician_email3 = batch_manager.retrieve_value_from_batch_row("politician_email3", batch_header_map, one_batch_row)
    youtube_id = batch_manager.retrieve_value_from_batch_row("politician_youtube_id", batch_header_map, one_batch_row)
    googleplus_id = batch_manager.retrieve_value_from_batch_row("politician_googleplus_id", batch_header_map,
                                                                one_batch_row)
    politician_phone_number = batch_manager.retrieve_value_from_batch_row("politician_phone_number", batch_header_map,
                                                                          one_batch_row)
    politician_phone_number2 = batch_manager.retrieve_value_from_batch_row("politician_phone_number2", batch_header_map,
                                                                           one_batch_row)
    politician_phone_number3 = batch_manager.retrieve_value_from_batch_row("politician_phone_number3", batch_header_map,
                                                                           one_batch_row)

    # extract twitter handle from politician_twitter_url
    politician_twitter_handle = extract_twitter_handle_from_text_string(politician_twitter_url)
    politician_twitter_handle2 = extract_twitter_handle_from_text_string(politician_twitter_url2)
    politician_twitter_handle3 = extract_twitter_handle_from_text_string(politician_twitter_url3)
    politician_twitter_handle4 = extract_twitter_handle_from_text_string(politician_twitter_url4)
    politician_twitter_handle5 = extract_twitter_handle_from_text_string(politician_twitter_url5)

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
        # TODO We could also support searching for other incoming politician_twitter_handles
        try:
            politician_query = Politician.objects.all()
            politician_query = politician_query.filter(
                Q(politician_twitter_handle__iexact=politician_twitter_handle) |
                Q(politician_twitter_handle2__iexact=politician_twitter_handle) |
                Q(politician_twitter_handle3__iexact=politician_twitter_handle) |
                Q(politician_twitter_handle4__iexact=politician_twitter_handle) |
                Q(politician_twitter_handle5__iexact=politician_twitter_handle)
            )
            politician_item_list = list(politician_query)
            if len(politician_item_list):
                # entry exists
                status = 'BATCH_ROW_ACTION_POLITICIAN_RETRIEVED-TWITTER_HANDLE '
                batch_row_action_found = True
                batch_row_action_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(politician_item_list) == 1:
                    kind_of_action = IMPORT_ADD_TO_EXISTING
                    single_politician_found = True
                    politician_we_vote_id = politician_item_list[0].we_vote_id
                else:
                    # more than one entry found with a match in Politician
                    kind_of_action = 'DO_NOT_PROCESS'
                    multiple_politicians_found = True
            else:
                # kind_of_action = IMPORT_CREATE
                single_politician_found = False
        except Politician.DoesNotExist:
            batch_row_action_politician = BatchRowActionPolitician()
            status += "BATCH_ROW_ACTION_POLITICIAN_NOT_FOUND-TWITTER_HANDLE "
            kind_of_action = 'TBD'

    if not single_politician_found and not multiple_politicians_found and \
            positive_value_exists(ctcl_uuid):
        try:
            politician_query = Politician.objects.all()
            politician_query = politician_query.filter(ctcl_uuid=ctcl_uuid)

            politician_item_list = list(politician_query)
            if len(politician_item_list):
                # entry exists
                status += 'BATCH_ROW_ACTION_POLITICIAN_RETRIEVED-CTCL_UUID '
                batch_row_action_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(politician_item_list) == 1:
                    kind_of_action = IMPORT_ADD_TO_EXISTING
                    single_politician_found = True
                    politician_we_vote_id = politician_item_list[0].we_vote_id
                else:
                    # more than one entry found with a match in Politician
                    kind_of_action = 'DO_NOT_PROCESS'
                    multiple_politicians_found = True
            else:
                # kind_of_action = IMPORT_CREATE
                single_politician_found = False
        except Politician.DoesNotExist:
            batch_row_action_politician = BatchRowActionPolitician()
            status += "BATCH_ROW_ACTION_POLITICIAN_NOT_FOUND-CTCL_UUID "
            kind_of_action = 'TBD'

    # twitter handle does not exist, next look up politician based on full politician_name
    if not single_politician_found and not multiple_politicians_found and positive_value_exists(politician_name):
        try:
            politician_query = Politician.objects.all()
            politician_query = politician_query.filter(politician_name__iexact=politician_name)
            if positive_value_exists(state_code):
                politician_query = politician_query.filter(state_code__iexact=state_code)

            politician_item_list = list(politician_query)
            if len(politician_item_list):
                # entry exists
                status += 'BATCH_ROW_ACTION_POLITICIAN_RETRIEVED-FULL_NAME '
                batch_row_action_created = False
                # success = True
                # if a single entry matches, update that entry
                if len(politician_item_list) == 1:
                    single_politician_found = True
                    kind_of_action = IMPORT_ADD_TO_EXISTING
                else:
                    # more than one entry found with a match in Politician
                    kind_of_action = 'DO_NOT_PROCESS'
                    multiple_politicians_found = True
            else:
                single_politician_found = False
        except Politician.DoesNotExist:
            batch_row_action_politician = BatchRowActionPolitician()
            single_politician_found = True
            status += "BATCH_ROW_ACTION_POLITICIAN_NOT_FOUND-FULL_NAME "
            kind_of_action = 'TBD'

    # Look up politician based on first and last name
    if not single_politician_found and not multiple_politicians_found and positive_value_exists(politician_name):
        try:
            politician_query = Politician.objects.all()
            politician_query = politician_query.filter(first_name__iexact=first_name)
            politician_query = politician_query.filter(last_name__iexact=last_name)
            if positive_value_exists(state_code):
                politician_query = politician_query.filter(state_code__iexact=state_code)

            politician_item_list = list(politician_query)
            if len(politician_item_list):
                # entry exists
                status += 'BATCH_ROW_ACTION_POLITICIAN_RETRIEVED-FIRST_AND_LAST_NAME '
                batch_row_action_created = False
                # if a single entry matches, update that entry
                if len(politician_item_list) == 1:
                    single_politician_found = True
                    kind_of_action = IMPORT_ADD_TO_EXISTING
                else:
                    # more than one entry found with a match in Politician
                    kind_of_action = 'DO_NOT_PROCESS'
                    multiple_politicians_found = True
            else:
                single_politician_found = False
        except Politician.DoesNotExist:
            batch_row_action_politician = BatchRowActionPolitician()
            single_politician_found = True
            status += "BATCH_ROW_ACTION_POLITICIAN_NOT_FOUND-FIRST_AND_LAST_NAME "
            kind_of_action = 'TBD'

    # if not positive_value_exists(politician_name) and not positive_value_exists(politician_twitter_handle):
    #     kind_of_action = 'TBD'
    #     status += "INSUFFICIENT_DATA_FOR_BATCH_ROW_ACTION_POLITICIAN_CREATE"

    if not single_politician_found and not multiple_politicians_found:
        kind_of_action = IMPORT_CREATE

    try:
        batch_row_action_politician.batch_set_id = batch_description.batch_set_id
        batch_row_action_politician.politician_name = politician_name
        batch_row_action_politician.first_name = first_name
        batch_row_action_politician.middle_name = middle_name
        batch_row_action_politician.last_name = last_name
        batch_row_action_politician.state_code = state_code
        batch_row_action_politician.political_party = party_name
        batch_row_action_politician.ctcl_uuid = ctcl_uuid
        batch_row_action_politician.politician_email = politician_email
        batch_row_action_politician.politician_email2 = politician_email2
        batch_row_action_politician.politician_email3 = politician_email3
        batch_row_action_politician.politician_phone_number = politician_phone_number
        batch_row_action_politician.politician_phone_number2 = politician_phone_number2
        batch_row_action_politician.politician_phone_number3 = politician_phone_number3
        batch_row_action_politician.politician_twitter_handle = politician_twitter_handle
        batch_row_action_politician.politician_twitter_handle2 = politician_twitter_handle2
        batch_row_action_politician.politician_twitter_handle3 = politician_twitter_handle3
        batch_row_action_politician.politician_twitter_handle4 = politician_twitter_handle4
        batch_row_action_politician.politician_twitter_handle5 = politician_twitter_handle5
        batch_row_action_politician.politician_facebook_id = facebook_id
        batch_row_action_politician.politician_googleplus_id = googleplus_id
        batch_row_action_politician.politician_youtube_id = youtube_id
        batch_row_action_politician.politician_url = website_url
        batch_row_action_politician.kind_of_action = kind_of_action
        batch_row_action_politician.status = status
        batch_row_action_politician.politician_we_vote_id = politician_we_vote_id
        batch_row_action_politician.save()

        success = True
        status += "CREATE_BATCH_ROW_ACTION_POLITICIAN-BATCH_ROW_ACTION_POLITICIAN_CREATED"
        batch_row_action_updated = True
    except Exception as e:
        batch_row_action_politician = BatchRowActionPolitician()
        success = False
        batch_row_action_created = False
        status += "CREATE_BATCH_ROW_ACTION_POLITICIAN-BATCH_ROW_ACTION_POLITICIAN_SAVE_ERROR"
        handle_exception(e, logger=logger, exception_message=status)

    # If a state was figured out, then update the batch_row with the state_code so we can use that for filtering
    if positive_value_exists(state_code):
        try:
            one_batch_row.state_code = state_code
            one_batch_row.save()
        except Exception as e:
            pass

    try:
        if positive_value_exists(state_code):
            one_batch_row.state_code = state_code
        if batch_row_action_created or batch_row_action_updated:
            # If BatchRowAction was created, this batch_row was analyzed
            one_batch_row.batch_row_analyzed = True
        if positive_value_exists(state_code) or batch_row_action_created or batch_row_action_updated:
            one_batch_row.save()
    except Exception as e:
        pass

    results = {
        'success':                      success,
        'status':                       status,
        'batch_row_action_created':     batch_row_action_created,
        'batch_row_action_updated':     batch_row_action_updated,
        'batch_row_action_politician':  batch_row_action_politician,
    }
    return results


def create_batch_row_action_polling_location(batch_description, batch_header_map, one_batch_row):
    """

    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()
    polling_location_manager = PollingLocationManager()
    success = False
    status = ""
    batch_row_action_updated = False
    batch_row_action_created = False
    kind_of_action = ""

    # Does a BatchRowActionPollingLocation entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_polling_location(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_polling_location = existing_results['batch_row_action_polling_location']
        batch_row_action_updated = True
        status += "BATCH_ROW_ACTION_POLLING_LOCATION_UPDATE "
    else:
        # If a BatchRowActionPollingLocation entry does not exist, create one
        try:
            batch_row_action_polling_location = BatchRowActionPollingLocation.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
                batch_set_id=batch_description.batch_set_id,
            )
            batch_row_action_created = True
            success = True
            status += "BATCH_ROW_ACTION_POLLING_LOCATION_CREATE "
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_polling_location = None
            success = False
            status += "BATCH_ROW_ACTION_POLLING_LOCATION_NOT_CREATED " + str(e) + ' '

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_polling_location': batch_row_action_polling_location,
            }
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_ORGANIZATIONS

    # Find the column in the incoming batch_row with the header title specified (ex/ "organization_name"
    city = batch_manager.retrieve_value_from_batch_row(
        "city", batch_header_map, one_batch_row)
    county_name = batch_manager.retrieve_value_from_batch_row(
        "county_name", batch_header_map, one_batch_row)
    latitude = batch_manager.retrieve_value_from_batch_row(
        "latitude", batch_header_map, one_batch_row)
    longitude = batch_manager.retrieve_value_from_batch_row(
        "longitude", batch_header_map, one_batch_row)
    line1 = batch_manager.retrieve_value_from_batch_row(
        "line1", batch_header_map, one_batch_row)
    line2 = batch_manager.retrieve_value_from_batch_row(
        "line2", batch_header_map, one_batch_row)
    location_name = batch_manager.retrieve_value_from_batch_row(
        "location_name", batch_header_map, one_batch_row)
    polling_location_deleted = batch_manager.retrieve_value_from_batch_row(
        "polling_location_deleted", batch_header_map, one_batch_row)
    precinct_name = batch_manager.retrieve_value_from_batch_row(
        "precinct_name", batch_header_map, one_batch_row)
    source_code = batch_manager.retrieve_value_from_batch_row(
        "source_code", batch_header_map, one_batch_row)
    state = batch_manager.retrieve_value_from_batch_row(
        "state", batch_header_map, one_batch_row)
    use_for_bulk_retrieve = batch_manager.retrieve_value_from_batch_row(
        "use_for_bulk_retrieve", batch_header_map, one_batch_row)
    polling_location_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "polling_location_we_vote_id", batch_header_map, one_batch_row)
    zip_long = batch_manager.retrieve_value_from_batch_row(
        "zip_long", batch_header_map, one_batch_row)

    keep_looking_for_duplicates = True
    kind_of_action = IMPORT_TO_BE_DETERMINED
    if positive_value_exists(polling_location_we_vote_id):
        # If here, then we are updating an existing known record
        results = \
            polling_location_manager.retrieve_polling_location_by_we_vote_id(polling_location_we_vote_id)
        if results['polling_location_found']:
            polling_location = results['polling_location']
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_ADD_TO_EXISTING
        else:
            kind_of_action = CLEAN_DATA_MANUALLY
            keep_looking_for_duplicates = False
            status += "POLLING_LOCATION_NOT_FOUND_BY_WE_VOTE_ID "

    address_field_exists = \
        positive_value_exists(state) or positive_value_exists(line1) or positive_value_exists(zip_long)
    if keep_looking_for_duplicates and address_field_exists:
        matching_results = polling_location_manager.retrieve_duplicate_polling_locations(
            state=state,
            line1=line1,
            zip_long=zip_long,
        )
        if matching_results['polling_location_list_found']:
            polling_location_list = matching_results['polling_location_list']
            keep_looking_for_duplicates = False
            if len(polling_location_list) == 1:
                kind_of_action = IMPORT_ADD_TO_EXISTING
                matching_polling_location = polling_location_list[0]
                polling_location_we_vote_id = matching_polling_location.we_vote_id
            else:
                kind_of_action = CLEAN_DATA_MANUALLY
            status += "CREATE_BATCH_ROW_ACTION_POLLING_LOCATION-DUPLICATE_FOUND: " + matching_results['status'] + " "
        elif not matching_results['success']:
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_QUERY_ERROR
        else:
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_CREATE

    latitude_and_longitude_exist = latitude and latitude != "" and longitude and longitude != ""
    if keep_looking_for_duplicates and latitude_and_longitude_exist:
        matching_results = polling_location_manager.retrieve_duplicate_polling_locations(
            latitude=latitude,
            longitude=longitude,
        )
        if matching_results['polling_location_list_found']:
            polling_location_list = matching_results['polling_location_list']
            keep_looking_for_duplicates = False
            if len(polling_location_list) == 1:
                kind_of_action = IMPORT_ADD_TO_EXISTING
                matching_polling_location = polling_location_list[0]
                polling_location_we_vote_id = matching_polling_location.we_vote_id
            else:
                kind_of_action = CLEAN_DATA_MANUALLY
            status += "CREATE_BATCH_ROW_ACTION_POLLING_LOCATION-DUPLICATE_FOUND: " + matching_results['status'] + " "
        elif not matching_results['success']:
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_QUERY_ERROR
        else:
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_CREATE

    if keep_looking_for_duplicates:
        # If here we have exhausted all of the ways we look for matches, so we can assume we need to
        #  create a new entry
        kind_of_action = IMPORT_CREATE

    if kind_of_action is IMPORT_CREATE:
        # If we have lat/long, but not the other fields, retrieve the full address from Google
        if latitude_and_longitude_exist and not address_field_exists:
            results = polling_location_manager.retrieve_address_from_latitude_and_longitude(
                latitude=latitude,
                longitude=longitude)
            if results['success']:
                city = results['city']
                line1 = results['line1']
                state = results['state_code']
                zip_long = results['zip_long']

    try:
        batch_row_action_polling_location.batch_set_id = batch_description.batch_set_id
        batch_row_action_polling_location.polling_location_we_vote_id = polling_location_we_vote_id
        batch_row_action_polling_location.city = city
        batch_row_action_polling_location.county_name = county_name
        if latitude and latitude != "":
            latitude_float = float(latitude)
            batch_row_action_polling_location.latitude = latitude_float
        if longitude and longitude != "":
            longitude_float = float(longitude)
            batch_row_action_polling_location.longitude = longitude_float
        batch_row_action_polling_location.line1 = line1
        batch_row_action_polling_location.line2 = line2
        batch_row_action_polling_location.location_name = location_name
        batch_row_action_polling_location.polling_location_deleted = positive_value_exists(polling_location_deleted)
        batch_row_action_polling_location.precinct_name = precinct_name
        batch_row_action_polling_location.source_code = source_code
        batch_row_action_polling_location.state = state
        batch_row_action_polling_location.use_for_bulk_retrieve = positive_value_exists(use_for_bulk_retrieve)
        batch_row_action_polling_location.zip_long = zip_long
        batch_row_action_polling_location.kind_of_action = kind_of_action
        batch_row_action_polling_location.save()
        success = True
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_POLLING_LOCATION_UNABLE_TO_SAVE: " + str(e) + " "

    try:
        if batch_row_action_created or batch_row_action_updated:
            # If BatchRowAction was created, this batch_row was analyzed
            one_batch_row.batch_row_analyzed = True
            one_batch_row.save()
    except Exception as e:
        status += "BATCH_ROW_ACTION_POLLING_LOCATION-UNABLE_TO_SAVE_BATCH_ROW: " + str(e) + " "

    results = {
        'success': success,
        'status': status,
        'batch_row_action_created': batch_row_action_created,
        'batch_row_action_updated': batch_row_action_updated,
        'batch_row_action_polling_location': batch_row_action_polling_location,
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

    batch_row_action_created = True
    batch_row_action_updated = False
    status = ''
    success = True
    contest_office_found = False
    contest_office_we_vote_id = ""
    office_ctcl_uuid = None
    office_district_id = None

    # Does a BatchRowActionCandidate entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_candidate(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_candidate = existing_results['batch_row_action_candidate']
        batch_row_action_updated = True
    else:
        # If a BatchRowActionCandidate entry does not exist, create one
        try:
            batch_row_action_candidate = BatchRowActionCandidate.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
                batch_set_id=batch_description.batch_set_id,
            )
            batch_row_action_created = True
            status += "BATCH_ROW_ACTION_CANDIDATE_CREATED "
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_candidate = BatchRowActionCandidate()
            success = False
            status += "BATCH_ROW_ACTION_CANDIDATE_NOT_CREATED " + str(e) + " "

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_candidate': batch_row_action_candidate,
            }
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_CANDIDATES

    # Find the column in the incoming batch_row with the header == candidate_name
    ballotpedia_candidate_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_candidate_id",
                                                                           batch_header_map, one_batch_row)
    ballotpedia_candidate_name = batch_manager.retrieve_value_from_batch_row("ballotpedia_candidate_name",
                                                                             batch_header_map, one_batch_row)
    ballotpedia_candidate_summary = batch_manager.retrieve_value_from_batch_row("ballotpedia_candidate_summary",
                                                                                batch_header_map, one_batch_row)
    ballotpedia_candidate_url = batch_manager.retrieve_value_from_batch_row("ballotpedia_candidate_url",
                                                                            batch_header_map, one_batch_row)
    ballotpedia_election_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_election_id",
                                                                          batch_header_map, one_batch_row)
    ballotpedia_image_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_image_id",
                                                                       batch_header_map, one_batch_row)
    ballotpedia_office_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_office_id",
                                                                        batch_header_map, one_batch_row)
    ballotpedia_person_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_person_id",
                                                                        batch_header_map, one_batch_row)
    ballotpedia_race_id = batch_manager.retrieve_value_from_batch_row("ballotpedia_race_id",
                                                                      batch_header_map, one_batch_row)
    birth_day_text = batch_manager.retrieve_value_from_batch_row("birth_day_text", batch_header_map, one_batch_row)
    candidate_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "candidate_we_vote_id", batch_header_map, one_batch_row)
    crowdpac_candidate_id = batch_manager.retrieve_value_from_batch_row("crowdpac_candidate_id",
                                                                        batch_header_map, one_batch_row)
    candidate_name = batch_manager.retrieve_value_from_batch_row("candidate_name", batch_header_map, one_batch_row)
    if positive_value_exists(one_batch_row.google_civic_election_id):
        google_civic_election_id = str(one_batch_row.google_civic_election_id)
    else:
        google_civic_election_id = str(batch_description.google_civic_election_id)
    ctcl_uuid = batch_manager.retrieve_value_from_batch_row("candidate_ctcl_uuid", batch_header_map, one_batch_row)
    candidate_ctcl_person_id = batch_manager.retrieve_value_from_batch_row(
        "candidate_ctcl_person_id", batch_header_map, one_batch_row)
    candidate_gender = batch_manager.retrieve_value_from_batch_row("candidate_gender", batch_header_map, one_batch_row)
    contest_office_name = batch_manager.retrieve_value_from_batch_row(
        "contest_office_name", batch_header_map, one_batch_row)
    candidate_is_top_ticket = batch_manager.retrieve_value_from_batch_row(
        "candidate_is_top_ticket", batch_header_map, one_batch_row)
    candidate_is_incumbent = batch_manager.retrieve_value_from_batch_row(
        "candidate_is_incumbent", batch_header_map, one_batch_row)
    candidate_participation_status = batch_manager.retrieve_value_from_batch_row(
        "candidate_participation_status", batch_header_map, one_batch_row)
    candidate_party_name = batch_manager.retrieve_value_from_batch_row(
        "candidate_party_name", batch_header_map, one_batch_row)
    candidate_twitter_handle_raw = batch_manager.retrieve_value_from_batch_row(
        "candidate_twitter_handle", batch_header_map, one_batch_row)
    candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle_raw)
    candidate_twitter_handle_raw2 = batch_manager.retrieve_value_from_batch_row(
        "candidate_twitter_handle2", batch_header_map, one_batch_row)
    candidate_twitter_handle2 = extract_twitter_handle_from_text_string(candidate_twitter_handle_raw2)
    candidate_twitter_handle_raw3 = batch_manager.retrieve_value_from_batch_row(
        "candidate_twitter_handle3", batch_header_map, one_batch_row)
    candidate_twitter_handle3 = extract_twitter_handle_from_text_string(candidate_twitter_handle_raw3)
    candidate_url = batch_manager.retrieve_value_from_batch_row("candidate_url", batch_header_map, one_batch_row)
    candidate_contact_form_url = batch_manager.retrieve_value_from_batch_row(
        "candidate_contact_form_url", batch_header_map, one_batch_row)
    facebook_url = batch_manager.retrieve_value_from_batch_row("facebook_url", batch_header_map, one_batch_row)
    candidate_email = batch_manager.retrieve_value_from_batch_row("candidate_email", batch_header_map, one_batch_row)
    candidate_profile_image_url = batch_manager.retrieve_value_from_batch_row(
        "candidate_profile_image_url", batch_header_map, one_batch_row)
    photo_url_from_ctcl = batch_manager.retrieve_value_from_batch_row(
        "photo_url_from_ctcl", batch_header_map, one_batch_row)
    photo_url_from_vote_usa = batch_manager.retrieve_value_from_batch_row(
        "photo_url_from_vote_usa", batch_header_map, one_batch_row)
    state_code = batch_manager.retrieve_value_from_batch_row("state_code", batch_header_map, one_batch_row)
    candidate_temp_id = batch_manager.retrieve_value_from_batch_row(
        "candidate_batch_id", batch_header_map, one_batch_row)  # TODO Is the name transformation correct?

    vote_usa_office_id = batch_manager.retrieve_value_from_batch_row(
        "voteusa office id", batch_header_map, one_batch_row)
    vote_usa_politician_id = batch_manager.retrieve_value_from_batch_row(
        "voteusa id", batch_header_map, one_batch_row)
    vote_usa_candidate_name = batch_manager.retrieve_value_from_batch_row(
        "candidate", batch_header_map, one_batch_row)
    vote_usa_state_code = batch_manager.retrieve_value_from_batch_row(
        "state code", batch_header_map, one_batch_row)
    vote_usa_profile_image_url_https = batch_manager.retrieve_value_from_batch_row(
        "photo300 url", batch_header_map, one_batch_row)
    vote_usa_party_name = batch_manager.retrieve_value_from_batch_row(
        "party", batch_header_map, one_batch_row)
    vote_usa_candidate_email = batch_manager.retrieve_value_from_batch_row(
        "email", batch_header_map, one_batch_row)
    vote_usa_candidate_url = batch_manager.retrieve_value_from_batch_row(
        "website url", batch_header_map, one_batch_row)
    vote_usa_facebook_url = batch_manager.retrieve_value_from_batch_row(
        "facebook url", batch_header_map, one_batch_row)
    vote_usa_candidate_twitter_url = batch_manager.retrieve_value_from_batch_row(
        "twitter url", batch_header_map, one_batch_row)
    vote_usa_ballotpedia_candidate_url = batch_manager.retrieve_value_from_batch_row(
        "ballotpedia url", batch_header_map, one_batch_row)

    # get batch_set_id from batch_description
    batch_set_id = str(batch_description.batch_set_id)
    # Look up batch_description with the given batch_set_id and kind_of_batch as CANDIDATE, get batch_header_id
    contest_office_batch_header_id = get_batch_header_id_from_batch_description(batch_set_id, CONTEST_OFFICE)

    if not positive_value_exists(state_code):
        if positive_value_exists(vote_usa_state_code):
            state_code = vote_usa_state_code

    # state_code lookup from the election
    if positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code):
        # Check to see if there is a state served for the election
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            state_code = election.state_code

    # state code look up: BatchRowActionContestOffice entry stores candidate_selection_ids.
    #  Get the state code and office from matching
    # candidate_selection_id BatchRowActionContestOffice entry. Eg: looking for 'can1' in candidate_selection_ids 1-10
    if positive_value_exists(candidate_temp_id):
        try:
            batch_row_action_contest_office_query = BatchRowActionContestOffice.objects.all()
            batch_row_action_contest_office_query = batch_row_action_contest_office_query.filter(
                batch_header_id=contest_office_batch_header_id)
            batch_row_action_contest_office_query = batch_row_action_contest_office_query.filter(
                Q(candidate_selection_id1__iexact=candidate_temp_id) |
                Q(candidate_selection_id2__iexact=candidate_temp_id) |
                Q(candidate_selection_id3__iexact=candidate_temp_id) |
                Q(candidate_selection_id4__iexact=candidate_temp_id) |
                Q(candidate_selection_id5__iexact=candidate_temp_id) |
                Q(candidate_selection_id6__iexact=candidate_temp_id) |
                Q(candidate_selection_id7__iexact=candidate_temp_id) |
                Q(candidate_selection_id8__iexact=candidate_temp_id) |
                Q(candidate_selection_id9__iexact=candidate_temp_id) |
                Q(candidate_selection_id10__iexact=candidate_temp_id))
            batch_row_action_contest_office_list = list(batch_row_action_contest_office_query)
            if len(batch_row_action_contest_office_list):
                state_code = batch_row_action_contest_office_list[0].state_code
                office_ctcl_uuid = batch_row_action_contest_office_list[0].ctcl_uuid
                office_district_id = batch_row_action_contest_office_list[0].district_id
                contest_office_batch_row_action_lookup_done = True
        except BatchRowActionContestOffice.DoesNotExist:
            status = "BATCH_ROW_ACTION_CANDIDATE-CONTEST_OFFICE_NOT_FOUND"
            pass

    # if google_civic_election_id is null, look up using state_code and/or election_day
    if not positive_value_exists(google_civic_election_id):
        election_day = batch_manager.retrieve_value_from_batch_row("election_day", batch_header_map, one_batch_row)
        election_results = batch_manager.retrieve_election_details_from_election_day_or_state_code(
            election_day, state_code)
        if election_results['success']:
            google_civic_election_id = election_results['google_civic_election_id']

    # Look up CandidateCampaign to see if an entry exists
    # These three parameters are needed to look up in OfficeHeld table for a match
    keep_looking_for_duplicates = True
    kind_of_action = IMPORT_TO_BE_DETERMINED
    candidate_list_manager = CandidateListManager()
    candidate_manager = CandidateManager()
    if positive_value_exists(candidate_we_vote_id):
        # If here, then we are updating an existing known record
        keep_looking_for_duplicates = False
        kind_of_action = IMPORT_ADD_TO_EXISTING
        # TODO We want to search the Candidate table for the existing record with this candidate_we_vote_id
        # candidate_found = True

    if not positive_value_exists(candidate_name) and positive_value_exists(ballotpedia_candidate_name):
        candidate_name = ballotpedia_candidate_name

    if not positive_value_exists(candidate_name) and positive_value_exists(vote_usa_candidate_name):
        candidate_name = vote_usa_candidate_name

    if keep_looking_for_duplicates and positive_value_exists(ballotpedia_candidate_id):
        matching_results = candidate_manager.retrieve_candidate_from_ballotpedia_candidate_id(
            ballotpedia_candidate_id, read_only=False)
        if matching_results['candidate_found']:
            candidate = matching_results['candidate']
            candidate_found = True
            keep_looking_for_duplicates = False
            candidate_we_vote_id = candidate.we_vote_id
            contest_office_we_vote_id = candidate.contest_office_we_vote_id
            kind_of_action = IMPORT_ADD_TO_EXISTING
        elif matching_results['MultipleObjectsReturned']:
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_TO_BE_DETERMINED
            status += "MORE_THAN_ONE_CANDIDATE_WITH_SAME_BALLOTPEDIA_CANDIDATE_ID2 ("
            status += str(ballotpedia_candidate_id)
            status += ") "

    if keep_looking_for_duplicates and positive_value_exists(google_civic_election_id) and \
            positive_value_exists(vote_usa_politician_id) and positive_value_exists(vote_usa_office_id):
        matching_results = candidate_manager.retrieve_candidate_from_vote_usa_variables(
            vote_usa_office_id=vote_usa_office_id,
            vote_usa_politician_id=vote_usa_politician_id,
            google_civic_election_id=google_civic_election_id,
            read_only=False)
        if matching_results['candidate_found']:
            candidate = matching_results['candidate']
            candidate_found = True
            keep_looking_for_duplicates = False
            candidate_we_vote_id = candidate.we_vote_id
            contest_office_we_vote_id = candidate.contest_office_we_vote_id
            kind_of_action = IMPORT_ADD_TO_EXISTING
        elif matching_results['MultipleObjectsReturned']:
            keep_looking_for_duplicates = False
            kind_of_action = IMPORT_TO_BE_DETERMINED
            status += matching_results['status']
            status += "MORE_THAN_ONE_CANDIDATE_WITH_SAME_VOTE_USA_IDS ("
            status += str(vote_usa_politician_id)
            status += ") "

    # ######################################
    # Retrieve from non-unique variables
    # We don't want to use this routine if we have a ballotpedia_candidate_id
    if keep_looking_for_duplicates and not positive_value_exists(ballotpedia_candidate_id):
        google_civic_election_id_list = [google_civic_election_id]
        matching_results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
            google_civic_election_id_list=google_civic_election_id_list,
            state_code=state_code,
            candidate_twitter_handle=candidate_twitter_handle,
            candidate_twitter_handle2=candidate_twitter_handle2,
            candidate_twitter_handle3=candidate_twitter_handle3,
            candidate_name=candidate_name,
            read_only=True)

        if matching_results['candidate_found']:
            candidate = matching_results['candidate']
            candidate_found = True
            keep_looking_for_duplicates = False
            candidate_we_vote_id = candidate.we_vote_id
            contest_office_we_vote_id = candidate.contest_office_we_vote_id
            kind_of_action = IMPORT_ADD_TO_EXISTING
        elif matching_results['multiple_entries_found']:
            keep_looking_for_duplicates = False
            kind_of_action = CLEAN_DATA_MANUALLY
            status += "CREATE_BATCH_ROW_ACTION_CANDIDATE-MULTIPLE_CANDIDATES_FOUND: " + matching_results['status'] + " "
        elif not matching_results['success']:
            kind_of_action = IMPORT_QUERY_ERROR
        else:
            kind_of_action = IMPORT_CREATE

    if keep_looking_for_duplicates:
        # If here we have exhausted all of the ways we look for candidate matches, so we can assume we need to
        #  create a new candidate
        kind_of_action = IMPORT_CREATE

    # ###############################
    # Now we need to find the Contest Office this Candidate should be connected with
    contest_office_id = 0
    contest_manager = ContestOfficeManager()
    if positive_value_exists(contest_office_we_vote_id):
        election_id_matches = True
        # Look up the contest_office information
        contest_results = contest_manager.retrieve_contest_office_from_we_vote_id(contest_office_we_vote_id)
        if contest_results['contest_office_found']:
            contest_office = contest_results['contest_office']
            if positive_value_exists(google_civic_election_id):
                google_civic_election_id_integer = convert_to_int(google_civic_election_id)
                office_google_civic_election_id = convert_to_int(contest_office.google_civic_election_id)
                # Make sure the contest office linked to this candidate is for *this* election
                if office_google_civic_election_id is not google_civic_election_id_integer:
                    # If this candidate is linked to an office for another election, force this script to look for
                    #  the correct contest_office below
                    election_id_matches = False
            if election_id_matches:
                contest_office_name = contest_office.office_name
                contest_office_we_vote_id = contest_office.we_vote_id
                contest_office_id = contest_office.id
                contest_office_found = True

    if not positive_value_exists(contest_office_found) and positive_value_exists(ballotpedia_race_id) \
            and positive_value_exists(google_civic_election_id):
        # Look up the contest_office information with the ballotpedia_race_id
        contest_results = contest_manager.retrieve_contest_office_from_ballotpedia_race_id(
            ballotpedia_race_id, google_civic_election_id)
        if contest_results['contest_office_found']:
            contest_office = contest_results['contest_office']
            contest_office_name = contest_office.office_name
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_id = contest_office.id
            contest_office_found = True
        else:
            status += contest_results['status']

    if not positive_value_exists(contest_office_found) and positive_value_exists(office_ctcl_uuid):
        # Look up the contest_office information with the ctcl_uuid
        contest_results = contest_manager.retrieve_contest_office_from_ctcl_uuid(office_ctcl_uuid)
        if contest_results['contest_office_found']:
            contest_office = contest_results['contest_office']
            contest_office_name = contest_office.office_name
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_id = contest_office.id
            contest_office_found = True

    if not positive_value_exists(contest_office_found) and positive_value_exists(google_civic_election_id) and \
            positive_value_exists(vote_usa_office_id):
        # Look up the contest_office information with the vote_usa_office_id
        contest_results = contest_manager.retrieve_contest_office(
            google_civic_election_id=google_civic_election_id,
            vote_usa_office_id=vote_usa_office_id)
        if contest_results['contest_office_found']:
            contest_office = contest_results['contest_office']
            contest_office_name = contest_office.office_name
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_id = contest_office.id
            contest_office_found = True

    if not positive_value_exists(contest_office_found):
        # Find the office even though we haven't found candidate
        contest_office_list_manager = ContestOfficeListManager()
        matching_results = contest_office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
            contest_office_name=contest_office_name,
            google_civic_election_id=google_civic_election_id,
            incoming_state_code=state_code,
            district_id=office_district_id,
            read_only=True)
        if matching_results['contest_office_found']:
            contest_office = matching_results['contest_office']
            contest_office_name = contest_office.office_name
            contest_office_we_vote_id = contest_office.we_vote_id
            contest_office_id = contest_office.id
        else:
            if kind_of_action == IMPORT_CREATE:
                status += "MISSING_VALID_OFFICE_ENTRY "
                kind_of_action = IMPORT_TO_BE_DETERMINED

    # TODO Other checks:
    #   Does the office match?

    # If we are missing required variables, don't create
    if kind_of_action == IMPORT_CREATE:
        if not positive_value_exists(candidate_name) or not positive_value_exists(state_code) or not \
                positive_value_exists(google_civic_election_id) or not positive_value_exists(contest_office_we_vote_id):
            kind_of_action = IMPORT_TO_BE_DETERMINED
            status += "COULD_NOT_CREATE_CANDIDATE_ENTRY-MISSING_REQUIRED_VARIABLES "

    # Save the data into BatchRowActionCandidate
    try:
        batch_row_action_candidate.batch_set_id = batch_description.batch_set_id
        batch_row_action_candidate.ballotpedia_candidate_id = convert_to_int(ballotpedia_candidate_id)
        batch_row_action_candidate.ballotpedia_candidate_name = ballotpedia_candidate_name
        batch_row_action_candidate.ballotpedia_candidate_summary = ballotpedia_candidate_summary
        if positive_value_exists(vote_usa_ballotpedia_candidate_url):
            batch_row_action_candidate.ballotpedia_candidate_url = vote_usa_ballotpedia_candidate_url
        else:
            batch_row_action_candidate.ballotpedia_candidate_url = ballotpedia_candidate_url
        batch_row_action_candidate.ballotpedia_office_id = convert_to_int(ballotpedia_office_id)
        batch_row_action_candidate.ballotpedia_person_id = convert_to_int(ballotpedia_person_id)
        batch_row_action_candidate.ballotpedia_race_id = convert_to_int(ballotpedia_race_id)
        batch_row_action_candidate.ballotpedia_election_id = convert_to_int(ballotpedia_election_id)
        batch_row_action_candidate.ballotpedia_image_id = convert_to_int(ballotpedia_image_id)
        batch_row_action_candidate.batch_row_action_office_ctcl_uuid = office_ctcl_uuid
        batch_row_action_candidate.birth_day_text = birth_day_text
        batch_row_action_candidate.candidate_ctcl_person_id = candidate_ctcl_person_id
        if positive_value_exists(vote_usa_candidate_email):
            batch_row_action_candidate.candidate_email = vote_usa_candidate_email
        else:
            batch_row_action_candidate.candidate_email = candidate_email
        batch_row_action_candidate.candidate_gender = candidate_gender
        if candidate_is_incumbent is not None and positive_value_exists(candidate_is_incumbent):
            batch_row_action_candidate.candidate_is_incumbent = True
        else:
            batch_row_action_candidate.candidate_is_incumbent = False
        if candidate_is_top_ticket is not None and positive_value_exists(candidate_is_top_ticket):
            batch_row_action_candidate.candidate_is_top_ticket = True
        else:
            batch_row_action_candidate.candidate_is_top_ticket = False
        batch_row_action_candidate.candidate_name = candidate_name
        batch_row_action_candidate.candidate_participation_status = candidate_participation_status
        if positive_value_exists(vote_usa_candidate_url):
            vote_usa_candidate_twitter_handle = extract_twitter_handle_from_text_string(vote_usa_candidate_twitter_url)
            batch_row_action_candidate.candidate_twitter_handle = vote_usa_candidate_twitter_handle
        else:
            batch_row_action_candidate.candidate_twitter_handle = candidate_twitter_handle
        batch_row_action_candidate.candidate_twitter_handle2 = candidate_twitter_handle2
        batch_row_action_candidate.candidate_twitter_handle3 = candidate_twitter_handle3
        if positive_value_exists(vote_usa_candidate_url):
            batch_row_action_candidate.candidate_url = vote_usa_candidate_url
        else:
            batch_row_action_candidate.candidate_url = candidate_url
        batch_row_action_candidate.candidate_contact_form_url = candidate_contact_form_url
        batch_row_action_candidate.candidate_we_vote_id = candidate_we_vote_id
        batch_row_action_candidate.contest_office_name = contest_office_name
        batch_row_action_candidate.contest_office_we_vote_id = contest_office_we_vote_id
        batch_row_action_candidate.contest_office_id = contest_office_id
        batch_row_action_candidate.crowdpac_candidate_id = convert_to_int(crowdpac_candidate_id)
        batch_row_action_candidate.ctcl_uuid = ctcl_uuid
        if positive_value_exists(vote_usa_facebook_url):
            batch_row_action_candidate.facebook_url = vote_usa_facebook_url
        else:
            batch_row_action_candidate.facebook_url = facebook_url
        batch_row_action_candidate.kind_of_action = kind_of_action
        batch_row_action_candidate.google_civic_election_id = google_civic_election_id
        if positive_value_exists(vote_usa_party_name):
            batch_row_action_candidate.party = vote_usa_party_name
        else:
            batch_row_action_candidate.party = candidate_party_name
        batch_row_action_candidate.photo_url = candidate_profile_image_url
        batch_row_action_candidate.photo_url_from_ctcl = photo_url_from_ctcl
        batch_row_action_candidate.photo_url_from_vote_usa = photo_url_from_vote_usa
        batch_row_action_candidate.state_code = state_code
        batch_row_action_candidate.status = status
        batch_row_action_candidate.vote_usa_office_id = vote_usa_office_id
        batch_row_action_candidate.vote_usa_politician_id = vote_usa_politician_id
        batch_row_action_candidate.vote_usa_profile_image_url_https = vote_usa_profile_image_url_https
        batch_row_action_candidate.save()
    except Exception as e:
        status += "BATCH_ROW_ACTION_CANDIDATE_UNABLE_TO_SAVE: " + str(e) + " "
        success = False

    # If a state was figured out, then update the batch_row with the state_code so we can use that for filtering
    if positive_value_exists(state_code):
        try:
            if batch_row_action_created or batch_row_action_updated:
                # If BatchRowAction was created, this batch_row was analyzed
                one_batch_row.batch_row_analyzed = True
            one_batch_row.state_code = state_code
            one_batch_row.save()
        except Exception as e:
            status += "BATCH_ROW_ACTION_STATE_UNABLE_TO_SAVE: " + str(e) + " "
            success = False

    results = {
        'success':                      success,
        'status':                       status,
        'batch_row_action_updated':     batch_row_action_updated,
        'batch_row_action_created':     batch_row_action_created,
        'batch_row_action_candidate':   batch_row_action_candidate,
    }
    return results


def create_batch_row_action_position(batch_description, batch_header_map, one_batch_row):
    """

    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :return:
    """
    batch_manager = BatchManager()
    status = ""
    organization_found = False
    organization_id = 0
    batch_row_action_updated = False
    batch_row_action_created = False
    keep_looking_for_duplicates = True
    candidate_found = False
    contest_office_we_vote_id = ""
    measure_found = False
    contest_measure_id = 0
    contest_measure_we_vote_id = ""

    # Does a BatchRowActionPosition entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_position(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_position = existing_results['batch_row_action_position']
        batch_row_action_updated = True
    else:
        # If a BatchRowActionOrganization entry does not exist, create one
        try:
            batch_row_action_position = BatchRowActionPosition.objects.create(
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
                batch_set_id=batch_description.batch_set_id,
            )
            batch_row_action_created = True
            success = True
            status = "BATCH_ROW_ACTION_POSITION_CREATED "
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_position = None
            batch_row_action_updated = False
            success = False
            status = "BATCH_ROW_ACTION_POSITION_NOT_CREATED: " + str(e) + " "

            results = {
                'success': success,
                'status': status,
                'batch_row_action_updated': batch_row_action_updated,
                'batch_row_action_created': batch_row_action_created,
                'batch_row_action_position': batch_row_action_position,
            }
            return results

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_POSITIONS

    position_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "position_we_vote_id", batch_header_map, one_batch_row)
    candidate_name = batch_manager.retrieve_value_from_batch_row(
        "candidate_name", batch_header_map, one_batch_row)
    candidate_twitter_handle_raw = batch_manager.retrieve_value_from_batch_row(
        "candidate_twitter_handle", batch_header_map, one_batch_row)
    candidate_twitter_handle = extract_twitter_handle_from_text_string(candidate_twitter_handle_raw)
    candidate_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "candidate_we_vote_id", batch_header_map, one_batch_row)
    contest_office_name = batch_manager.retrieve_value_from_batch_row(
        "contest_office_name", batch_header_map, one_batch_row)
    contest_measure_title = batch_manager.retrieve_value_from_batch_row(
        "contest_measure_title", batch_header_map, one_batch_row)
    measure_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "measure_we_vote_id", batch_header_map, one_batch_row)
    more_info_url = batch_manager.retrieve_value_from_batch_row("more_info_url", batch_header_map, one_batch_row)
    statement_text = batch_manager.retrieve_value_from_batch_row("statement_text", batch_header_map, one_batch_row)
    stance = batch_manager.retrieve_value_from_batch_row("stance", batch_header_map, one_batch_row)
    if stance.lower() not in ('info_only', 'no_stance', 'oppose', 'percent_rating', 'still_deciding', 'support'):
        support = batch_manager.retrieve_value_from_batch_row("support", batch_header_map, one_batch_row)
        oppose = batch_manager.retrieve_value_from_batch_row("oppose", batch_header_map, one_batch_row)
        if positive_value_exists(oppose):
            stance = OPPOSE
        elif positive_value_exists(support):
            stance = SUPPORT
        elif positive_value_exists(statement_text):
            stance = INFORMATION_ONLY
        else:
            # If no stance was provided, and no statement_text, we default to a "Support" stance
            stance = SUPPORT

    organization_name = batch_manager.retrieve_value_from_batch_row(
        "organization_name", batch_header_map, one_batch_row)
    organization_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "organization_we_vote_id", batch_header_map, one_batch_row)
    organization_twitter_handle_raw = batch_manager.retrieve_value_from_batch_row(
        "organization_twitter_handle", batch_header_map, one_batch_row)
    organization_twitter_handle = extract_twitter_handle_from_text_string(organization_twitter_handle_raw)
    if positive_value_exists(one_batch_row.google_civic_election_id):
        google_civic_election_id = str(one_batch_row.google_civic_election_id)
    else:
        google_civic_election_id = str(batch_description.google_civic_election_id)

    state_code = batch_manager.retrieve_value_from_batch_row("state_code", batch_header_map, one_batch_row)

    if not positive_value_exists(google_civic_election_id):
        # look up google_civic_election_id using state and election_day
        election_day = batch_manager.retrieve_value_from_batch_row("election_day", batch_header_map, one_batch_row)
        election_results = batch_manager.retrieve_election_details_from_election_day_or_state_code(
            election_day, state_code, read_only=False)
        if election_results['success']:
            google_civic_election_id = election_results['google_civic_election_id']
            # election_name = election_results['election_name']

    if positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code):
        # Check to see if there is a state served for the election
        election_manager = ElectionManager()
        results = election_manager.retrieve_election(google_civic_election_id)
        if results['election_found']:
            election = results['election']
            state_code = election.state_code

    # get org we_vote_id from batch_description for org endorsement import
    if not positive_value_exists(organization_we_vote_id) and \
            positive_value_exists(batch_description.organization_we_vote_id):
        organization_we_vote_id = batch_description.organization_we_vote_id
    # Find the organization
    if positive_value_exists(organization_we_vote_id):
        # If here, then we are updating an existing known record
        organization_manager = OrganizationManager()
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
        if organization_results['organization_found']:
            organization_found = True
            organization = organization_results['organization']
            organization_we_vote_id = organization.we_vote_id
            organization_id = organization.id
            organization_name = organization.organization_name
        else:
            status += "ORGANIZATION_NOT_FOUND_BY_WE_VOTE_ID "

    if not organization_found and positive_value_exists(organization_twitter_handle):
        organization_list_manager = OrganizationListManager()
        matching_results = organization_list_manager.retrieve_organizations_from_twitter_handle(
            twitter_handle=organization_twitter_handle, read_only=True)

        if matching_results['organization_found']:
            organization_found = True
            organization = matching_results['organization']
            organization_we_vote_id = organization.we_vote_id
            organization_id = organization.id
            organization_name = organization.organization_name
        elif matching_results['multiple_entries_found']:
            status += "MULTIPLE_POSITIONS_FOUND "
        else:
            status += matching_results['status']

    position_manager = PositionManager()
    if positive_value_exists(position_we_vote_id):
        # If here, then we are updating an existing known record
        keep_looking_for_duplicates = False
        kind_of_action = IMPORT_ADD_TO_EXISTING
        position_results = position_manager.retrieve_position_from_we_vote_id(position_we_vote_id)
        if position_results['position_found']:
            position = position_results['position']

    if not organization_found:
        # If an organization is not found, there is no use trying to find the position
        keep_looking_for_duplicates = False

    # By here, we should have the organization (owner of the position) and the election
    # NEXT: figure out what candidate/office the endorsement is for
    contest_office_manager = ContestOfficeManager()
    if positive_value_exists(candidate_we_vote_id):
        candidate_manager = CandidateManager()
        candidate_results = candidate_manager.retrieve_candidate_from_we_vote_id(candidate_we_vote_id, read_only=True)

        if candidate_results['candidate_found']:
            candidate = candidate_results['candidate']
            candidate_found = True
            candidate_we_vote_id = candidate.we_vote_id
            candidate_id = candidate.id
            office_results = \
                retrieve_next_or_most_recent_office_for_candidate(candidate_we_vote_id=candidate_we_vote_id)
            if office_results['contest_office_found']:
                contest_office = office_results['contest_office']
                contest_office_we_vote_id = contest_office.we_vote_id
                contest_office_name = contest_office.office_name
                google_civic_election_id = contest_office.google_civic_election_id
        else:
            status += candidate_results['status']
    elif positive_value_exists(measure_we_vote_id):
        contest_measure_manager = ContestMeasureManager()
        measure_results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(measure_we_vote_id)

        if measure_results['contest_measure_found']:
            measure = measure_results['contest_measure']
            measure_found = True
            contest_measure_we_vote_id = measure.we_vote_id
            contest_measure_id = measure.id
            contest_measure_title = measure.measure_title
            if not positive_value_exists(google_civic_election_id) and positive_value_exists(measure_we_vote_id):
                google_civic_election_id = \
                    contest_measure_manager.fetch_google_civic_election_id_from_measure_we_vote_id(
                        measure_we_vote_id)
        else:
            status += measure_results['status']
    elif positive_value_exists(candidate_twitter_handle) or positive_value_exists(candidate_name):
        candidate_list_manager = CandidateListManager()
        google_civic_election_id_list = [google_civic_election_id]
        matching_results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
            google_civic_election_id_list=google_civic_election_id_list,
            state_code=state_code,
            candidate_twitter_handle=candidate_twitter_handle,
            candidate_name=candidate_name,
            read_only=True)

        if matching_results['candidate_found']:
            candidate = matching_results['candidate']
            candidate_found = True
            candidate_we_vote_id = candidate.we_vote_id
            candidate_id = candidate.id
            office_results = \
                retrieve_next_or_most_recent_office_for_candidate(candidate_we_vote_id=candidate_we_vote_id)
            if office_results['contest_office_found']:
                contest_office = office_results['contest_office']
                contest_office_we_vote_id = contest_office.we_vote_id
                contest_office_name = contest_office.office_name
                google_civic_election_id = contest_office.google_civic_election_id
        elif matching_results['multiple_entries_found']:
            # Note: In some jurisdictions like NY, they list one candidate with multiple parties.
            #  We therefore have to store multiple candidates with the same name in these cases.
            status += "CREATE_BATCH_ROW_ACTION_POSITION-MULTIPLE_CANDIDATES_FOUND "
            if matching_results['candidate_list_found']:
                # NOTE: It would be better if we matched to multiple candidates, instead of just the first one
                candidate_list = matching_results['candidate_list']
                candidate = candidate_list[0]
                candidate_found = True
                candidate_we_vote_id = candidate.we_vote_id
                candidate_id = candidate.id
                office_results = \
                    retrieve_next_or_most_recent_office_for_candidate(candidate_we_vote_id=candidate_we_vote_id)
                if office_results['contest_office_found']:
                    contest_office = office_results['contest_office']
                    contest_office_we_vote_id = contest_office.we_vote_id
                    contest_office_name = contest_office.office_name
                    google_civic_election_id = contest_office.google_civic_election_id
        elif not matching_results['success']:
            status += matching_results['status']
        else:
            pass
    elif positive_value_exists(contest_measure_title):
        contest_measure_list_manager = ContestMeasureListManager()
        google_civic_election_id_list = [google_civic_election_id]
        matching_results = contest_measure_list_manager.retrieve_contest_measures_from_non_unique_identifiers(
            google_civic_election_id_list, state_code, contest_measure_title)

        if matching_results['contest_measure_found']:
            measure = matching_results['contest_measure']
            measure_found = True
            contest_measure_we_vote_id = measure.we_vote_id
            contest_measure_id = measure.id
            if not positive_value_exists(google_civic_election_id):
                google_civic_election_id = measure.google_civic_election_d
        elif matching_results['multiple_entries_found']:
            status += "MULTIPLE_MEASURES_FOUND "
        elif not matching_results['success']:
            status += matching_results['status']
        else:
            pass

    if keep_looking_for_duplicates:
        if candidate_found and organization_found:
            position_results = \
                position_manager.retrieve_organization_candidate_position_with_we_vote_id(
                    organization_id, candidate_we_vote_id, google_civic_election_id)
            if position_results['position_found']:
                position = position_results['position']
                position_we_vote_id = position.we_vote_id
        elif measure_found and organization_found:
            position_results = \
                position_manager.retrieve_organization_contest_measure_position_with_we_vote_id(
                    organization_id, contest_measure_we_vote_id, google_civic_election_id)
            if position_results['position_found']:
                position = position_results['position']
                position_we_vote_id = position.we_vote_id

    if positive_value_exists(candidate_name):
        ballot_item_display_name = candidate_name
        # Note organization_name becomes speaker_display_name below
        variables_found_to_create_position = positive_value_exists(ballot_item_display_name) \
            and positive_value_exists(candidate_found) \
            and positive_value_exists(organization_name) \
            and positive_value_exists(organization_we_vote_id) \
            and positive_value_exists(stance)
        # and positive_value_exists(contest_office_name) \
        # and positive_value_exists(contest_office_we_vote_id) \
        if not variables_found_to_create_position:
            status += "CANDIDATE-MISSING_VARIABLES_REQUIRED_TO_CREATE "
            if not positive_value_exists(ballot_item_display_name):
                status += " ballot_item_display_name "
            if not positive_value_exists(candidate_found):
                status += " candidate_found "
            if not positive_value_exists(contest_office_name):
                status += " contest_office_name "
            if not positive_value_exists(contest_office_we_vote_id):
                status += " contest_office_we_vote_id "
            if not positive_value_exists(organization_name):
                status += " organization_name "
            if not positive_value_exists(organization_we_vote_id):
                status += " organization_we_vote_id "
            if not positive_value_exists(stance):
                status += " stance "
    elif positive_value_exists(contest_measure_we_vote_id):
        ballot_item_display_name = contest_measure_title
        # Note organization_name becomes speaker_display_name below
        variables_found_to_create_position = positive_value_exists(ballot_item_display_name) \
            and positive_value_exists(organization_name) \
            and positive_value_exists(organization_we_vote_id) \
            and positive_value_exists(stance)
        if not variables_found_to_create_position:
            status += "MEASURE_WE_VOTE_ID-MISSING_VARIABLES_REQUIRED_TO_CREATE "
            if not positive_value_exists(ballot_item_display_name):
                status += " ballot_item_display_name "
            if not positive_value_exists(organization_name):
                status += " organization_name "
            if not positive_value_exists(organization_we_vote_id):
                status += " organization_we_vote_id "
            if not positive_value_exists(stance):
                status += " stance "
    elif contest_measure_title:
        ballot_item_display_name = contest_measure_title
        # Note organization_name becomes speaker_display_name below
        variables_found_to_create_position = positive_value_exists(ballot_item_display_name) \
            and positive_value_exists(contest_measure_we_vote_id) \
            and positive_value_exists(organization_name) \
            and positive_value_exists(organization_we_vote_id) \
            and positive_value_exists(stance)
        if not variables_found_to_create_position:
            status += "MEASURE-MISSING_VARIABLES_REQUIRED_TO_CREATE "
            if not positive_value_exists(ballot_item_display_name):
                status += " ballot_item_display_name "
            if not positive_value_exists(contest_measure_we_vote_id):
                status += " contest_measure_we_vote_id "
            if not positive_value_exists(organization_name):
                status += " organization_name "
            if not positive_value_exists(organization_we_vote_id):
                status += " organization_we_vote_id "
            if not positive_value_exists(stance):
                status += " stance "
    else:
        ballot_item_display_name = ""
        variables_found_to_create_position = False
        status += "MISSING_CANDIDATE_OR_MEASURE_REQUIRED_TO_CREATE "

    if positive_value_exists(position_we_vote_id):
        kind_of_action = IMPORT_ADD_TO_EXISTING
    elif positive_value_exists(variables_found_to_create_position):
        kind_of_action = IMPORT_CREATE
    else:
        kind_of_action = IMPORT_TO_BE_DETERMINED
        print_to_log(logger=logger, exception_message_optional=status)

    try:
        batch_row_action_position.batch_set_id = batch_description.batch_set_id
        batch_row_action_position.position_we_vote_id = position_we_vote_id
        batch_row_action_position.ballot_item_display_name = ballot_item_display_name
        batch_row_action_position.candidate_campaign_we_vote_id = candidate_we_vote_id
        # batch_row_action_position.candidate_campaign_id = candidate_id
        batch_row_action_position.contest_office_name = contest_office_name
        batch_row_action_position.contest_office_we_vote_id = contest_office_we_vote_id
        # batch_row_action_position.contest_office_id = contest_office_id
        batch_row_action_position.contest_measure_we_vote_id = contest_measure_we_vote_id
        batch_row_action_position.contest_measure_id = contest_measure_id
        batch_row_action_position.google_civic_election_id = google_civic_election_id
        batch_row_action_position.more_info_url = more_info_url
        batch_row_action_position.stance = stance
        batch_row_action_position.statement_text = statement_text
        batch_row_action_position.state_code = state_code
        batch_row_action_position.speaker_display_name = organization_name
        batch_row_action_position.speaker_twitter_handle = organization_twitter_handle
        # batch_row_action_position.organization_id = organization_id
        batch_row_action_position.organization_we_vote_id = organization_we_vote_id
        batch_row_action_position.kind_of_action = kind_of_action
        batch_row_action_position.status = status
        batch_row_action_position.save()
        success = True
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_POSITION_UNABLE_TO_SAVE: " + str(e) + ' '
        batch_row_action_updated = False

    try:
        if batch_row_action_created or batch_row_action_updated:
            # If BatchRowAction was created, this batch_row was analyzed
            one_batch_row.batch_row_analyzed = True
            one_batch_row.save()
    except Exception as e:
        status += "CANNOT_SAVE_ONE_BATCH_ROW: " + str(e) + ' '
        success = False

    results = {
        'success': success,
        'status': status,
        'batch_row_action_created': batch_row_action_created,
        'batch_row_action_updated': batch_row_action_updated,
        'batch_row_action_position': batch_row_action_position,
    }
    return results


def create_batch_row_action_ballot_item(batch_description,
                                        batch_header_map,
                                        one_batch_row,
                                        election_objects_dict={},
                                        measure_objects_dict={},
                                        office_objects_dict={}):
    """
    Handle batch_row for ballot_item type
    :param batch_description:
    :param batch_header_map:
    :param one_batch_row:
    :param election_objects_dict:
    :param measure_objects_dict:
    :param office_objects_dict:
    :return:
    """
    batch_manager = BatchManager()

    batch_row_action_created = False
    batch_row_action_updated = False
    status = ''
    status += 'CREATE_BATCH_ROW_ACTION_BALLOT_ITEM-START '
    success = True
    existing_ballot_item_id = 0
    existing_ballot_item_found = False
    contest_measure_text = ""
    contest_measure_url = ""
    yes_vote_description = ""
    no_vote_description = ""

    if positive_value_exists(one_batch_row.google_civic_election_id):
        google_civic_election_id = str(one_batch_row.google_civic_election_id)
    else:
        google_civic_election_id = str(batch_description.google_civic_election_id)

    # Gather information in advance, so we can try to only do a single create (and avoid another save if we can help it)

    # NOTE: If you add incoming header names here, make sure to update BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS
    # These are variables that might come from an import file, and are used to identify which
    #  ballot item to add to a map point
    polling_location_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "polling_location_we_vote_id", batch_header_map, one_batch_row)
    contest_office_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "contest_office_we_vote_id", batch_header_map, one_batch_row)
    contest_office_name = batch_manager.retrieve_value_from_batch_row(
        "contest_office_name", batch_header_map, one_batch_row)
    candidate_name = batch_manager.retrieve_value_from_batch_row("candidate_name", batch_header_map, one_batch_row)
    candidate_twitter_handle = batch_manager.retrieve_value_from_batch_row(
        "candidate_twitter_handle", batch_header_map, one_batch_row)
    contest_measure_we_vote_id = batch_manager.retrieve_value_from_batch_row(
        "contest_measure_we_vote_id", batch_header_map, one_batch_row)
    # Used for matching only
    contest_measure_name = batch_manager.retrieve_value_from_batch_row(
        "contest_measure_name", batch_header_map, one_batch_row)
    local_ballot_order = batch_manager.retrieve_value_from_batch_row(
        "local_ballot_order", batch_header_map, one_batch_row)
    local_ballot_order = convert_to_int(local_ballot_order)
    state_code = batch_manager.retrieve_value_from_batch_row(
        "state_code", batch_header_map, one_batch_row)
    voter_id = batch_manager.retrieve_value_from_batch_row(
        "voter_id", batch_header_map, one_batch_row)
    voter_id = convert_to_int(voter_id)
    # These are not needed because they come from the measure table
    # contest_measure_text = batch_manager.retrieve_value_from_batch_row(
    #     "contest_measure_text", batch_header_map, one_batch_row)
    # contest_measure_url = batch_manager.retrieve_value_from_batch_row(
    #     "contest_measure_url", batch_header_map, one_batch_row)
    # yes_vote_description = batch_manager.retrieve_value_from_batch_row(
    #     "yes_vote_description", batch_header_map, one_batch_row)
    # no_vote_description = batch_manager.retrieve_value_from_batch_row(
    #     "no_vote_description", batch_header_map, one_batch_row)

    # Look up contest office or measure to see if an entry exists
    # These three parameters are needed to look up in OfficeHeld table for a match
    keep_looking_for_duplicates = True
    contest_measure_found = False
    contest_measure = None

    # state_code lookup from the election
    if positive_value_exists(google_civic_election_id) and not positive_value_exists(state_code):
        # Check to see if there is a state served for the election
        if google_civic_election_id in election_objects_dict:
            election = election_objects_dict[google_civic_election_id]
            if election:
                state_code = election.state_code
        else:
            election_manager = ElectionManager()
            results = election_manager.retrieve_election(google_civic_election_id)
            if results['election_found']:
                election = results['election']
                state_code = election.state_code
                election_objects_dict[google_civic_election_id] = election

    # See if we have a contest_office_we_vote_id
    contest_office_manager = ContestOfficeManager()
    if positive_value_exists(contest_office_we_vote_id):
        keep_looking_for_duplicates = False
        # If here, then we are updating an existing known record
        if contest_office_we_vote_id in office_objects_dict:
            contest_office = office_objects_dict[contest_office_we_vote_id]
            if contest_office:
                contest_office_name = contest_office.office_name
        else:
            status += "RETRIEVING_OFFICE_FROM_WE_VOTE_ID "
            # Needs to be read_only=False so we don't get "terminating connection due to conflict with recovery" error
            results = contest_office_manager.retrieve_contest_office_from_we_vote_id(contest_office_we_vote_id,
                                                                                     read_only=False)
            if results['contest_office_found']:
                contest_office = results['contest_office']
                contest_office_name = contest_office.office_name
                office_objects_dict[contest_office_we_vote_id] = contest_office
            else:
                status += "COULD_NOT_RETRIEVE_OFFICE_FROM_WE_VOTE_ID: "
                status += results['status']

    if keep_looking_for_duplicates and not positive_value_exists(contest_office_we_vote_id) and \
            positive_value_exists(contest_office_name):
        # See if we have an office name
        contest_office_list_manager = ContestOfficeListManager()
        # Needs to be read_only=False, so we don't get "terminating connection due to conflict with recovery" error
        matching_results = contest_office_list_manager.retrieve_contest_offices_from_non_unique_identifiers(
            contest_office_name=contest_office_name,
            google_civic_election_id=google_civic_election_id,
            incoming_state_code=state_code,
            read_only=False)
        if matching_results['contest_office_found']:
            keep_looking_for_duplicates = False
            contest_office = matching_results['contest_office']
            contest_office_name = contest_office.office_name
            contest_office_we_vote_id = contest_office.we_vote_id
            office_objects_dict[contest_office_we_vote_id] = contest_office
        elif matching_results['contest_office_list_found']:
            status += "RETRIEVE_OFFICE_FROM_NON_UNIQUE-MULTIPLE_POSSIBLE_OFFICES_FOUND "
            keep_looking_for_duplicates = False
        elif not matching_results['success']:
            status += "RETRIEVE_OFFICE_FROM_NON_UNIQUE-NO_SUCCESS "
            status += matching_results['status']
            keep_looking_for_duplicates = False

    if keep_looking_for_duplicates and \
            positive_value_exists(candidate_twitter_handle) or positive_value_exists(candidate_name):
        candidate_list_manager = CandidateListManager()
        google_civic_election_id_list = [google_civic_election_id]
        # Needs to be read_only=False, so we don't get "terminating connection due to conflict with recovery" error
        matching_results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
            google_civic_election_id_list=google_civic_election_id_list,
            state_code=state_code,
            candidate_twitter_handle=candidate_twitter_handle,
            candidate_name=candidate_name,
            read_only=True)
        if matching_results['candidate_found']:
            candidate = matching_results['candidate']
            keep_looking_for_duplicates = False
            contest_office_we_vote_id = candidate.contest_office_we_vote_id

    contest_measure_manager = ContestMeasureManager()
    if keep_looking_for_duplicates:
        # See if we have a contest_measure_we_vote_id
        if positive_value_exists(contest_measure_we_vote_id):
            # If here, then we are updating an existing known record
            if contest_measure_we_vote_id in measure_objects_dict:
                contest_measure = measure_objects_dict[contest_measure_we_vote_id]
                contest_measure_found = True
                if contest_measure:
                    contest_measure_name = contest_measure.measure_title
            else:
                # Needs to be read_only=False so we don't get "terminating connection due to conflict with recovery"
                results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
                    contest_measure_we_vote_id, read_only=False)
                if results['contest_measure_found']:
                    keep_looking_for_duplicates = False
                    contest_measure = results['contest_measure']
                    contest_measure_found = True
                    contest_measure_name = contest_measure.measure_title
                    measure_objects_dict[contest_measure_we_vote_id] = contest_measure
                else:
                    keep_looking_for_duplicates = True

    if keep_looking_for_duplicates and not \
            positive_value_exists(contest_measure_we_vote_id) and positive_value_exists(contest_measure_name):
        # See if we have an measure name
        contest_measure_list = ContestMeasureListManager()
        keep_looking_for_duplicates = True
        google_civic_election_id_list = [google_civic_election_id]
        # Needs to be read_only=False so we don't get "terminating connection due to conflict with recovery" error
        matching_results = contest_measure_list.retrieve_contest_measures_from_non_unique_identifiers(
            google_civic_election_id_list, state_code, contest_measure_name, read_only=False)
        if matching_results['contest_measure_found']:
            contest_measure = matching_results['contest_measure']
            contest_measure_found = True
            contest_measure_name = contest_measure.measure_title
            contest_measure_we_vote_id = contest_measure.we_vote_id
            measure_objects_dict[contest_measure_we_vote_id] = contest_measure
            keep_looking_for_duplicates = False
        elif matching_results['contest_measure_list_found']:
            status += "RETRIEVE_MEASURE_FROM_NON_UNIQUE-MULTIPLE_POSSIBLE_MEASURES_FOUND "
            keep_looking_for_duplicates = False
        elif not matching_results['success']:
            status += "RETRIEVE_MEASURE_FROM_NON_UNIQUE-NO_SUCCESS "
            status += matching_results['status']
            keep_looking_for_duplicates = False

    # Now retrieve full measure data (if needed)
    if positive_value_exists(contest_measure_we_vote_id):
        # If here, then we are updating an existing known record
        if contest_measure_we_vote_id in measure_objects_dict:
            contest_measure = measure_objects_dict[contest_measure_we_vote_id]
            contest_measure_found = True
        else:
            # Needs to be read_only=False so we don't get "terminating connection due to conflict with recovery" error
            results = contest_measure_manager.retrieve_contest_measure_from_we_vote_id(
                contest_measure_we_vote_id, read_only=False)
            if results['contest_measure_found']:
                contest_measure = results['contest_measure']
                measure_objects_dict[contest_measure_we_vote_id] = contest_measure
                contest_measure_found = True
        if contest_measure_found:
            contest_measure_name = contest_measure.measure_title
            contest_measure_text = contest_measure.get_measure_text()
            contest_measure_url = contest_measure.get_measure_url()
            yes_vote_description = contest_measure.ballotpedia_yes_vote_description
            no_vote_description = contest_measure.ballotpedia_no_vote_description

    # check for duplicate entries in the live ballot_item data
    existing_ballot_item_query_completed = False
    if positive_value_exists(contest_office_we_vote_id) or positive_value_exists(contest_measure_we_vote_id):
        try:
            # This used to retrieve from using('readonly') but the query gets interrupted from updates from master
            existing_ballot_item_query = BallotItem.objects.all()
            existing_ballot_item_query = existing_ballot_item_query.filter(
                google_civic_election_id=google_civic_election_id,
                polling_location_we_vote_id__iexact=polling_location_we_vote_id
            )
            if positive_value_exists(contest_office_we_vote_id):
                existing_ballot_item_query = existing_ballot_item_query.filter(
                    contest_office_we_vote_id__iexact=contest_office_we_vote_id)
            elif positive_value_exists(contest_measure_we_vote_id):
                existing_ballot_item_query = existing_ballot_item_query.filter(
                    contest_measure_we_vote_id__iexact=contest_measure_we_vote_id)

            existing_entry_list = existing_ballot_item_query[:1]
            existing_ballot_item_query_completed = True
            if len(existing_entry_list):
                existing_ballot_item = existing_entry_list[0]
                existing_ballot_item_id = existing_ballot_item.id
                existing_ballot_item_found = True
            else:
                existing_ballot_item_found = False
        except Exception as e:
            status += "CREATE_BATCH_ROW_ACTION_BALLOT_ITEM-BATCH_ROW_ACTION_BALLOT_ITEM_RETRIEVE_ERROR: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

    # Do we have the minimum required variables?
    polling_location_or_voter = positive_value_exists(polling_location_we_vote_id) or positive_value_exists(voter_id)
    office_or_measure = \
        (positive_value_exists(contest_office_we_vote_id) or positive_value_exists(contest_measure_we_vote_id)) \
        and existing_ballot_item_query_completed
    if polling_location_or_voter and office_or_measure and google_civic_election_id:
        if positive_value_exists(existing_ballot_item_found):
            # Update existing ballot item
            # batch_row_action_ballot_item.ballot_item_id = existing_ballot_item_id
            kind_of_action = IMPORT_ADD_TO_EXISTING
        else:
            kind_of_action = IMPORT_CREATE
    else:
        if not polling_location_or_voter:
            status += "MISSING_POLLING_LOCATION_OR_VOTER_ID "
        if not office_or_measure:
            status += "MISSING_OFFICE_OR_MEASURE "
        if not google_civic_election_id:
            status += "MISSING_GOOGLE_CIVIC_ELECTION_ID "
        kind_of_action = IMPORT_TO_BE_DETERMINED
        print_to_log(logger=logger, exception_message_optional=status)

    ballot_item_display_name = ''
    if positive_value_exists(contest_office_name):
        ballot_item_display_name = contest_office_name
    elif positive_value_exists(contest_measure_name):
        ballot_item_display_name = contest_measure_name

    # Does a BatchRowActionBallotItem entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    batch_row_action_ballot_item_change_found = False
    existing_results = batch_manager.retrieve_batch_row_action_ballot_item(
        batch_description.batch_header_id, one_batch_row.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_ballot_item = existing_results['batch_row_action_ballot_item']
        batch_row_action_updated = True
        status += "EXISTING_BATCH_ROW_ACTION_BALLOT_ITEM_FOUND "
    else:
        # If a BatchRowActionBallotItem entry does not exist, create one
        status += "[BatchRowActionBallotItem.objects.create]"
        try:
            batch_row_action_ballot_item = BatchRowActionBallotItem.objects.create(
                ballot_item_display_name=ballot_item_display_name,
                ballot_item_id=existing_ballot_item_id,
                batch_header_id=batch_description.batch_header_id,
                batch_row_id=one_batch_row.id,
                batch_set_id=batch_description.batch_set_id,
                contest_measure_we_vote_id=contest_measure_we_vote_id,
                contest_office_we_vote_id=contest_office_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_action=kind_of_action,
                local_ballot_order=local_ballot_order,
                measure_text=contest_measure_text,
                measure_url=contest_measure_url,
                no_vote_description=no_vote_description,
                polling_location_we_vote_id=polling_location_we_vote_id,
                state_code=state_code,
                status=status,
                voter_id=voter_id,
                yes_vote_description=yes_vote_description,
            )
            batch_row_action_created = True
            status += "BATCH_ROW_ACTION_BALLOT_ITEM_CREATED "
        except Exception as e:
            batch_row_action_created = False
            batch_row_action_ballot_item = None
            success = False
            status += "BATCH_ROW_ACTION_BALLOT_ITEM_NOT_CREATED: " + str(e) + " "
            handle_exception(e, logger=logger, exception_message=status)

            results = {
                'success':                      success,
                'status':                       status,
                'batch_row_action_updated':     batch_row_action_updated,
                'batch_row_action_created':     batch_row_action_created,
                'batch_row_action_ballot_item': batch_row_action_ballot_item,
                'batch_row':                    one_batch_row,
                'election_objects_dict':        election_objects_dict,
                'measure_objects_dict':         measure_objects_dict,
                'office_objects_dict':          office_objects_dict,
            }
            return results

    # Update the BatchRowActionBallotItem if needed
    try:
        if batch_row_action_ballot_item.batch_set_id != batch_description.batch_set_id:
            batch_row_action_ballot_item.batch_set_id = batch_description.batch_set_id
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.polling_location_we_vote_id != polling_location_we_vote_id:
            batch_row_action_ballot_item.polling_location_we_vote_id = polling_location_we_vote_id
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.kind_of_action != kind_of_action:
            batch_row_action_ballot_item.kind_of_action = kind_of_action
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.contest_office_we_vote_id != contest_office_we_vote_id:
            batch_row_action_ballot_item.contest_office_we_vote_id = contest_office_we_vote_id
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.contest_measure_we_vote_id != contest_measure_we_vote_id:
            batch_row_action_ballot_item.contest_measure_we_vote_id = contest_measure_we_vote_id
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.state_code != state_code:
            batch_row_action_ballot_item.state_code = state_code
            batch_row_action_ballot_item_change_found = True
        # batch_row_action_ballot_item.contest_measure_name = contest_measure_name
        if batch_row_action_ballot_item.local_ballot_order != local_ballot_order:
            batch_row_action_ballot_item.local_ballot_order = local_ballot_order
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.google_civic_election_id != google_civic_election_id:
            batch_row_action_ballot_item.google_civic_election_id = google_civic_election_id
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.measure_text != contest_measure_text:
            batch_row_action_ballot_item.measure_text = contest_measure_text
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.measure_url != contest_measure_url:
            batch_row_action_ballot_item.measure_url = contest_measure_url
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.no_vote_description != no_vote_description:
            batch_row_action_ballot_item.no_vote_description = no_vote_description
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.yes_vote_description != yes_vote_description:
            batch_row_action_ballot_item.yes_vote_description = yes_vote_description
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.voter_id != voter_id:
            batch_row_action_ballot_item.voter_id = voter_id
            batch_row_action_ballot_item_change_found = True
        if batch_row_action_ballot_item.ballot_item_display_name != ballot_item_display_name:
            batch_row_action_ballot_item.ballot_item_display_name = ballot_item_display_name
            batch_row_action_ballot_item_change_found = True
        if positive_value_exists(batch_row_action_ballot_item_change_found):
            batch_row_action_ballot_item.status = status
            batch_row_action_ballot_item.save()
            status += "BATCH_ROW_ACTION_BALLOT_ITEM_SAVED "
        else:
            status += "BATCH_ROW_ACTION_BALLOT_ITEM_NO_SAVE_NEEDED "
    except Exception as e:
        success = False
        status += "BATCH_ROW_ACTION_BALLOT_ITEM_UNABLE_TO_SAVE: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)

    try:
        if batch_row_action_created or batch_row_action_updated:
            # If BatchRowAction was created, this batch_row was analyzed
            batch_row_changed = False
            if positive_value_exists(polling_location_we_vote_id):
                if one_batch_row.polling_location_we_vote_id != polling_location_we_vote_id:
                    one_batch_row.polling_location_we_vote_id = polling_location_we_vote_id
                    batch_row_changed = True
            if positive_value_exists(voter_id):
                if one_batch_row.voter_id != voter_id:
                    one_batch_row.voter_id = voter_id
                    batch_row_changed = True
            if not positive_value_exists(one_batch_row.batch_row_analyzed):
                one_batch_row.batch_row_analyzed = True
                batch_row_changed = True
            if batch_row_changed:
                one_batch_row.save()
    except Exception as e:
        status += "COULD_NOT_SAVE_BATCH_ROW: " + str(e) + " "
        handle_exception(e, logger=logger, exception_message=status)

    results = {
        'success':                      success,
        'status':                       status,
        'batch_row_action_created':     batch_row_action_created,
        'batch_row_action_updated':     batch_row_action_updated,
        'batch_row_action_ballot_item': batch_row_action_ballot_item,
        'batch_row':                    one_batch_row,
        'election_objects_dict':        election_objects_dict,
        'measure_objects_dict':         measure_objects_dict,
        'office_objects_dict':          office_objects_dict,
    }
    return results


def create_batch_row_action_ballot_item_delete(batch_description, existing_ballot_item):
    """
    Schedule the delete of existing ballot_item
    :param batch_description:
    :param existing_ballot_item:
    :return:
    """
    batch_manager = BatchManager()

    status = ''
    success = True

    if positive_value_exists(existing_ballot_item.google_civic_election_id):
        google_civic_election_id = str(existing_ballot_item.google_civic_election_id)
    else:
        google_civic_election_id = str(batch_description.google_civic_election_id)

    # Does a BatchRowActionBallotItem entry already exist?
    # We want to start with the BatchRowAction... entry first so we can record our findings line by line while
    #  we are checking for existing duplicate data
    existing_results = batch_manager.retrieve_batch_row_action_ballot_item(
        batch_description.batch_header_id, ballot_item_id=existing_ballot_item.id)
    if existing_results['batch_row_action_found']:
        batch_row_action_ballot_item = existing_results['batch_row_action_ballot_item']
        batch_row_action_delete_exists = True
    else:
        # If a BatchRowActionBallotItem entry does not exist, create one
        try:
            batch_row_action_ballot_item = BatchRowActionBallotItem.objects.create(
                ballot_item_id=existing_ballot_item.id,
                ballot_item_display_name=existing_ballot_item.ballot_item_display_name,
                batch_header_id=batch_description.batch_header_id,
                batch_set_id=batch_description.batch_set_id,
                google_civic_election_id=google_civic_election_id,
                kind_of_action=IMPORT_DELETE,
            )
            batch_row_action_delete_exists = True
            status += "BATCH_ROW_ACTION_BALLOT_ITEM_DELETE_CREATED "
        except Exception as e:
            batch_row_action_delete_exists = False
            batch_row_action_ballot_item = None
            success = False
            status += "BATCH_ROW_ACTION_BALLOT_ITEM_DELETE_NOT_CREATED: " + str(e) + " "

            results = {
                'success':                          success,
                'status':                           status,
                'batch_row_action_delete_exists':   batch_row_action_delete_exists,
                'batch_row_action_ballot_item':     batch_row_action_ballot_item,
            }
            return results

    results = {
        'success':                          success,
        'status':                           status,
        'batch_row_action_delete_exists':   batch_row_action_delete_exists,
        'batch_row_action_ballot_item':     batch_row_action_ballot_item,
    }
    return results


def import_office_held_data_from_batch_row_actions(batch_header_id, batch_row_id,
                                                      create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for office held, IMPORT_CREATE or IMPORT_ADD_TO_EXISTING
    Process batch row entries in order to create or update OfficeHeld entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for IMPORT_CREATE
    :param update_entry_flag: set to True for IMPORT_ADD_TO_EXISTING
    :return: 
    """
    success = False
    status = ""
    number_of_offices_held_created = 0
    number_of_offices_held_updated = 0
    kind_of_batch = ""
    new_office_held = ''
    new_office_held_created = False
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_OFFICE_HELD_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_offices_held_created':    number_of_offices_held_created,
            'number_of_offices_held_updated':    number_of_offices_held_updated
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
        status += "IMPORT_OFFICE_HELD_ENTRY-BATCH_DESCRIPTION_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_offices_held_created':    number_of_offices_held_created,
            'number_of_offices_held_updated':    number_of_offices_held_updated
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
        status += "IMPORT_OFFICE_HELD_ENTRY-BATCH_HEADER_MAP_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_offices_held_created':    number_of_offices_held_created,
            'number_of_offices_held_updated':    number_of_offices_held_updated
        }
        return results

    batch_row_action_list_found = False
    try:
        batch_row_action_list = BatchRowActionOfficeHeld.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
            kind_of_action = IMPORT_CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
            kind_of_action = IMPORT_ADD_TO_EXISTING
        else:
            # error handling
            status += "IMPORT_OFFICE_HELD_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                              success,
                'status':                               status,
                'number_of_offices_held_created':    number_of_offices_held_created,
                'number_of_offices_held_updated':    number_of_offices_held_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionOfficeHeld.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    # batch_manager = BatchManager()

    if not batch_row_action_list_found:
        status += "IMPORT_OFFICE_HELD_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_offices_held_created':    number_of_offices_held_created,
            'number_of_offices_held_updated':    number_of_offices_held_updated
        }
        return results

    for one_batch_row_action in batch_row_action_list:

        # Find the column in the incoming batch_row with the header == office_held_name
        office_held_name = one_batch_row_action.office_held_name
        office_held_name_es = one_batch_row_action.office_held_name_es
        if positive_value_exists(one_batch_row_action.google_civic_election_id):
            google_civic_election_id = str(one_batch_row_action.google_civic_election_id)
        else:
            google_civic_election_id = str(batch_description.google_civic_election_id)
        ctcl_uuid = one_batch_row_action.ctcl_uuid
        office_held_description = one_batch_row_action.office_held_description
        office_held_description_es = one_batch_row_action.office_held_description_es
        office_held_is_partisan = one_batch_row_action.office_held_is_partisan
        state_code = one_batch_row_action.state_code

        # Look up OfficeHeld to see if an entry exists
        # These five parameters are needed to look up in OfficeHeld table for a match
        if (positive_value_exists(office_held_name) or positive_value_exists(office_held_name_es)) and \
                positive_value_exists(state_code) and positive_value_exists(google_civic_election_id):
            office_held_manager = OfficeHeldManager()
            if create_entry_flag:
                results = office_held_manager.create_office_held_row_entry(office_held_name, state_code,
                                                                                 office_held_description, ctcl_uuid,
                                                                                 office_held_is_partisan,
                                                                                 google_civic_election_id,
                                                                                 office_held_name_es,
                                                                                 office_held_description_es)
                if results['new_office_held_created']:
                    number_of_offices_held_created += 1
                    success = True
                    # now update BatchRowActionOfficeHeld table entry
                    try:
                        one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                        new_office_held = results['new_office_held']
                        one_batch_row_action.office_held_we_vote_id = new_office_held.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "OFFICE_HELD_RETRIEVE_ERROR"
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                office_held_we_vote_id = one_batch_row_action.office_held_we_vote_id
                results = office_held_manager.update_office_held_row_entry(office_held_name,
                                                                                 state_code, office_held_description,
                                                                                 ctcl_uuid, office_held_is_partisan,
                                                                                 google_civic_election_id,
                                                                                 office_held_we_vote_id,
                                                                                 office_held_name_es,
                                                                                 office_held_description_es)
                if results['office_held_updated']:
                    number_of_offices_held_updated += 1
                    success = True
            else:
                # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
                status += "IMPORT_OFFICE_HELD_ENTRY:NO_CREATE_OR_UPDATE_ERROR"
                results = {
                    'success':                              success,
                    'status':                               status,
                    'number_of_offices_held_created':    number_of_offices_held_created,
                    'number_of_offices_held_updated':    number_of_offices_held_updated,
                    'new_office_held':                   new_office_held,
                }
                return results

    if number_of_offices_held_created:
        status += "IMPORT_OFFICE_HELD_ENTRY:OFFICE_HELD_CREATED"
    elif number_of_offices_held_updated:
        status += "IMPORT_OFFICE_HELD_ENTRY:OFFICE_HELD_UPDATED"

    results = {
        'success':                              success,
        'status':                               status,
        'number_of_offices_held_created':    number_of_offices_held_created,
        'number_of_offices_held_updated':    number_of_offices_held_updated,
        'new_office_held':                   new_office_held,
    }
    return results


def update_or_create_batch_header_mapping(batch_header_id, kind_of_batch, incoming_header_map_values):
    success = False
    status = ""

    # Filter out header values that aren't We Vote approved
    if kind_of_batch == CANDIDATE:
        modified_header_map_values = incoming_header_map_values
    elif kind_of_batch == CONTEST_OFFICE:
        modified_header_map_values = incoming_header_map_values
    elif kind_of_batch == OFFICE_HELD:
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


# There is also a function of this same name in models.py
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
    elif kind_of_batch == OFFICE_HELD:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_OFFICES_HELD
    elif kind_of_batch == IMPORT_BALLOT_ITEM:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_BALLOT_ITEMS
    elif kind_of_batch == IMPORT_POLLING_LOCATION:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_POLLING_LOCATIONS
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
    elif kind_of_batch == REPRESENTATIVES:
        kind_of_batch_recognized = True
        batch_import_keys_accepted_dict = BATCH_IMPORT_KEYS_ACCEPTED_FOR_REPRESENTATIVES
    else:
        kind_of_batch_recognized = False
        batch_import_keys_accepted_dict = {}

    if kind_of_batch_recognized:
        if incoming_header_map_values['batch_header_map_000'] in batch_import_keys_accepted_dict:
            # We deal with empty values and make values lowercase within this function
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_000'], batch_header.batch_header_column_000)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_001'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_001'], batch_header.batch_header_column_001)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_002'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_002'], batch_header.batch_header_column_002)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_003'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_003'], batch_header.batch_header_column_003)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_004'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_004'], batch_header.batch_header_column_004)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_005'] in batch_import_keys_accepted_dict:
            batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_005'], batch_header.batch_header_column_005)
        suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_006'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_006'], batch_header.batch_header_column_006)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_007'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_007'], batch_header.batch_header_column_007)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_008'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_008'], batch_header.batch_header_column_008)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_009'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_009'], batch_header.batch_header_column_009)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_010'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_010'], batch_header.batch_header_column_010)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_011'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_011'], batch_header.batch_header_column_011)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_012'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_012'], batch_header.batch_header_column_012)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_013'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_013'], batch_header.batch_header_column_013)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_014'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_014'], batch_header.batch_header_column_014)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_015'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_015'], batch_header.batch_header_column_015)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_016'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_016'], batch_header.batch_header_column_016)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_017'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_017'], batch_header.batch_header_column_017)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_018'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_018'], batch_header.batch_header_column_018)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_019'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_019'], batch_header.batch_header_column_019)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created
        if incoming_header_map_values['batch_header_map_020'] in batch_import_keys_accepted_dict:
            results = batch_manager.create_batch_header_translation_suggestion(
                kind_of_batch, incoming_header_map_values['batch_header_map_020'], batch_header.batch_header_column_020)
            suggestions_created = suggestions_created + 1 if results['suggestion_created'] else suggestions_created

    results = {
        'success':              success,
        'status':               status,
        'suggestions_created':  suggestions_created,
    }
    return results


def import_contest_office_data_from_batch_row_actions(
        batch_header_id, batch_row_id, state_code="", create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for contest office, IMPORT_CREATE or IMPORT_ADD_TO_EXISTING
    Process batch row entries in order to create or update ContestOffice entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param state_code:
    :param create_entry_flag: set to True for IMPORT_CREATE
    :param update_entry_flag: set to True for IMPORT_ADD_TO_EXISTING
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

    batch_row_action_list_found = False
    try:
        batch_row_action_list = BatchRowActionContestOffice.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)
        if positive_value_exists(state_code):
            batch_row_action_list = batch_row_action_list.filter(state_code__iexact=state_code)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
            kind_of_action = IMPORT_CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
            kind_of_action = IMPORT_ADD_TO_EXISTING
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

    # if not batch_row_action_list_found:
    #     status += "IMPORT_CONTEST_OFFICE_ENTRY-BATCH_ROW_ACTION_LIST_MISSING "
    #     results = {
    #         'success':                              success,
    #         'status':                               status,
    #         'number_of_contest_offices_created':    number_of_contest_offices_created,
    #         'number_of_contest_offices_updated':    number_of_contest_offices_updated
    #     }
    #     return results

    for one_batch_row_action in batch_row_action_list:
        # Find the column in the incoming batch_row with the header == contest_office_name
        contest_office_name = one_batch_row_action.contest_office_name
        google_civic_election_id = str(one_batch_row_action.google_civic_election_id)
        contest_office_votes_allowed = one_batch_row_action.number_voting_for
        contest_office_number_elected = one_batch_row_action.number_elected
        state_code = one_batch_row_action.state_code
        defaults = {
            'district_id':                      one_batch_row_action.district_id,
            'district_name':                    one_batch_row_action.district_name,
            'district_scope':                   one_batch_row_action.district_scope,
            'ballotpedia_district_id':          one_batch_row_action.ballotpedia_district_id,
            'ballotpedia_election_id':          one_batch_row_action.ballotpedia_election_id,
            'ballotpedia_is_marquee':           one_batch_row_action.ballotpedia_is_marquee,
            'ballotpedia_office_id':            one_batch_row_action.ballotpedia_office_id,
            'ballotpedia_office_name':          one_batch_row_action.ballotpedia_office_name,
            'ballotpedia_office_url':           one_batch_row_action.ballotpedia_office_url,
            'ballotpedia_race_id':              one_batch_row_action.ballotpedia_race_id,
            'ballotpedia_race_office_level':    one_batch_row_action.ballotpedia_race_office_level,
            'is_ballotpedia_general_election':          one_batch_row_action.is_ballotpedia_general_election,
            'is_ballotpedia_general_runoff_election':   one_batch_row_action.is_ballotpedia_general_runoff_election,
            'is_ballotpedia_primary_election':          one_batch_row_action.is_ballotpedia_primary_election,
            'is_ballotpedia_primary_runoff_election':   one_batch_row_action.is_ballotpedia_primary_runoff_election,
        }
        if positive_value_exists(one_batch_row_action.ctcl_uuid):
            defaults['ctcl_uuid'] = one_batch_row_action.ctcl_uuid
        if positive_value_exists(one_batch_row_action.vote_usa_office_id):
            defaults['vote_usa_office_id'] = one_batch_row_action.vote_usa_office_id

        # These three parameters are minimum variables required for the ContestOffice table
        if positive_value_exists(contest_office_name) and positive_value_exists(state_code) and \
                positive_value_exists(google_civic_election_id):
            contest_office_manager = ContestOfficeManager()
            if create_entry_flag:
                defaults['google_civic_office_name'] = one_batch_row_action.contest_office_name
                results = contest_office_manager.create_contest_office_row_entry(
                    contest_office_name=contest_office_name,
                    contest_office_votes_allowed=contest_office_votes_allowed,
                    contest_office_number_elected=contest_office_number_elected,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    defaults=defaults)
                if results['contest_office_updated']:
                    number_of_contest_offices_created += 1
                    success = True
                    # now update BatchRowActionContestOffice table entry with the results of this action
                    try:
                        one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                        contest_office = results['contest_office']
                        one_batch_row_action.contest_office_we_vote_id = contest_office.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "CONTEST_OFFICE_RETRIEVE_ERROR"
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                contest_office_we_vote_id = one_batch_row_action.contest_office_we_vote_id
                results = contest_office_manager.update_contest_office_row_entry(
                    contest_office_name=contest_office_name,
                    contest_office_votes_allowed=contest_office_votes_allowed,
                    contest_office_number_elected=contest_office_number_elected,
                    contest_office_we_vote_id=contest_office_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    state_code=state_code,
                    defaults=defaults)
                if results['contest_office_updated']:
                    number_of_contest_offices_updated += 1
                    success = True
                    # now update BatchRowActionContestOffice table entry with the results of this action
                    try:
                        one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                        contest_office = results['contest_office']
                        one_batch_row_action.contest_office_we_vote_id = contest_office.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "CONTEST_OFFICE_RETRIEVE_ERROR"
                        handle_exception(e, logger=logger, exception_message=status)
            else:
                # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
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
        status += "IMPORT_CONTEST_OFFICE_ENTRY:CONTEST_OFFICE_CREATED "
    elif number_of_contest_offices_updated:
        status += "IMPORT_CONTEST_OFFICE_ENTRY:CONTEST_OFFICE_UPDATED "

    results = {
        'success':                              success,
        'status':                               status,
        'number_of_contest_offices_created':    number_of_contest_offices_created,
        'number_of_contest_offices_updated':    number_of_contest_offices_updated,
        'new_contest_office':                   new_contest_office,
    }
    return results


def import_measure_data_from_batch_row_actions(batch_header_id, batch_row_id,
                                               create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for measure, IMPORT_CREATE or IMPORT_ADD_TO_EXISTING
    Process batch row entries in order to create or update contestmeasure entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for IMPORT_CREATE
    :param update_entry_flag: set to True for IMPORT_ADD_TO_EXISTING
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

    batch_row_action_list_found = False
    try:
        batch_row_action_list = BatchRowActionMeasure.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
            kind_of_action = IMPORT_CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
            kind_of_action = IMPORT_ADD_TO_EXISTING
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

        # Find the column in the incoming batch_row with the header == office_held_name
        measure_title = one_batch_row_action.measure_title
        measure_subtitle = one_batch_row_action.measure_subtitle
        if positive_value_exists(one_batch_row_action.google_civic_election_id):
            google_civic_election_id = str(one_batch_row_action.google_civic_election_id)
        else:
            google_civic_election_id = str(batch_description.google_civic_election_id)
        ctcl_uuid = one_batch_row_action.ctcl_uuid
        measure_text = one_batch_row_action.measure_text
        state_code = one_batch_row_action.state_code
        defaults = {
            'election_day_text':            one_batch_row_action.election_day_text,
            'ballotpedia_district_id':      one_batch_row_action.ballotpedia_district_id,
            'ballotpedia_election_id':      one_batch_row_action.ballotpedia_election_id,
            'ballotpedia_measure_id':       one_batch_row_action.ballotpedia_measure_id,
            'ballotpedia_measure_name':     one_batch_row_action.ballotpedia_measure_name,
            'ballotpedia_measure_status':   one_batch_row_action.ballotpedia_measure_status,
            'ballotpedia_measure_summary':  one_batch_row_action.ballotpedia_measure_summary,
            'ballotpedia_measure_text':     one_batch_row_action.ballotpedia_measure_text,
            'ballotpedia_measure_url':      one_batch_row_action.ballotpedia_measure_url,
            'ballotpedia_yes_vote_description': one_batch_row_action.ballotpedia_yes_vote_description,
            'ballotpedia_no_vote_description':  one_batch_row_action.ballotpedia_no_vote_description,
            'state_code':                   one_batch_row_action.state_code,
        }

        # Look up ContestMeasure to see if an entry exists
        # These five parameters are needed to look up in Measure table for a match
        if positive_value_exists(measure_title) and positive_value_exists(state_code) and \
                positive_value_exists(google_civic_election_id):
            contest_measure_manager = ContestMeasureManager()
            if create_entry_flag:
                results = contest_measure_manager.create_measure_row_entry(
                    ctcl_uuid=ctcl_uuid,
                    google_civic_election_id=google_civic_election_id,
                    measure_subtitle=measure_subtitle,
                    measure_text=measure_text,
                    measure_title=measure_title,
                    state_code=state_code,
                    defaults=defaults)
                if results['contest_measure_created']:
                    number_of_measures_created += 1
                    success = True
                    # now update BatchRowActionMeasure table entry
                    try:
                        one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                        new_measure = results['contest_measure']
                        one_batch_row_action.measure_we_vote_id = new_measure.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "MEASURE_RETRIEVE_ERROR:" + str(e) + " "
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                measure_we_vote_id = one_batch_row_action.measure_we_vote_id
                results = contest_measure_manager.update_measure_row_entry(measure_title, measure_subtitle,
                                                                           measure_text, state_code, ctcl_uuid,
                                                                           google_civic_election_id, measure_we_vote_id,
                                                                           defaults)
                if results['contest_measure_updated']:
                    number_of_measures_updated += 1
                    success = True
            else:
                # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
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


def import_candidate_data_from_batch_row_actions(batch_header_id, batch_row_id, create_entry_flag=False,
                                                 update_entry_flag=False):
    """
    Import batch_rows for candidate, IMPORT_CREATE or IMPORT_ADD_TO_EXISTING
    Process batch row entries in order to create or update CandidateCampaign entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for IMPORT_CREATE
    :param update_entry_flag: set to True for IMPORT_ADD_TO_EXISTING
    :return: 
    """
    success = False
    status = ""
    number_of_candidates_created = 0
    number_of_candidates_updated = 0
    new_candidate = ''

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

    batch_row_action_list_found = False
    try:
        batch_row_action_list = BatchRowActionCandidate.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
            kind_of_action = IMPORT_CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
            kind_of_action = IMPORT_ADD_TO_EXISTING
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
        candidate_ctcl_person_id = one_batch_row_action.candidate_ctcl_person_id
        if positive_value_exists(one_batch_row_action.google_civic_election_id):
            google_civic_election_id = str(one_batch_row_action.google_civic_election_id)
        else:
            google_civic_election_id = str(batch_description.google_civic_election_id)

        # These update values are using the field names in the CandidateCampaign class
        update_values = {}
        retrieve_ballotpedia_image = False
        # We only want to add data, not remove any
        if positive_value_exists(one_batch_row_action.ballotpedia_candidate_id):
            update_values['ballotpedia_candidate_id'] = one_batch_row_action.ballotpedia_candidate_id
        if positive_value_exists(one_batch_row_action.ballotpedia_candidate_name):
            update_values['ballotpedia_candidate_name'] = one_batch_row_action.ballotpedia_candidate_name
        if positive_value_exists(one_batch_row_action.ballotpedia_candidate_summary):
            update_values['ballotpedia_candidate_summary'] = one_batch_row_action.ballotpedia_candidate_summary
        if positive_value_exists(one_batch_row_action.ballotpedia_candidate_url):
            update_values['ballotpedia_candidate_url'] = one_batch_row_action.ballotpedia_candidate_url
        if positive_value_exists(one_batch_row_action.ballotpedia_election_id):
            update_values['ballotpedia_election_id'] = one_batch_row_action.ballotpedia_election_id
        if positive_value_exists(one_batch_row_action.ballotpedia_image_id):
            update_values['ballotpedia_image_id'] = one_batch_row_action.ballotpedia_image_id
            retrieve_ballotpedia_image = True
        if positive_value_exists(one_batch_row_action.ballotpedia_office_id):
            update_values['ballotpedia_office_id'] = one_batch_row_action.ballotpedia_office_id
        if positive_value_exists(one_batch_row_action.ballotpedia_person_id):
            update_values['ballotpedia_person_id'] = one_batch_row_action.ballotpedia_person_id
        if positive_value_exists(one_batch_row_action.ballotpedia_race_id):
            update_values['ballotpedia_race_id'] = one_batch_row_action.ballotpedia_race_id
        if positive_value_exists(one_batch_row_action.birth_day_text):
            update_values['birth_day_text'] = one_batch_row_action.birth_day_text
        if positive_value_exists(one_batch_row_action.candidate_gender):
            update_values['candidate_gender'] = one_batch_row_action.candidate_gender
        if positive_value_exists(one_batch_row_action.candidate_is_incumbent):
            update_values['candidate_is_incumbent'] = one_batch_row_action.candidate_is_incumbent
        else:
            update_values['candidate_is_incumbent'] = False
        if positive_value_exists(one_batch_row_action.candidate_is_top_ticket):
            update_values['candidate_is_top_ticket'] = one_batch_row_action.candidate_is_top_ticket
        if positive_value_exists(one_batch_row_action.candidate_name):
            update_values['candidate_name'] = one_batch_row_action.candidate_name
        if positive_value_exists(one_batch_row_action.candidate_participation_status):
            update_values['candidate_participation_status'] = one_batch_row_action.candidate_participation_status
        if positive_value_exists(one_batch_row_action.candidate_twitter_handle):
            update_values['candidate_twitter_handle'] = one_batch_row_action.candidate_twitter_handle
        if positive_value_exists(one_batch_row_action.candidate_url):
            update_values['candidate_url'] = one_batch_row_action.candidate_url
        if positive_value_exists(one_batch_row_action.candidate_contact_form_url):
            update_values['candidate_contact_form_url'] = one_batch_row_action.candidate_contact_form_url
        if positive_value_exists(one_batch_row_action.candidate_email):
            update_values['candidate_email'] = one_batch_row_action.candidate_email
        if positive_value_exists(one_batch_row_action.contest_office_we_vote_id):
            update_values['contest_office_we_vote_id'] = one_batch_row_action.contest_office_we_vote_id
        if positive_value_exists(one_batch_row_action.contest_office_id):
            update_values['contest_office_id'] = one_batch_row_action.contest_office_id
        if positive_value_exists(one_batch_row_action.contest_office_name):
            update_values['contest_office_name'] = one_batch_row_action.contest_office_name
        if positive_value_exists(one_batch_row_action.crowdpac_candidate_id):
            update_values['crowdpac_candidate_id'] = one_batch_row_action.crowdpac_candidate_id
        if positive_value_exists(one_batch_row_action.ctcl_uuid):
            update_values['ctcl_uuid'] = one_batch_row_action.ctcl_uuid
        if positive_value_exists(one_batch_row_action.facebook_url):
            update_values['facebook_url'] = one_batch_row_action.facebook_url
        if positive_value_exists(google_civic_election_id):
            update_values['google_civic_election_id'] = google_civic_election_id
        if positive_value_exists(one_batch_row_action.party):
            update_values['party'] = one_batch_row_action.party
        if positive_value_exists(one_batch_row_action.photo_url):
            update_values['photo_url'] = one_batch_row_action.photo_url
        if positive_value_exists(one_batch_row_action.photo_url_from_ctcl):
            update_values['photo_url_from_ctcl'] = one_batch_row_action.photo_url_from_ctcl
        if positive_value_exists(one_batch_row_action.photo_url_from_vote_usa):
            update_values['photo_url_from_vote_usa'] = one_batch_row_action.photo_url_from_vote_usa
        if positive_value_exists(one_batch_row_action.vote_usa_office_id):
            update_values['vote_usa_office_id'] = one_batch_row_action.vote_usa_office_id
        if positive_value_exists(one_batch_row_action.vote_usa_politician_id):
            update_values['vote_usa_politician_id'] = one_batch_row_action.vote_usa_politician_id
        if positive_value_exists(one_batch_row_action.vote_usa_profile_image_url_https):
            update_values['vote_usa_profile_image_url_https'] = one_batch_row_action.vote_usa_profile_image_url_https
        if positive_value_exists(one_batch_row_action.state_code):
            update_values['state_code'] = one_batch_row_action.state_code

        candidate_manager = CandidateManager()
        if create_entry_flag:
            # These parameters are required to create a CandidateCampaign entry
            if positive_value_exists(one_batch_row_action.candidate_name) \
                    and positive_value_exists(google_civic_election_id) and \
                    positive_value_exists(one_batch_row_action.state_code):
                # Check to see if anyone else is using the Twitter handle

                results = candidate_manager.create_candidate_row_entry(update_values)
                if results['new_candidate_created']:
                    number_of_candidates_created += 1
                    success = True
                    # now update BatchRowActionCandidate table entry
                    try:
                        one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                        new_candidate = results['new_candidate']
                        one_batch_row_action.candidate_we_vote_id = new_candidate.we_vote_id
                        one_batch_row_action.save()
                        if positive_value_exists(retrieve_ballotpedia_image) \
                                and not positive_value_exists(new_candidate.we_vote_hosted_profile_image_url_large):
                            # Only run this if we have a ballotpedia_image_id and no saved profile image
                            results = retrieve_and_save_ballotpedia_candidate_images(new_candidate)
                            if results['success']:
                                new_candidate = results['candidate']
                        # Create link to office if it doesn't exist
                        results = candidate_manager.get_or_create_candidate_to_office_link(
                            candidate_we_vote_id=new_candidate.we_vote_id,
                            contest_office_we_vote_id=one_batch_row_action.contest_office_we_vote_id,
                            google_civic_election_id=google_civic_election_id,
                            state_code=new_candidate.state_code)
                    except Exception as e:
                        success = False
                        status += "CANDIDATE_RETRIEVE_ERROR"
                        handle_exception(e, logger=logger, exception_message=status)
        elif update_entry_flag:
            candidate_we_vote_id = one_batch_row_action.candidate_we_vote_id

            results = candidate_manager.update_candidate_row_entry(candidate_we_vote_id, update_values)
            if results['candidate_updated']:
                new_candidate = results['updated_candidate']
                number_of_candidates_updated += 1
                success = True
                if positive_value_exists(retrieve_ballotpedia_image) \
                        and not positive_value_exists(new_candidate.we_vote_hosted_profile_image_url_large):
                    # Only run this if we have a ballotpedia_image_id and no saved profile image
                    results = retrieve_and_save_ballotpedia_candidate_images(new_candidate)
                    if results['success']:
                        new_candidate = results['candidate']
                # Create link to office if it doesn't exist
                results = candidate_manager.get_or_create_candidate_to_office_link(
                    candidate_we_vote_id=new_candidate.we_vote_id,
                    contest_office_we_vote_id=one_batch_row_action.contest_office_we_vote_id,
                    google_civic_election_id=google_civic_election_id,
                    state_code=new_candidate.state_code)
        else:
            # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
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
        status += "IMPORT_CANDIDATE_ENTRY:OFFICE_HELD_CREATED"
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


def import_politician_data_from_batch_row_actions(batch_header_id, batch_row_id, create_entry_flag=False,
                                                  update_entry_flag=False):
    """
    Import batch_rows for politician, IMPORT_CREATE or IMPORT_ADD_TO_EXISTING
    Process batch row entries in order to create or update Politician entries
    :param batch_header_id: 
    :param batch_row_id: 
    :param create_entry_flag: set to True for IMPORT_CREATE
    :param update_entry_flag: set to True for IMPORT_ADD_TO_EXISTING
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

    batch_row_action_list_found = False
    try:
        batch_row_action_list = BatchRowActionPolitician.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
            kind_of_action = IMPORT_CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
            kind_of_action = IMPORT_ADD_TO_EXISTING
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
        # politician_email_address = one_batch_row_action.politician_email_address
        politician_email = one_batch_row_action.politician_email
        politician_email2 = one_batch_row_action.politician_email2
        politician_email3 = one_batch_row_action.politician_email3
        politician_phone_number = one_batch_row_action.politician_phone_number
        politician_phone_number2 = one_batch_row_action.politician_phone_number2
        politician_phone_number3 = one_batch_row_action.politician_phone_number3
        politician_twitter_handle = one_batch_row_action.politician_twitter_handle
        politician_twitter_handle2 = one_batch_row_action.politician_twitter_handle2
        politician_twitter_handle3 = one_batch_row_action.politician_twitter_handle3
        politician_twitter_handle4 = one_batch_row_action.politician_twitter_handle4
        politician_twitter_handle5 = one_batch_row_action.politician_twitter_handle5
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
                results = politician_manager.create_politician_row_entry(
                    politician_name=politician_name,
                    politician_first_name=politician_first_name,
                    politician_middle_name=politician_middle_name,
                    politician_last_name=politician_last_name,
                    ctcl_uuid=ctcl_uuid,
                    political_party=political_party,
                    politician_email=politician_email,
                    politician_email2=politician_email2,
                    politician_email3=politician_email3,
                    politician_phone_number=politician_phone_number,
                    politician_phone_number2=politician_phone_number2,
                    politician_phone_number3=politician_phone_number3,
                    politician_twitter_handle=politician_twitter_handle,
                    politician_twitter_handle2=politician_twitter_handle2,
                    politician_twitter_handle3=politician_twitter_handle3,
                    politician_twitter_handle4=politician_twitter_handle4,
                    politician_twitter_handle5=politician_twitter_handle5,
                    politician_facebook_id=politician_facebook_id,
                    politician_googleplus_id=politician_googleplus_id,
                    politician_youtube_id=politician_youtube_id,
                    politician_website_url=politician_website_url)
                if results['new_politician_created']:
                    number_of_politicians_created += 1
                    success = True
                    # now update BatchRowActionPolitician table entry
                    try:
                        one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                        new_politician = results['new_politician']
                        one_batch_row_action.politician_we_vote_id = new_politician.we_vote_id
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "POLITICIAN_RETRIEVE_ERROR "
                        handle_exception(e, logger=logger, exception_message=status)
            elif update_entry_flag:
                politician_we_vote_id = one_batch_row_action.politician_we_vote_id
                results = politician_manager.update_politician_row_entry(
                    politician_name=politician_name,
                    politician_first_name=politician_first_name,
                    politician_middle_name=politician_middle_name,
                    politician_last_name=politician_last_name,
                    ctcl_uuid=ctcl_uuid,
                    political_party=political_party,
                    politician_email=politician_email,
                    politician_email2=politician_email2,
                    politician_email3=politician_email3,
                    politician_twitter_handle=politician_twitter_handle,
                    politician_twitter_handle2=politician_twitter_handle2,
                    politician_twitter_handle3=politician_twitter_handle3,
                    politician_twitter_handle4=politician_twitter_handle4,
                    politician_twitter_handle5=politician_twitter_handle5,
                    politician_phone_number=politician_phone_number,
                    politician_phone_number2=politician_phone_number2,
                    politician_phone_number3=politician_phone_number3,
                    politician_facebook_id=politician_facebook_id,
                    politician_googleplus_id=politician_googleplus_id,
                    politician_youtube_id=politician_youtube_id,
                    politician_website_url=politician_website_url,
                    politician_we_vote_id=politician_we_vote_id)
                if results['politician_updated']:
                    number_of_politicians_updated += 1
                    success = True
            else:
                # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
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
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
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
                organization_name=one_batch_row_action.organization_name,
                organization_website=one_batch_row_action.organization_website,
                organization_twitter_handle=one_batch_row_action.organization_twitter_handle,
                organization_email=one_batch_row_action.organization_email,
                organization_facebook=one_batch_row_action.organization_facebook,
                organization_image=temp_org_image,
                twitter_id=twitter_id_for_new_organization)

            if not results['organization_created']:
                continue

            number_of_organizations_created += 1
            organization = results['organization']
            success = True

            # now update BatchRowActionOrganization table entry
            try:
                one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
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
                organization.organization_contact_form_url = one_batch_row_action.organization_contact_form_url
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
            # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
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


def import_polling_location_data_from_batch_row_actions(
        batch_header_id, batch_row_id, create_entry_flag=False, update_entry_flag=False):
    success = False
    status = ""
    number_created = 0
    number_updated = 0
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_POLLING_LOCATION_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':           success,
            'status':            status,
            'number_created':    number_created,
            'number_updated':    number_updated
        }
        return results

    try:
        batch_row_action_list = BatchRowActionPollingLocation.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
        else:
            # error handling
            status += "IMPORT_POLLING_LOCATION_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':         success,
                'status':          status,
                'number_created':  number_created,
                'number_updated':  number_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionPollingLocation.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    if not batch_row_action_list_found:
        status += "IMPORT_POLLING_LOCATION_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_created':    number_created,
            'number_updated':    number_updated
        }
        return results

    if update_entry_flag:
        status += "POLLING_LOCATION_UPDATE_NOT_WORKING YET "

    polling_location_manager = PollingLocationManager()
    for one_batch_row_action in batch_row_action_list:
        if create_entry_flag:
            results = polling_location_manager.update_or_create_polling_location(
                one_batch_row_action.polling_location_we_vote_id, '',
                one_batch_row_action.location_name, '', '',
                one_batch_row_action.line1, one_batch_row_action.line2,
                one_batch_row_action.city, one_batch_row_action.state, one_batch_row_action.zip_long,
                county_name=one_batch_row_action.county_name,
                precinct_name=one_batch_row_action.precinct_name,
                source_code=one_batch_row_action.source_code,
                latitude=one_batch_row_action.latitude,
                longitude=one_batch_row_action.longitude,
                use_for_bulk_retrieve=one_batch_row_action.use_for_bulk_retrieve,
                polling_location_deleted=one_batch_row_action.polling_location_deleted)

            if not results['polling_location_created']:
                continue

            number_created += 1
            polling_location = results['polling_location']
            success = True

            # now update BatchRowActionPollingLocation table entry
            try:
                one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                one_batch_row_action.polling_location_we_vote_id = polling_location.we_vote_id
                one_batch_row_action.save()
            except Exception as e:
                success = False
                status += "BATCH_ROW_ACTION_POLLING_LOCATION_SAVE_ERROR " + str(e) + " "
                handle_exception(e, logger=logger, exception_message=status)

            try:
                # Now update with additional fields
                polling_location.city = one_batch_row_action.city
                polling_location.county_name = one_batch_row_action.county_name
                polling_location.line1 = one_batch_row_action.line1
                polling_location.line2 = one_batch_row_action.line2
                polling_location.location_name = one_batch_row_action.location_name
                polling_location.polling_location_deleted = one_batch_row_action.polling_location_deleted
                polling_location.precinct_name = one_batch_row_action.precinct_name
                polling_location.source_code = one_batch_row_action.source_code
                polling_location.state = one_batch_row_action.state
                polling_location.use_for_bulk_retrieve = one_batch_row_action.use_for_bulk_retrieve
                polling_location.zip_long = one_batch_row_action.zip_long
                polling_location.save()
            except Exception as e:
                status += "FAILED_SAVING_POLLING_LOCATION: " + str(e) + " "
        elif update_entry_flag:
            pass
            # organization_we_vote_id = one_batch_row_action.organization_we_vote_id
            # results = organization_manager.update_organization_row_entry(organization_title, organization_subtitle,
            #                                                            organization_text, state_code, ctcl_uuid,
            #                                                         google_civic_election_id, organization_we_vote_id)
            # if results['organization_updated']:
            #     number_updated += 1
            #     success = True
        else:
            # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
            status += "IMPORT_POLLING_LOCATION_ENTRY:NO_CREATE_OR_UPDATE_ERROR "
            results = {
                'success':         success,
                'status':          status,
                'number_created':  number_created,
                'number_updated':  number_updated,
            }
            return results

    if number_created:
        status += "IMPORT_POLLING_LOCATION_ENTRY-CREATED "
    elif number_updated:
        status += "IMPORT_POLLING_LOCATION_ENTRY-UPDATED "

    results = {
        'success':           success,
        'status':            status,
        'number_created':    number_created,
        'number_updated':    number_updated,
    }
    return results


def import_position_data_from_batch_row_actions(
        batch_header_id,
        batch_row_id,
        create_entry_flag=False,
        update_entry_flag=False,
        voter_device_id=None):
    success = False
    status = ""
    number_of_positions_created = 0
    number_of_positions_updated = 0
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status = "IMPORT_POSITION_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_positions_created':    number_of_positions_created,
            'number_of_positions_updated':    number_of_positions_updated
        }
        return results

    try:
        batch_row_action_list = BatchRowActionPosition.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
        else:
            # error handling
            status += "IMPORT_POSITION_ENTRY-KIND_OF_ACTION_MISSING"
            results = {
                'success':                      success,
                'status':                       status,
                'number_of_positions_created':  number_of_positions_created,
                'number_of_positions_updated':  number_of_positions_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionPosition.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    if not batch_row_action_list_found:
        status += "IMPORT_POSITION_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                       success,
            'status':                        status,
            'number_of_positions_created':    number_of_positions_created,
            'number_of_positions_updated':    number_of_positions_updated
        }
        return results

    voter_id = 0
    volunteer_task_manager = VolunteerTaskManager()
    voter_we_vote_id = ""
    if positive_value_exists(voter_device_id):
        voter = fetch_voter_from_voter_device_link(voter_device_id)
        if hasattr(voter, 'we_vote_id'):
            voter_id = voter.id
            voter_we_vote_id = voter.we_vote_id

    position_manager = PositionManager()
    google_civic_election_id = 0
    unique_organization_we_vote_id_list = []
    for one_batch_row_action in batch_row_action_list:
        if create_entry_flag:
            position_we_vote_id = ""
            # DALE 2019-08-05 Refactoring this function to use update_values will take some time
            results = position_manager.update_or_create_position(
                position_we_vote_id=position_we_vote_id,
                organization_we_vote_id=one_batch_row_action.organization_we_vote_id,
                google_civic_election_id=one_batch_row_action.google_civic_election_id,
                state_code=one_batch_row_action.state_code,
                ballot_item_display_name=one_batch_row_action.ballot_item_display_name,
                candidate_we_vote_id=one_batch_row_action.candidate_campaign_we_vote_id,
                measure_we_vote_id=one_batch_row_action.contest_measure_we_vote_id,
                # politician_we_vote_id=one_batch_row_action.politician_we_vote_id,  # Not added to batch_row_action yet
                stance=one_batch_row_action.stance,
                set_as_public_position=True,
                statement_text=one_batch_row_action.statement_text,
                statement_html=one_batch_row_action.statement_html,
                more_info_url=one_batch_row_action.more_info_url,
            )
            # office_we_vote_id = one_batch_row_action.contest_office_we_vote_id,

            if not results['new_position_created']:
                continue

            # Store a list of organization voter guides we should refresh
            if positive_value_exists(one_batch_row_action.google_civic_election_id):
                # The election id should all be the same, so we just use the last one
                google_civic_election_id = one_batch_row_action.google_civic_election_id
            if positive_value_exists(one_batch_row_action.organization_we_vote_id) and \
                    one_batch_row_action.organization_we_vote_id not in unique_organization_we_vote_id_list:
                unique_organization_we_vote_id_list.append(one_batch_row_action.organization_we_vote_id)

            number_of_positions_created += 1
            position = results['position']
            success = True

            # Give volunteer credit - if here, we know a position was just created
            if positive_value_exists(voter_we_vote_id):
                try:
                    # Give the volunteer who entered this credit
                    task_results = volunteer_task_manager.create_volunteer_task_completed(
                        action_constant=VOLUNTEER_ACTION_POSITION_SAVED,
                        voter_id=voter_id,
                        voter_we_vote_id=voter_we_vote_id,
                    )
                except Exception as e:
                    status += 'FAILED_TO_CREATE_VOLUNTEER_TASK_COMPLETED: ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

            # now update BatchRowActionPosition table entry
            try:
                one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                one_batch_row_action.position_we_vote_id = position.we_vote_id
                one_batch_row_action.save()
            except Exception as e:
                success = False
                status += "BATCH_ROW_ACTION_POSITION_SAVE_ERROR "
                handle_exception(e, logger=logger, exception_message=status)

            # try:
            #     # Now update position with additional fields
            #     position.organization_instagram_handle = one_batch_row_action.organization_instagram_handle
            #     position.organization_contact_name = one_batch_row_action.organization_contact_name
            #     position.save()
            # except Exception as e:
            #     pass
        elif update_entry_flag:
            update_values = {}
            # These fields we only replace data -- we don't need to wipe any values out
            if positive_value_exists(one_batch_row_action.organization_we_vote_id):
                update_values['organization_we_vote_id'] = one_batch_row_action.organization_we_vote_id
            if positive_value_exists(one_batch_row_action.google_civic_election_id):
                update_values['google_civic_election_id'] = one_batch_row_action.google_civic_election_id
            if positive_value_exists(one_batch_row_action.state_code):
                update_values['state_code'] = one_batch_row_action.state_code
            if positive_value_exists(one_batch_row_action.candidate_campaign_we_vote_id):
                update_values['candidate_campaign_we_vote_id'] = one_batch_row_action.candidate_campaign_we_vote_id
            if positive_value_exists(one_batch_row_action.contest_measure_we_vote_id):
                update_values['contest_measure_we_vote_id'] = one_batch_row_action.contest_measure_we_vote_id
            if positive_value_exists(one_batch_row_action.stance):
                update_values['stance'] = one_batch_row_action.stance
            # These fields we will clear
            update_values['statement_text'] = one_batch_row_action.statement_text \
                if positive_value_exists(one_batch_row_action.statement_text) else ""
            update_values['statement_html'] = one_batch_row_action.statement_html \
                if positive_value_exists(one_batch_row_action.statement_html) else ""
            update_values['more_info_url'] = one_batch_row_action.more_info_url \
                if positive_value_exists(one_batch_row_action.more_info_url) else ""

            position_we_vote_id = one_batch_row_action.position_we_vote_id
            results = position_manager.update_position_row_entry(position_we_vote_id, update_values)
            if results['position_updated']:
                number_of_positions_updated += 1
                success = True
        else:
            # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
            status += "IMPORT_POSITION_ENTRY:NO_CREATE_OR_UPDATE_ERROR "
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_positions_created':  number_of_positions_created,
                'number_of_positions_updated':  number_of_positions_updated,
            }
            return results

    if number_of_positions_created:
        status += "IMPORT_POSITION_ENTRY: POSITIONS_CREATED "
    elif number_of_positions_updated:
        status += "IMPORT_POSITION_ENTRY: POSITIONS_UPDATED "

    if positive_value_exists(number_of_positions_created) or positive_value_exists(number_of_positions_updated):
        # Refresh all voter guides that were touched by new positions
        for organization_we_vote_id in unique_organization_we_vote_id_list:
            results = refresh_existing_voter_guides(google_civic_election_id, organization_we_vote_id)
            # voter_guide_updated_count = results['voter_guide_updated_count']

    results = {
        'success':                      success,
        'status':                       status,
        'number_of_positions_created':  number_of_positions_created,
        'number_of_positions_updated':  number_of_positions_updated,
    }
    return results


def import_update_or_create_office_held_entry(batch_header_id, batch_row_id):
    """
    Either create or update OfficeHeld table entry with batch_row office_held details 
    
    :param batch_header_id: 
    :param batch_row_id: 
    :return: 
    """
    success = False
    status = ""
    office_held_updated = False
    new_office_held_created = False
    new_office_held = ''
    number_of_offices_held_created = 0
    number_of_offices_held_updated = 0
    batch_row_action_list_found = False

    if not positive_value_exists(batch_header_id):
        status += "IMPORT_CREATE_OR_UPDATE_OFFICE_HELD_ENTRY-BATCH_HEADER_ID_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_offices_held_created':    number_of_offices_held_created,
            'number_of_offices_held_updated':    number_of_offices_held_updated
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
        status += "IMPORT_CREATE_OR_UPDATE_OFFICE_HELD_ENTRY-BATCH_DESCRIPTION_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_offices_held_created':    number_of_offices_held_created,
            'number_of_offices_held_updated':    number_of_offices_held_updated
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
        status += "IMPORT_CREATE_OR_UPDATE_OFFICE_HELD_ENTRY-BATCH_HEADER_MAP_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_offices_held_created':    number_of_offices_held_created,
            'number_of_offices_held_updated':    number_of_offices_held_updated
        }
        return results

    batch_row_action_list_found = False
    try:
        batch_row_action_office_held_list = BatchRowActionOfficeHeld.objects.all()
        batch_row_action_office_held_list = batch_row_action_office_held_list.filter(
            batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_office_held_list = batch_row_action_office_held_list.filter(
                batch_row_id=batch_row_id)

        if len(batch_row_action_office_held_list):
            batch_row_action_list_found = True
            # TODO assumption is that length of this list is going to be one, single record match
            one_batch_row_action = batch_row_action_office_held_list[0]
    except BatchRowActionOfficeHeld.DoesNotExist:
        # batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    # batch_manager = BatchManager()

    if not batch_row_action_list_found:
        status += "IMPORT_CREATE_OR_UPDATE_OFFICE_HELD_ENTRY-BATCH_ROW_ACTION_LIST_MISSING"
        results = {
            'success':                              success,
            'status':                               status,
            'number_of_offices_held_created':    number_of_offices_held_created,
            'number_of_offices_held_updated':    number_of_offices_held_updated
        }
        return results

    if batch_description_found and batch_header_map_found and batch_row_action_list_found:

        state_code = one_batch_row_action.state_code
        office_held_name = one_batch_row_action.office_held_name
        if positive_value_exists(one_batch_row_action.google_civic_election_id):
            google_civic_election_id = str(one_batch_row_action.google_civic_election_id)
        else:
            google_civic_election_id = str(batch_description.google_civic_election_id)
        ctcl_uuid = one_batch_row_action.ctcl_uuid
        office_held_description = one_batch_row_action.office_held_description
        office_held_is_partisan = one_batch_row_action.office_held_is_partisan
        office_held_name_es = one_batch_row_action.office_held_name_es
        office_held_description_es = one_batch_row_action.office_held_description_es

        # Look up OfficeHeld to see if an entry exists

        kind_of_action = one_batch_row_action.kind_of_action
        # Only add entries with kind_of_action set to either IMPORT_CREATE or IMPORT_ADD_TO_EXISTING.
        office_held_manager = OfficeHeldManager()
        if kind_of_action == IMPORT_CREATE:
            # call create_office_held_row_entry
            results = office_held_manager.create_office_held_row_entry(office_held_name, state_code,
                                                                             office_held_description, ctcl_uuid,
                                                                             office_held_is_partisan,
                                                                             google_civic_election_id)

            if results['new_office_held_created']:
                success = True
                number_of_offices_held_created += 1

                # now update BatchRowActionOfficeHeld table entry
                try:
                    one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                    one_batch_row_action.office_held_we_vote_id = \
                        results['new_office_held'].we_vote_id
                    one_batch_row_action.save()
                except Exception as e:
                    success = False
                    new_office_held_created = False
                    status += "IMPORT_UPDATE_OR_CREATE_OFFICE_HELD_ENTRY-OFFICE_HELD_RETRIEVE_ERROR"
                    handle_exception(e, logger=logger, exception_message=status)
        elif kind_of_action == IMPORT_ADD_TO_EXISTING:
            # call update_office_held_row_entry
            office_held_we_vote_id = one_batch_row_action.office_held_we_vote_id
            results = office_held_manager.update_office_held_row_entry(office_held_name, state_code,
                                                                             office_held_description,
                                                                             ctcl_uuid,
                                                                             office_held_is_partisan,
                                                                             google_civic_election_id,
                                                                             office_held_we_vote_id,
                                                                             office_held_name_es,
                                                                             office_held_description_es)
            if results['office_held_updated']:
                success = True
                office_held_updated = True
                number_of_offices_held_updated += 1

            try:
                # store elected_we_vote_id from OfficeHeld table
                updated_office_held = results['updated_office_held']
                one_batch_row_action.office_held_we_vote_id = updated_office_held.we_vote_id
                one_batch_row_action.save()
            except Exception as e:
                success = False
                new_office_held_created = False
                status += "IMPORT_CREATE_OR_UPDATE_OFFICE_HELD_ENTRY-OFFICE_HELD_RETRIEVE_ERROR"
                handle_exception(e, logger=logger, exception_message=status)
        else:
            # kind_of_action is either TBD or DO_NOT_PROCESS, do nothing
            success = True
            status = "IMPORT_CREATE_OR_UPDATE_OFFICE_HELD_ENTRY-ACTION_TBD_OR_DO_NOT_PROCESS"
    if number_of_offices_held_created:
        status = "IMPORT_CREATE_OR_UPDATE_OFFICE_HELD_ENTRY-OFFICE_HELD_CREATED"
    elif number_of_offices_held_updated:
        status = "IMPORT_CREATE_OR_UPDATE_OFFICE_HELD_ENTRY-OFFICE_HELD_UPDATED"
    results = {
        'success':                              success,
        'status':                               status,
        'new_office_held_created':           new_office_held_created,
        'office_held_updated':               office_held_updated,
        'new_office_held':                   new_office_held,
        'number_of_offices_held_created':    number_of_offices_held_created,
        'number_of_offices_held_updated':    number_of_offices_held_updated
        }
    return results


def import_ballot_item_data_from_batch_row_actions(batch_header_id, batch_row_id,
                                                   create_entry_flag=False, update_entry_flag=False):
    """
    Import batch_rows for ballot_items, IMPORT_CREATE or IMPORT_ADD_TO_EXISTING
    Process batch row entries in order to create or update ballot_item entries
    :param batch_header_id:
    :param batch_row_id:
    :param create_entry_flag: set to True for IMPORT_CREATE
    :param update_entry_flag: set to True for IMPORT_ADD_TO_EXISTING
    :return:
    """
    success = True
    status = ""
    number_of_ballot_items_created = 0
    number_of_ballot_items_updated = 0
    new_ballot_item = ''

    if not positive_value_exists(batch_header_id):
        status += "IMPORT_BALLOT_ITEM_ENTRY-BATCH_HEADER_ID_MISSING "
        success = False
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_ballot_items_created':   number_of_ballot_items_created,
            'number_of_ballot_items_updated':   number_of_ballot_items_updated
        }
        return results

    try:
        batch_description = BatchDescription.objects.using('readonly').get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        batch_description = BatchDescription()
        batch_description_found = False
        status += "IMPORT_BALLOT_ITEM_ENTRY-BATCH_DESCRIPTION_MISSING "
    except Exception as e:
        batch_description_found = False
        status += "IMPORT_BALLOT_ITEM_ENTRY-ERROR_RETRIEVING_BATCH_DESCRIPTION: " + str(e) + " "

    if not batch_description_found:
        success = False
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_ballot_items_created':   number_of_ballot_items_created,
            'number_of_ballot_items_updated':   number_of_ballot_items_updated
        }
        return results

        # kind_of_batch = batch_description.kind_of_batch

    try:
        batch_header_map = BatchHeaderMap.objects.using('readonly').get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        batch_header_map_found = False
        status += "IMPORT_BALLOT_ITEM_ENTRY-BATCH_HEADER_MAP_MISSING "
    except Exception as e:
        batch_header_map_found = False
        status += "ERROR_RETRIEVING_BATCH_HEADER_MAP: " + str(e) + " "

    if not batch_header_map_found:
        success = False
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_ballot_items_created':   number_of_ballot_items_created,
            'number_of_ballot_items_updated':   number_of_ballot_items_updated
        }
        return results

    batch_row_action_list_found = False
    try:
        batch_row_action_list = BatchRowActionBallotItem.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(batch_row_id):
            batch_row_action_list = batch_row_action_list.filter(batch_row_id=batch_row_id)

        if positive_value_exists(create_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_CREATE)
            kind_of_action = IMPORT_CREATE
        elif positive_value_exists(update_entry_flag):
            batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_ADD_TO_EXISTING)
            kind_of_action = IMPORT_ADD_TO_EXISTING
        else:
            # error handling
            status += "IMPORT_BALLOT_ITEM_ENTRY-KIND_OF_ACTION_MISSING "
            success = False
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_ballot_items_created':   number_of_ballot_items_created,
                'number_of_ballot_items_updated':   number_of_ballot_items_updated
            }
            return results

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except BatchRowActionBallotItem.DoesNotExist:
        batch_row_action_list = []
        batch_row_action_list_found = False
        pass

    if not batch_row_action_list_found:
        status += "IMPORT_BALLOT_ITEM_ENTRY-BATCH_ROW_ACTION_LIST_NOT_FOUND "
        results = {
            'success':                          success,
            'status':                           status,
            'number_of_ballot_items_created':   number_of_ballot_items_created,
            'number_of_ballot_items_updated':   number_of_ballot_items_updated
        }
        return results

    ballot_returned_manager = BallotReturnedManager()
    ballot_returned_entries_that_exist = []
    measure_manager = ContestMeasureManager()
    office_manager = ContestOfficeManager()
    polling_location_manager = PollingLocationManager()
    for one_batch_row_action in batch_row_action_list:
        # Find the column in the incoming batch_row with the header == ballot_item_display_name
        ballot_item_display_name = one_batch_row_action.ballot_item_display_name
        local_ballot_order = one_batch_row_action.local_ballot_order
        if positive_value_exists(one_batch_row_action.google_civic_election_id):
            google_civic_election_id = str(one_batch_row_action.google_civic_election_id)
        else:
            google_civic_election_id = str(batch_description.google_civic_election_id)
        # Set this for the possible creation of BallotReturned entry
        polling_location_we_vote_id = one_batch_row_action.polling_location_we_vote_id
        state_code = one_batch_row_action.state_code
        # Make sure we have both ids for office
        if positive_value_exists(one_batch_row_action.contest_office_we_vote_id) \
                and not positive_value_exists(one_batch_row_action.contest_office_id):
            one_batch_row_action.contest_office_id = office_manager.fetch_contest_office_id_from_we_vote_id(
                one_batch_row_action.contest_office_we_vote_id)
        elif positive_value_exists(one_batch_row_action.contest_office_id) \
                and not positive_value_exists(one_batch_row_action.contest_office_we_vote_id):
            one_batch_row_action.contest_office_we_vote_id = office_manager.fetch_contest_office_we_vote_id_from_id(
                one_batch_row_action.contest_office_id)
        # Make sure we have both ids for measure
        if positive_value_exists(one_batch_row_action.contest_measure_we_vote_id) \
                and not positive_value_exists(one_batch_row_action.contest_measure_id):
            one_batch_row_action.contest_measure_id = measure_manager.fetch_contest_measure_id_from_we_vote_id(
                one_batch_row_action.contest_measure_we_vote_id)
        elif positive_value_exists(one_batch_row_action.contest_measure_id) \
                and not positive_value_exists(one_batch_row_action.contest_measure_we_vote_id):
            one_batch_row_action.contest_measure_we_vote_id = measure_manager.fetch_contest_measure_we_vote_id_from_id(
                one_batch_row_action.contest_measure_id)
        defaults = {
            'ballot_item_id':               one_batch_row_action.ballot_item_id,
            'contest_office_id':            one_batch_row_action.contest_office_id,
            'contest_measure_id':           one_batch_row_action.contest_measure_id,
            'contest_office_we_vote_id':    one_batch_row_action.contest_office_we_vote_id,
            'contest_measure_we_vote_id':   one_batch_row_action.contest_measure_we_vote_id,
            'measure_subtitle':             one_batch_row_action.measure_subtitle,
            'measure_url':                  one_batch_row_action.measure_url,
            'no_vote_description':          one_batch_row_action.no_vote_description,
            'polling_location_we_vote_id':  one_batch_row_action.polling_location_we_vote_id,
            'state_code':                   one_batch_row_action.state_code,
            'yes_vote_description':         one_batch_row_action.yes_vote_description,
        }

        # Look up BallotItem to see if an entry exists
        # These five parameters are needed to look up in BallotItem table for a match
        if positive_value_exists(ballot_item_display_name) and positive_value_exists(state_code) \
                and positive_value_exists(google_civic_election_id):
            ballot_item_manager = BallotItemManager()
            if create_entry_flag:
                results = ballot_item_manager.create_ballot_item_row_entry(ballot_item_display_name,
                                                                           local_ballot_order, state_code,
                                                                           google_civic_election_id, defaults)
                if results['new_ballot_item_created']:
                    number_of_ballot_items_created += 1
                    # now update BatchRowActionBallotItem table entry
                    try:
                        one_batch_row_action.kind_of_action = IMPORT_ADD_TO_EXISTING
                        new_ballot_item = results['ballot_item']
                        one_batch_row_action.save()
                    except Exception as e:
                        success = False
                        status += "BALLOT_ITEM_RETRIEVE_ERROR: " + str(e) + " "
                        handle_exception(e, logger=logger, exception_message=status)
                else:
                    status += results['status']
            elif update_entry_flag:
                results = ballot_item_manager.update_ballot_item_row_entry(
                    ballot_item_display_name,
                    local_ballot_order,
                    google_civic_election_id,
                    defaults)
                if results['ballot_item_updated']:
                    number_of_ballot_items_updated += 1
                else:
                    status += results['status']
            else:
                # This is error, it shouldn't reach here, we are handling IMPORT_CREATE or UPDATE entries only.
                status += "IMPORT_BALLOT_ITEM_ENTRY:NO_CREATE_OR_UPDATE_ERROR "
                success = False
                results = {
                    'success':                          success,
                    'status':                           status,
                    'number_of_ballot_items_created':   number_of_ballot_items_created,
                    'number_of_ballot_items_updated':   number_of_ballot_items_updated,
                    'new_ballot_item':                  new_ballot_item,
                }
                return results

            if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
                # If we are here, we want to make sure that we have a BallotReturned entry for this BallotItem
                combined_key = str(polling_location_we_vote_id) + "-" + str(google_civic_election_id)
                if combined_key in ballot_returned_entries_that_exist:
                    pass
                else:
                    results = ballot_returned_manager.retrieve_ballot_returned_from_polling_location_we_vote_id(
                        polling_location_we_vote_id, google_civic_election_id)
                    if results['success'] and not results['ballot_returned_found']:
                        # Create new BallotReturned entry
                        voter_id = 0
                        polling_location_results = polling_location_manager.retrieve_polling_location_by_id(
                            0, polling_location_we_vote_id)
                        if polling_location_results['polling_location_found']:
                            polling_location = polling_location_results['polling_location']
                            latitude = polling_location.latitude
                            longitude = polling_location.longitude
                            polling_location_name = polling_location.location_name
                            results = polling_location.get_text_for_map_search_results()
                            text_for_map_search = results['text_for_map_search']
                            state_code = polling_location.state

                            create_results = ballot_returned_manager.update_or_create_ballot_returned(
                                polling_location_we_vote_id, voter_id, google_civic_election_id,
                                latitude=latitude, longitude=longitude,
                                ballot_location_display_name=polling_location_name,
                                text_for_map_search=text_for_map_search,
                                normalized_state=state_code)
                            if create_results['ballot_returned_found']:
                                ballot_returned_entries_that_exist.append(combined_key)
                                status += "BALLOT_RETURNED_CREATED_OR_UPDATED "
                            else:
                                status += create_results['status']
                        else:
                            status += "POLLING_LOCATION_NOT_FOUND: '" + polling_location_we_vote_id + "' "
                    else:
                        # Either retrieve failed, or ballot_returned_found was true
                        pass
            else:
                # Missing polling_location_we_vote_id or google_civic_election_id
                pass
        else:
            status += "IMPORT_BALLOT_ITEM_ENTRY:MISSING_DISPLAY_NAME-STATE_CODE-OR_ELECTION_ID "

    # if number_of_ballot_items_created or number_of_ballot_items_updated:
    #     if positive_value_exists(polling_location_we_vote_id) and positive_value_exists(google_civic_election_id):
    #         # Make sure there is a ballot_returned entry
    #         results = ballot_returned_manager.retrieve_ballot_returned_from_polling_location_we_vote_id(
    #             polling_location_we_vote_id, google_civic_election_id)
    #         if results['success'] and not results['ballot_returned_found']:

    if number_of_ballot_items_created:
        status += "IMPORT_BALLOT_ITEM_ENTRY:BALLOT_ITEM_CREATED "
    elif number_of_ballot_items_updated:
        status += "IMPORT_BALLOT_ITEM_ENTRY:BALLOT_ITEM_UPDATED "
    else:
        status += "IMPORT_BALLOT_ITEM_ENTRY:BALLOT_ITEM_NOT_UPDATED_OR_CREATED "

    results = {
        'success':                          success,
        'status':                           status,
        'number_of_ballot_items_created':   number_of_ballot_items_created,
        'number_of_ballot_items_updated':   number_of_ballot_items_updated,
        'new_ballot_item':                  new_ballot_item,
    }
    return results


def delete_ballot_item_data_from_batch_row_actions(batch_header_id, ballot_item_id=0):
    """
    Delete existing ballot_items, IMPORT_DELETE
    :param batch_header_id:
    :param ballot_item_id:
    :return:
    """
    success = True
    status = ""
    number_of_table_rows_deleted = 0

    if not positive_value_exists(batch_header_id):
        status += "IMPORT_BALLOT_ITEM_ENTRY-BATCH_HEADER_ID_MISSING "
        success = False
        results = {
            'success':                      success,
            'status':                       status,
            'number_of_table_rows_deleted': number_of_table_rows_deleted,
        }
        return results

    try:
        batch_description = BatchDescription.objects.using('readonly').get(batch_header_id=batch_header_id)
        batch_description_found = True
    except BatchDescription.DoesNotExist:
        # This is fine
        batch_description = BatchDescription()
        batch_description_found = False

    if not batch_description_found:
        status += "IMPORT_BALLOT_ITEM_ENTRY-BATCH_DESCRIPTION_MISSING "
        success = False
        results = {
            'success':                      success,
            'status':                       status,
            'number_of_table_rows_deleted': number_of_table_rows_deleted,
        }
        return results

    try:
        batch_header_map = BatchHeaderMap.objects.using('readonly').get(batch_header_id=batch_header_id)
        batch_header_map_found = True
    except BatchHeaderMap.DoesNotExist:
        # This is fine
        batch_header_map_found = False
        success = False

    if not batch_header_map_found:
        status += "IMPORT_BALLOT_ITEM_ENTRY-BATCH_HEADER_MAP_MISSING "
        success = False
        results = {
            'success':                      success,
            'status':                       status,
            'number_of_table_rows_deleted': number_of_table_rows_deleted,
        }
        return results

    batch_row_action_list_found = False
    try:
        batch_row_action_list = BatchRowActionBallotItem.objects.all()
        batch_row_action_list = batch_row_action_list.filter(batch_header_id=batch_header_id)
        if positive_value_exists(ballot_item_id):
            batch_row_action_list = batch_row_action_list.filter(ballot_item_id=ballot_item_id)
        batch_row_action_list = batch_row_action_list.filter(kind_of_action=IMPORT_DELETE)

        if len(batch_row_action_list):
            batch_row_action_list_found = True

    except Exception as e:
        status += "FAILED_BATCH_ROW_ACTION_BALLOT_ITEM_RETRIEVE: " + str(e) + " "
        batch_row_action_list = []
        batch_row_action_list_found = False

    if not batch_row_action_list_found:
        status += "DELETE_BALLOT_ITEM_ENTRY-BATCH_ROW_ACTION_LIST_NOT_FOUND "
        results = {
            'success':                      success,
            'status':                       status,
            'number_of_table_rows_deleted': number_of_table_rows_deleted,
        }
        return results

    for one_batch_row_action in batch_row_action_list:
        ballot_item_manager = BallotItemManager()
        results = ballot_item_manager.delete_ballot_item(ballot_item_id=one_batch_row_action.ballot_item_id)
        if results['ballot_item_deleted']:
            try:
                one_batch_row_action.kind_of_action = IMPORT_ALREADY_DELETED
                one_batch_row_action.save()
                number_of_table_rows_deleted += 1
                status += "DELETE_BALLOT_ITEM_ENTRY-SUCCESS "
            except Exception as e:
                status += "DELETE_BALLOT_ITEM_ENTRY-ERROR: " + str(e) + " "
        else:
            status += "BALLOT_ITEM_NOT_DELETED "

    results = {
        'success':                      success,
        'status':                       status,
        'number_of_table_rows_deleted': number_of_table_rows_deleted,
    }
    return results


def import_data_from_batch_row_actions(
        kind_of_batch,
        kind_of_action,
        batch_header_id,
        batch_row_id=0,
        state_code="",
        ballot_item_id=0,
        voter_device_id=""):
    """
    Cycle through and process batch_row_action entries.
    The kind_of_action is either IMPORT_CREATE or IMPORT_ADD_TO_EXISTING or IMPORT_DELETE.
    :param kind_of_batch:
    :param kind_of_action:
    :param batch_header_id:
    :param batch_row_id:
    :param state_code:
    :param ballot_item_id:
    :param voter_device_id:
    :return:
    """
    success = False
    status = ''
    number_of_table_rows_created = 0
    number_of_table_rows_updated = 0
    number_of_table_rows_deleted = 0
    create_flag = False
    update_flag = False
    delete_flag = False

    # for one_batch_row in batch_row_list:
    if kind_of_action == IMPORT_CREATE:
        create_flag = True
    elif kind_of_action == IMPORT_ADD_TO_EXISTING:
        update_flag = True
    elif kind_of_action == IMPORT_DELETE:
        delete_flag = True
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
            'number_of_table_rows_updated': number_of_table_rows_updated,
            'number_of_table_rows_deleted': number_of_table_rows_deleted,
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
            batch_header_id, batch_row_id, state_code, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_contest_offices_created']:
                # for now, do not handle batch_row_action_contest_office data
                # batch_row_action_contest_office = results['batch_row_action_contest_office']
                number_of_table_rows_created = results['number_of_contest_offices_created']
            elif results['number_of_contest_offices_updated']:
                number_of_table_rows_updated = results['number_of_contest_offices_updated']
            success = True
    elif kind_of_batch == OFFICE_HELD:
        results = import_office_held_data_from_batch_row_actions(
            batch_header_id, batch_row_id, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_offices_held_created']:
                # for now, do not handle batch_row_action_office_held data
                # batch_row_action_office_held = results['batch_row_action_office_held']
                number_of_table_rows_created = results['number_of_offices_held_created']
            elif results['number_of_offices_held_updated']:
                number_of_table_rows_updated = results['number_of_offices_held_updated']
            success = True
    elif kind_of_batch == MEASURE:
        results = import_measure_data_from_batch_row_actions(batch_header_id, batch_row_id, create_flag,
                                                             update_flag)
        status += results['status']
        if results['success']:
            if results['number_of_measures_created']:
                # for now, do not handle batch_row_action_measure data
                # batch_row_action_office_held = results['batch_row_action_office_held']
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
    elif kind_of_batch == IMPORT_POLLING_LOCATION:
        results = import_polling_location_data_from_batch_row_actions(
            batch_header_id, batch_row_id, create_flag, update_flag)
        status += results['status']
        if results['success']:
            if results['number_created']:
                number_of_table_rows_created = results['number_created']
            elif results['number_updated']:
                number_of_table_rows_updated = results['number_updated']
            success = True
    elif kind_of_batch == POSITION:
        results = import_position_data_from_batch_row_actions(
            batch_header_id,
            batch_row_id,
            create_flag,
            update_flag,
            voter_device_id=voter_device_id)
        status += results['status']
        if results['success']:
            if results['number_of_positions_created']:
                # for now, do not handle batch_row_action_politician data
                # batch_row_action_politician = results['batch_row_action_politician']
                number_of_table_rows_created = results['number_of_positions_created']
            elif results['number_of_positions_updated']:
                number_of_table_rows_updated = results['number_of_positions_updated']
            success = True
    elif kind_of_batch == IMPORT_BALLOT_ITEM:
        if create_flag or update_flag:
            results = import_ballot_item_data_from_batch_row_actions(
                batch_header_id, batch_row_id, create_flag, update_flag)
            status += results['status']
            if results['success']:
                if results['number_of_ballot_items_created']:
                    # for now, do not handle batch_row_action_ballot_item data
                    # batch_row_action_ballot_item = results['batch_row_action_ballot_items_created']
                    number_of_table_rows_created = results['number_of_ballot_items_created']
                elif results['number_of_ballot_items_updated']:
                    number_of_table_rows_updated = results['number_of_ballot_items_updated']
                success = True
        elif delete_flag:
            results = delete_ballot_item_data_from_batch_row_actions(
                batch_header_id, ballot_item_id=ballot_item_id)
            status += results['status']
            if results['success']:
                number_of_table_rows_deleted = results['number_of_table_rows_deleted']
                success = True
        else:
            status += "IMPORT_BALLOT_ITEM-NOT_CREATE_UPDATE_OR_DELETE "
            pass

    results = {
        'success':                      success,
        'status':                       status,
        'batch_header_id':              batch_header_id,
        'kind_of_batch':                kind_of_batch,
        'table_rows_created':           success,
        'number_of_table_rows_created': number_of_table_rows_created,
        'number_of_table_rows_updated': number_of_table_rows_updated,
        'number_of_table_rows_deleted': number_of_table_rows_deleted,
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


def export_voter_list_with_emails():
    """
    Exports voter list from VoterManager

    :return export_result: dictionary with status and voter list
    """
    voter_manager = VoterManager()
    export_result = dict()
    status = 'NO_EXPORT'
    export_result = voter_manager.retrieve_voter_list_with_emails()
    if export_result and export_result['voter_list']:
        status = 'SUCCESS'

    export_result = {
        'status':   status,
        'voter_list':   export_result['voter_list'],
    }

    return export_result

