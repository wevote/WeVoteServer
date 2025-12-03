# politician/controllers_data_cleaning.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.utils.timezone import now
import pytz

from config.base import get_environment_variable
from import_export_batches.controllers_data_cleaning import full_deduplication_for_next_state
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from wevote_functions.functions_date import convert_date_to_date_as_integer, generate_localized_datetime_from_obj
from .controllers import add_alternate_names_to_next_spot, find_duplicate_politician, \
    generate_campaignx_for_politician, merge_if_duplicate_politicians
from .models import DeduplicationNeededForStateToday, Politician, PoliticianManager, PoliticiansArePossibleDuplicates
from .controllers_generate_color import generate_background

POLITICIANS_SYNC_URL = get_environment_variable("POLITICIANS_SYNC_URL")  # politiciansSyncOut
TWITTER_API_ON = positive_value_exists(get_environment_variable("TWITTER_API_ON", no_exception=True))
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")
WEB_APP_ROOT_URL = get_environment_variable("WEB_APP_ROOT_URL")

logger = wevote_functions.admin.get_logger(__name__)


def batch_process_deduplication_scripts_politician():  # DEDUPLICATION_SCRIPTS_POLITICIAN
    all_states_deduplication_complete = False
    status = ':||: '
    success = True

    # ##################
    # Every day, we go through all states and run a duplication check so we end up with a list of Politicians
    #  that might be duplicates. Every time this script runs, we check one more state.
    results = full_deduplication_for_next_state()
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "
        all_states_deduplication_complete = results['all_states_deduplication_complete']

    # ##################
    # After all states have been checked once per day for duplicates, we check to see if there have been any
    #  manual deduplication in any states. If so, run the full_deduplication_for_next_state again for that state
    #  the next time batch_process_deduplication_scripts_politician is run.
    if all_states_deduplication_complete:
        results = find_states_that_need_new_politician_deduplication()
        if positive_value_exists(results['success']):
            state_code_list = results['state_code_list']
            if state_code_list and len(state_code_list) > 0:
                # Update the DeduplicationNeededForStateToday entry for today with the
                # states that need to be deduplicated again.
                try:
                    pacific_tz = pytz.timezone('US/Pacific')
                    date_now = now().astimezone(pacific_tz)
                    date_now_as_integer = convert_date_to_date_as_integer(date_now)
                    deduplication_needed_for_state_today, created = \
                        DeduplicationNeededForStateToday.objects.get_or_create(
                            date_now_as_integer=date_now_as_integer,
                        )
                    # Set the deduplication_needed flag to True for each state in the list
                    for state_code in state_code_list:
                        field_name = f"{state_code.lower()}_deduplication_needed"
                        setattr(deduplication_needed_for_state_today, field_name, True)

                    deduplication_needed_for_state_today.save()
                    status += f"UPDATED_DeduplicationNeededForStateToday for states: {', '.join(state_code_list)} "
                except Exception as e:
                    status += "FAILED_TO_UPDATE_DeduplicationNeededForStateToday: {e} ".format(e=e)
                    success = False
        if positive_value_exists(results['status']):
            status += results['status'] + " :||: "

    results = {
        'status': status,
        'success': success,
    }
    return results


def batch_process_maintenance_scripts_politician():
    status = ':||: '
    success = True

    # ##################
    # Make sure we have a version of the politician's name without a middle initial (for matching endorsements)
    results = generate_google_civic_name_alternates(
        number_to_generate=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Generate a unique background color for each politician so their photo has a rectangle to sit in
    results = generate_politician_photo_backgrounds(
        number_to_generate=50,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Create seo_friendly_path for all politicians who currently don't have one
    results = generate_politician_seo_friendly_paths(
        number_to_create=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Check all entries that have Politician.linked_campaignx_we_vote_id and
    # make sure we have that corresponding CampaignX entry. If not, delete the Politician.linked_campaignx_we_vote_id
    # value.
    results = delete_linked_campaignx_we_vote_id_if_campaignx_not_found(
        number_to_verify=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Create default CampaignX for all politicians who currently don't have one
    results = generate_campaignx_for_every_politician(
        number_to_create=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Find all politicians with linked_campaignx_we_vote_id and make sure Campaignx
    # entry includes linked_politician_we_vote_id. If it doesn't, or linked_politician_we_vote_id in CampaignX entry
    # doesn't match the Politician.we_vote_id, update it.
    results = update_campaignx_with_linked_politician_we_vote_id(
        number_to_update=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    results = {
        'status': status,
        'success': success,
    }
    return results


def delete_linked_campaignx_we_vote_id_if_campaignx_not_found(
        number_to_verify=1000,
        state_code=None,
):
    """
    Check all entries that have Politician.linked_campaignx_we_vote_id and
    make sure we have that corresponding CampaignX entry. If not, delete the Politician.linked_campaignx_we_vote_id
    value.
    """
    records_cleared = 0
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_made = 0
    updates_needed = False

    try:
        politician_query = Politician.objects.all()
        politician_query = politician_query.exclude(
            Q(linked_campaignx_we_vote_id__isnull=True) |
            Q(linked_campaignx_we_vote_id="")
        )
        politician_query = politician_query.filter(linked_campaignx_we_vote_id_verified=False)
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        linked_campaignx_we_vote_id_list = \
            politician_query.values_list('linked_campaignx_we_vote_id', flat=True).distinct()
        linked_campaignx_we_vote_id_list = list(linked_campaignx_we_vote_id_list[:number_to_verify])

        # Find existing CampaignX entries expected from the Politician.linked_campaignx_we_vote_id values
        from campaign.models import CampaignX
        existing_campaignx_we_vote_ids = set(CampaignX.objects.filter(
            we_vote_id__in=linked_campaignx_we_vote_id_list
        ).values_list('we_vote_id', flat=True))

        # Create a list of linked_campaignx_we_vote_ids that don't exist in CampaignX
        non_existent_campaignx_we_vote_ids = [
            we_vote_id for we_vote_id in linked_campaignx_we_vote_id_list
            if we_vote_id not in existing_campaignx_we_vote_ids
        ]

        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_verify if total_to_convert > number_to_verify else 0
        datetime_now = generate_localized_datetime_from_obj()[1]
        if existing_campaignx_we_vote_ids and len(existing_campaignx_we_vote_ids) > 0:
            politician_unchanged_query = Politician.objects.filter(
                linked_campaignx_we_vote_id__in=existing_campaignx_we_vote_ids
            )
            politician_unchanged_list = list(politician_unchanged_query)
            for politician in politician_unchanged_list:
                politician.linked_campaignx_we_vote_id_date_last_updated = datetime_now
                politician.linked_campaignx_we_vote_id_verified = True
                update_list.append(politician)
                updates_needed = True
                updates_made += 1
        if non_existent_campaignx_we_vote_ids and len(non_existent_campaignx_we_vote_ids) > 0:
            politician_clear_query = Politician.objects.filter(
                linked_campaignx_we_vote_id__in=non_existent_campaignx_we_vote_ids
            )
            politician_list_to_clear = list(politician_clear_query)
            for politician in politician_list_to_clear:
                politician.linked_campaignx_we_vote_id = None
                politician.linked_campaignx_we_vote_id_date_last_updated = datetime_now
                politician.linked_campaignx_we_vote_id_verified = True
                update_list.append(politician)
                updates_needed = True
                updates_made += 1
                records_cleared += 1
    except Exception as e:
        status += "ERROR_POLITICIAN_QUERY_delete_linked_campaignx_we_vote_id_if_campaignx_not_found query: {e} " \
                  "".format(e=e)
        success = False

    if updates_needed:
        try:
            Politician.objects.bulk_update(
                update_list, [
                    'linked_campaignx_we_vote_id',
                    'linked_campaignx_we_vote_id_date_last_updated',
                    'linked_campaignx_we_vote_id_verified'])
            status += \
                "delete_linked_campaignx_we_vote_id_if_campaignx_not_found: " \
                "{updates_made:,} politicians scanned for a current linked_campaignx_we_vote_id. " \
                "{records_cleared:,} records had Politician.linked_campaignx_we_vote_id cleared out. " \
                "{total_to_convert_after:,} remaining. " \
                "".format(
                    records_cleared=records_cleared,
                    total_to_convert_after=total_to_convert_after,
                    updates_made=updates_made)
        except Exception as e:
            status += "ERROR_POLITICIAN_BULK_UPDATE_delete_linked_campaignx_we_vote_id_if_campaignx_not_found: {e} " \
                "".format(e=e)
            success = False
    else:
        status += \
            "delete_linked_campaignx_we_vote_id_if_campaignx_not_found: " \
            "{total_to_convert_after:,} remaining. " \
            "".format(
                total_to_convert_after=total_to_convert_after)

    results = {
        'status': status,
        'success': success,
    }
    return results


def politician_deduplication_for_one_state(state_code=''):
    status = ''
    success = True

    if not positive_value_exists(state_code):
        status += "STATE_CODE_IS_REQUIRED: "
        success = False
        return {
            'status': status,
            'success': success,
        }

    # Delete all existing duplicates
    try:
        queryset = PoliticiansArePossibleDuplicates.objects.filter(
            state_code__iexact=state_code,
        )
        number_deleted, unused = queryset.delete()
        status += f"[Deleted {number_deleted:,} PoliticiansArePossibleDuplicates entries for state {state_code}] "
    except Exception as e:
        status += "ERROR_DELETING_POSSIBLE_DUPLICATES: {e} ".format(e=e)
        success = False

    if success:
        merge_results = find_and_merge_duplicate_politicians(state_code=state_code)
        status += merge_results['status']
        if merge_results['politicians_merged_found']:
            politicians_merged_list = merge_results['politicians_merged_list']
            for politician in politicians_merged_list:
                status += f"[Politician {politician.politician_name} merged.] "
        if merge_results['duplicate_check_complete_politician_we_vote_id_list']:
            try:
                we_vote_ids_to_update = merge_results['duplicate_check_complete_politician_we_vote_id_list']
                if len(we_vote_ids_to_update) > 0:
                    Politician.objects.filter(we_vote_id__in=we_vote_ids_to_update)\
                        .update(duplicate_check_last_completed=now())
                    status += f"DUPLICATE_CHECK_COMPLETE_FOR-{len(we_vote_ids_to_update)}-POLITICIANS "
            except Exception as e:
                status += f"COULD_NOT_UPDATE_DUPLICATE_CHECK_LAST_COMPLETED: {e} "
        if merge_results['reset_duplicate_check_last_completed_we_vote_id_list']:
            try:
                we_vote_ids_to_update = merge_results['reset_duplicate_check_last_completed_we_vote_id_list']
                if len(we_vote_ids_to_update) > 0:
                    Politician.objects.filter(we_vote_id__in=we_vote_ids_to_update)\
                        .update(duplicate_check_last_completed=None)
                    status += f"RESET_DUPLICATE_CHECK_FOR-{len(we_vote_ids_to_update)}-POLITICIANS "
            except Exception as e:
                status += f"COULD_NOT_RESET_DUPLICATE_CHECK_LAST_COMPLETED: {e} "

    results = {
        'status': status,
        'success': success,
    }
    return results


def find_and_merge_duplicate_politicians(state_code=''):
    duplicate_check_complete_politician_we_vote_id_list = []
    politician_manager = PoliticianManager()
    politicians_merged_found = False
    politicians_merged_list = []
    reset_duplicate_check_last_completed_we_vote_id_list = []
    status = ""
    success = True
    error_results = {
        "duplicate_check_complete_politician_we_vote_id_list": [],
        "politicians_merged_found": politicians_merged_found,
        "politicians_merged_list": politicians_merged_list,
        "reset_duplicate_check_last_completed_we_vote_id_list": reset_duplicate_check_last_completed_we_vote_id_list,
        "status": status,
        "success": False,
    }
    # ################################
    # Assemble a list of politicians that we already think might be duplicates
    try:
        queryset = PoliticiansArePossibleDuplicates.objects.using('readonly').all()
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        queryset = queryset.exclude(politician1_we_vote_id=None)
        queryset = queryset.exclude(politician2_we_vote_id=None)
        queryset_politician1 = queryset.values_list('politician1_we_vote_id', flat=True).distinct()
        exclude_politician1_we_vote_id_list = list(queryset_politician1)
        queryset_politician2 = queryset.values_list('politician2_we_vote_id', flat=True).distinct()
        exclude_politician2_we_vote_id_list = list(queryset_politician2)
        exclude_politician_we_vote_id_list = \
            list(set(exclude_politician1_we_vote_id_list + exclude_politician2_we_vote_id_list))
    except Exception as e:
        status += f"COULD_NOT_RETRIEVE_POSSIBLE_DUPLICATES: {str(e)} "
        error_results['status'] = status
        return error_results

    # ################################
    # Retrieve list of politicians to compare
    try:
        politician_query = Politician.objects.using('readonly').all()
        if exclude_politician_we_vote_id_list and len(exclude_politician_we_vote_id_list) > 0:
            politician_query = politician_query.exclude(we_vote_id__in=exclude_politician_we_vote_id_list)
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        politician_list = list(politician_query)
    except Exception as e:
        status += f"COULD_NOT_RETRIEVE_POLITICIANS: {str(e)} "
        error_results['status'] = status
        return error_results

    # ################################
    # Loop through all the politicians in this state
    try:
        for we_vote_politician in politician_list:
            if we_vote_politician.we_vote_id in exclude_politician_we_vote_id_list:
                continue
            # Start ignore list with entries already reviewed
            ignore_politician_id_list = exclude_politician_we_vote_id_list.copy()
            # Add current entry to ignore list
            ignore_politician_id_list.append(we_vote_politician.we_vote_id)
            # Now check for others we have already labeled as "not a duplicate" of this particular politician
            duplicates_results = \
                politician_manager.retrieve_politicians_are_not_duplicates_list(we_vote_politician.we_vote_id)
            if duplicates_results['success']:
                not_a_duplicate_list = duplicates_results['politicians_are_not_duplicates_list_we_vote_ids']
                # Add current entry to ignore list
                ignore_politician_id_list += not_a_duplicate_list
            else:
                status += f"COULD_NOT_RETRIEVE_POLITICIANS_ARE_NOT_DUPLICATES: {duplicates_results['status']} "

            results = find_duplicate_politician(we_vote_politician, ignore_politician_id_list, read_only=True)

            # If we find politicians to merge, store them for review
            if results['politician_merge_possibility_found']:
                politician_option1_for_template = we_vote_politician
                politician_option2_for_template = results['politician_merge_possibility']

                # Can we automatically merge these politicians?
                merge_results = merge_if_duplicate_politicians(
                    politician_option1_for_template,
                    politician_option2_for_template,
                    results['politician_merge_conflict_values'])

                if merge_results['politicians_merged']:
                    politician = merge_results['politician']
                    if politician.we_vote_id not in exclude_politician_we_vote_id_list:
                        exclude_politician_we_vote_id_list.append(politician.we_vote_id)
                    if we_vote_politician.we_vote_id not in exclude_politician_we_vote_id_list:
                        exclude_politician_we_vote_id_list.append(we_vote_politician.we_vote_id)
                    PoliticiansArePossibleDuplicates.objects.create(
                        politician1_we_vote_id=politician.we_vote_id,
                        politician2_we_vote_id=None,
                        state_code=state_code,
                    )
                    PoliticiansArePossibleDuplicates.objects.create(
                        politician1_we_vote_id=we_vote_politician.we_vote_id,
                        politician2_we_vote_id=None,
                        state_code=state_code,
                    )
                    politicians_merged_list.append(politician)
                    politicians_merged_found = True
                    if politician.we_vote_id not in reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(politician.we_vote_id)
                else:
                    # Add an entry showing that this is a possible match
                    status += (
                        f"[Politician {we_vote_politician.politician_name} "
                        f"({we_vote_politician.we_vote_id}) has possible match.] "
                    )
                    PoliticiansArePossibleDuplicates.objects.create(
                        politician1_we_vote_id=we_vote_politician.we_vote_id,
                        politician2_we_vote_id=politician_option2_for_template.we_vote_id,
                        state_code=state_code,
                    )
                    if politician_option2_for_template.we_vote_id not in exclude_politician_we_vote_id_list:
                        exclude_politician_we_vote_id_list.append(politician_option2_for_template.we_vote_id)
                    if we_vote_politician.we_vote_id not in reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(we_vote_politician.we_vote_id)
                    if politician_option2_for_template.we_vote_id not in \
                            reset_duplicate_check_last_completed_we_vote_id_list:
                        reset_duplicate_check_last_completed_we_vote_id_list.append(
                            politician_option2_for_template.we_vote_id)
            else:
                # No matches found
                PoliticiansArePossibleDuplicates.objects.create(
                    politician1_we_vote_id=we_vote_politician.we_vote_id,
                    politician2_we_vote_id=None,
                    state_code=state_code,
                )
                if we_vote_politician.we_vote_id not in duplicate_check_complete_politician_we_vote_id_list:
                    duplicate_check_complete_politician_we_vote_id_list.append(we_vote_politician.we_vote_id)
    except Exception as e:
        status += f"CRASHED_IN_POLITICIAN_LIST_LOOP: {str(e)} "
        # Fall through to exit function

    return {
        "duplicate_check_complete_politician_we_vote_id_list": duplicate_check_complete_politician_we_vote_id_list,
        "politicians_merged_found": politicians_merged_found,
        "politicians_merged_list": politicians_merged_list,
        "reset_duplicate_check_last_completed_we_vote_id_list": reset_duplicate_check_last_completed_we_vote_id_list,
        "status": status,
        "success": success,
    }


def find_states_that_need_new_politician_deduplication():
    """
    Check to see if there are any states with that have new politicians that haven't been checked for duplicates
    """
    state_codes_for_deduplication = [
        "ak", "al", "ar", "az", "ca", "co", "ct", "dc", "de", "fl", "ga", "hi", "ia", "id", "il", "in", "ks",
        "ky", "la", "ma", "md", "me", "mi", "mn", "mo", "ms", "mt", "na", "nc", "nd", "ne", "nh", "nj", "nm",
        "nv", "ny", "oh", "ok", "or", "pa", "pr", "ri", "sc", "sd", "tn", "tx", "ut", "va", "vt", "wa", "wi",
        "wv", "wy"
    ]
    state_code_list = []
    status = ''
    success = True

    # Return all politicians from any state in state_codes_for_deduplication
    #  that have a null duplicate_check_last_completed value
    # We want to identify new politicians that haven't been deduplicated yet
    politician_query = Politician.objects.using('readonly').filter(
        state_code__in=state_codes_for_deduplication,
        duplicate_check_last_completed__isnull=True,
    )
    # Extract a list of politician we_vote_id values from the politician_query organized by state_code
    politician_list = list(politician_query)
    politicians_by_state_code = {}
    for politician in politician_list:
        if politician.state_code not in politicians_by_state_code:
            politicians_by_state_code[politician.state_code] = []
        politicians_by_state_code[politician.state_code].append(politician.we_vote_id)

    # Now cycle through each state in state_codes_for_deduplication and make sure
    # that none of the we_vote_id values in politicians_by_state_code appear in PoliticiansArePossibleDuplicates
    for state_code in politicians_by_state_code:
        politician_we_vote_id_list = politicians_by_state_code[state_code]
        politician_we_vote_id_remaining_list = politician_we_vote_id_list.copy()
        politician_duplicate_check_query = PoliticiansArePossibleDuplicates.objects.using('readonly').filter(
            (
                Q(politician1_we_vote_id__in=politician_we_vote_id_list) &
                Q(politician2_we_vote_id__isnull=False)
            ) | (
                Q(politician2_we_vote_id__in=politician_we_vote_id_list) &
                Q(politician1_we_vote_id__isnull=False)
            )
        )
        politician_duplicate_check_list = list(politician_duplicate_check_query)
        # Cycle through politician_duplicate_check_list and remove one-by-one the values in politician_we_vote_id_list.
        #  If there are values left, then we can run the deduplication process for the state again
        for politician_duplicate_check in politician_duplicate_check_list:
            if politician_duplicate_check.politician1_we_vote_id in politician_we_vote_id_remaining_list:
                politician_we_vote_id_remaining_list.remove(politician_duplicate_check.politician1_we_vote_id)
            if politician_duplicate_check.politician2_we_vote_id in politician_we_vote_id_remaining_list:
                politician_we_vote_id_remaining_list.remove(politician_duplicate_check.politician2_we_vote_id)

        if len(politician_we_vote_id_remaining_list) > 0:
            # We need to run the deduplication process for this state again
            state_code_list.append(state_code)

    return {
        "state_code_list": state_code_list,
        "status": status,
        "success": success,
    }


def generate_campaignx_for_every_politician(
        number_to_create=1000,
        state_code=None,
):
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_made = 0
    updates_needed = False

    try:
        politician_query = Politician.objects.all()
        politician_query = politician_query.filter(
            Q(linked_campaignx_we_vote_id__isnull=True) |
            Q(linked_campaignx_we_vote_id="")
        )
        politician_query = politician_query.exclude(
            Q(seo_friendly_path__isnull=True) |
            Q(seo_friendly_path="")
        )
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_create if total_to_convert > number_to_create else 0
        politician_list_to_convert = list(politician_query[:number_to_create])
        datetime_now = generate_localized_datetime_from_obj()[1]
        for one_politician in politician_list_to_convert:
            results = generate_campaignx_for_politician(
                datetime_now=datetime_now,
                politician=one_politician,
                save_individual_politician=False,
            )
            if results['success'] and results['campaignx_created']:
                one_politician = results['politician']
                update_list.append(one_politician)
                updates_needed = True
                updates_made += 1
    except Exception as e:
        status += "ERROR_POLITICIAN_QUERY_generate_campaignx_for_every_politician query: {e} ".format(e=e)
        success = False

    if updates_needed:
        try:
            Politician.objects.bulk_update(
                update_list, ['linked_campaignx_we_vote_id', 'linked_campaignx_we_vote_id_date_last_updated'])
            status += \
                "generate_campaignx_for_every_politician Generated CampaignX for {updates_made:,} politicians. " \
                "{total_to_convert_after:,} remaining. " \
                "".format(
                    total_to_convert_after=total_to_convert_after,
                    updates_made=updates_made)
        except Exception as e:
            status += "ERROR_POLITICIAN_BULK_UPDATE_generate_campaignx_for_every_politician: {e} ".format(e=e)
            success = False
    else:
        status += "NO_UPDATES_NEEDED_generate_campaignx_for_every_politician "

    results = {
        'status': status,
        'success': success,
    }
    return results


def generate_politician_photo_backgrounds(
        number_to_generate=10,
        state_code=None,
):
    politicians_not_updated = 0
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_made = 0
    updates_needed = False

    try:
        politician_query = Politician.objects.all()
        politician_query = politician_query.exclude(
            Q(we_vote_hosted_profile_image_url_large__isnull=True) |
            Q(we_vote_hosted_profile_image_url_large="")
        )
        politician_query = politician_query.exclude(profile_image_background_color_needed=False)
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_generate if total_to_convert > number_to_generate else 0
        politician_list_to_convert = list(politician_query[:number_to_generate])

        for politician in politician_list_to_convert:
            politician.profile_image_background_color_needed = False
            if positive_value_exists(politician.we_vote_hosted_profile_image_url_large):
                politician.profile_image_background_color = generate_background(politician)
                updates_made += 1
                update_list.append(politician)
                updates_needed = True
            else:
                politicians_not_updated += 1
        if total_to_convert == 0:
            status += "All politicians have been updated with a background color for profile photo."
    except Exception as e:
        status += "ERROR_POLITICIAN_QUERY-generate_politician_photo_backgrounds: {e} ".format(e=e)
        success = False

    if updates_needed:
        try:
            Politician.objects.bulk_update(update_list, ['profile_image_background_color',
                                                         'profile_image_background_color_needed'])
            status += \
                "generate_politician_photo_backgrounds: {updates_made:,} updates made. " \
                "Politicians without picture URL:  {politicians_not_updated:,}. " \
                "{total_to_convert_after:,} remaining. " \
                "".format(
                    politicians_not_updated=politicians_not_updated,
                    total_to_convert_after=total_to_convert_after,
                    updates_made=updates_made)
        except Exception as e:
            status += "ERROR_POLITICIAN_BULK_UPDATE-generate_politician_photo_backgrounds: {e} ".format(e=e)
            success = False
    else:
        status += "NO_UPDATES_NEEDED_generate_politician_photo_backgrounds "
    results = {
        'status': status,
        'success': success,
    }
    return results


def generate_politician_seo_friendly_paths(
        number_to_create=1000,
        state_code=None,
):
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_made = 0
    updates_needed = False

    try:
        politician_query = Politician.objects.all()
        politician_query = politician_query.filter(
            Q(seo_friendly_path__isnull=True) |
            Q(seo_friendly_path="")
        )
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_create if total_to_convert > number_to_create else 0
        politician_list_to_convert = list(politician_query[:number_to_create])
        politician_manager = PoliticianManager()
        datetime_now = generate_localized_datetime_from_obj()[1]
        for one_politician in politician_list_to_convert:
            results = politician_manager.generate_seo_friendly_path(
                politician_name=one_politician.politician_name,
                politician_we_vote_id=one_politician.we_vote_id,
                state_code=one_politician.state_code,
            )
            if results['seo_friendly_path_found']:
                one_politician.seo_friendly_path = results['seo_friendly_path']
                one_politician.seo_friendly_path_date_last_updated = datetime_now
                update_list.append(one_politician)
                updates_needed = True
                updates_made += 1
    except Exception as e:
        status += "ERROR_POLITICIAN_QUERY-generate_politician_seo_friendly_paths query: {e} ".format(e=e)
        success = False

    if updates_needed:
        try:
            Politician.objects.bulk_update(update_list,
                                           ['seo_friendly_path', 'seo_friendly_path_date_last_updated'])
            status += \
                "generate_politician_seo_friendly_paths: " \
                "{updates_made:,} politicians updated with new seo_friendly_path. " \
                "{total_to_convert_after:,} remaining. " \
                "".format(
                    total_to_convert_after=total_to_convert_after,
                    updates_made=updates_made)
        except Exception as e:
            status += "ERROR_POLITICIAN_BULK_UPDATE-generate_politician_seo_friendly_paths: {e} ".format(e=e)
            success = False
    else:
        status += "NO_UPDATES_NEEDED_generate_politician_seo_friendly_paths "

    results = {
        'status': status,
        'success': success,
    }
    return results


def generate_google_civic_name_alternates(
        number_to_generate=1000,
        state_code=None,
):
    """
    Make sure we have a version of the politician's name without a middle initial (for matching endorsements)
    """
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_failed = 0
    updates_made = 0
    updates_needed = False

    try:
        politician_query = Politician.objects.all()
        politician_query = politician_query.filter(google_civic_name_alternates_generated=False)
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_generate if total_to_convert > number_to_generate else 0
        politician_list_to_convert = list(politician_query[:number_to_generate])
        for one_politician in politician_list_to_convert:
            results = add_alternate_names_to_next_spot(
                politician=one_politician,
            )
            if results['values_changed']:
                politician = results['politician']
                politician.google_civic_name_alternates_generated = True
                update_list.append(politician)
                updates_needed = True
                updates_made += 1
            elif results['success']:
                one_politician.google_civic_name_alternates_generated = True
                update_list.append(one_politician)
                updates_needed = True
            else:
                updates_failed += 1
    except Exception as e:
        status += "ERROR_POLITICIAN_QUERY generate_google_civic_name_alternates query: {e} ".format(e=e)
        success = False

    if updates_needed:
        try:
            Politician.objects.bulk_update(update_list, [
                'google_civic_name_alternates_generated',
                'google_civic_candidate_name',
                'google_civic_candidate_name2',
                'google_civic_candidate_name3',
            ])
            status += \
                "{updates_made:,} google_civic_name_alternates_generated. " \
                "{total_to_convert_after:,} remaining. " \
                "".format(
                    total_to_convert_after=total_to_convert_after,
                    updates_made=updates_made)
        except Exception as e:
            status += "ERROR_POLITICIAN_BULK_UPDATE generate_google_civic_name_alternates: {e} ".format(e=e)
            success = False
    else:
        status += "NO_UPDATES_NEEDED_generate_google_civic_name_alternates "
    results = {
        'status': status,
        'success': success,
    }
    return results


def update_campaignx_with_linked_politician_we_vote_id(
        number_to_update=1000,
        state_code=None,
):
    """
    Find all politicians with linked_campaignx_we_vote_id and make sure Campaignx
    entry includes linked_politician_we_vote_id. If it doesn't, or linked_politician_we_vote_id in CampaignX entry
    doesn't match the Politician.we_vote_id, update it.
    """
    politician_update_list = []
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_made = 0
    updates_needed = False
    from campaign.models import CampaignX

    try:
        politician_query = Politician.objects.all()
        politician_query = politician_query.exclude(
            Q(linked_campaignx_we_vote_id__isnull=True) |
            Q(linked_campaignx_we_vote_id="")
        )
        politician_query = politician_query.filter(linked_campaignx_we_vote_id_verified_in_campaignx=False)
        if positive_value_exists(state_code):
            politician_query = politician_query.filter(state_code__iexact=state_code)
        total_to_convert = politician_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        politician_list_to_convert = list(politician_query[:number_to_update])
        campaignx_we_vote_id_list = []
        politician_dict_by_campaign_we_vote_id = {}
        politicians_with_linked_campaignx_we_vote_id_count = 0
        for one_politician in politician_list_to_convert:
            if positive_value_exists(one_politician.linked_campaignx_we_vote_id):
                politicians_with_linked_campaignx_we_vote_id_count += 1
                if one_politician.linked_campaignx_we_vote_id not in campaignx_we_vote_id_list:
                    campaignx_we_vote_id_list.append(one_politician.linked_campaignx_we_vote_id)
                    politician_dict_by_campaign_we_vote_id[one_politician.linked_campaignx_we_vote_id] = one_politician

        campaignx_query = CampaignX.objects.all()
        campaignx_query = campaignx_query.filter(we_vote_id__in=campaignx_we_vote_id_list)
        campaignx_list = list(campaignx_query)
        campaignx_with_linked_politician_we_vote_id_count = 0
        for one_campaignx in campaignx_list:
            if one_campaignx.we_vote_id in politician_dict_by_campaign_we_vote_id:
                one_politician = politician_dict_by_campaign_we_vote_id[one_campaignx.we_vote_id]
                if hasattr(one_politician, 'we_vote_id') and positive_value_exists(one_politician.we_vote_id):
                    if one_campaignx.linked_politician_we_vote_id != one_politician.we_vote_id:
                        one_campaignx.linked_politician_we_vote_id = one_politician.we_vote_id
                        update_list.append(one_campaignx)
                        updates_made += 1

                        one_politician.linked_campaignx_we_vote_id_verified_in_campaignx = True
                        politician_update_list.append(one_politician)

                        updates_needed = True

            if positive_value_exists(one_campaignx.linked_politician_we_vote_id):
                campaignx_with_linked_politician_we_vote_id_count += 1
    except Exception as e:
        status += "ERROR_POLITICIAN_QUERY_update_campaignx_with_linked_politician_we_vote_id: {e} ".format(e=e)
        success = False

    if updates_needed:
        try:
            CampaignX.objects.bulk_update(
                update_list, ['linked_politician_we_vote_id'])
            status += \
                "update_campaignx_with_linked_politician_we_vote_id: " \
                "{updates_made:,} politicians updated with new linked_campaignx_we_vote_id. " \
                "{total_to_convert_after:,} remaining. " \
                "".format(
                    total_to_convert_after=total_to_convert_after,
                    updates_made=updates_made)
        except Exception as e:
            status += "ERROR_CAMPAIGNX_BULK_UPDATE_update_campaignx_with_linked_politician_we_vote_id: {e} " \
                      "".format(e=e)
            success = False

        # Mark the politicians as verified
        try:
            Politician.objects.bulk_update(
                politician_update_list, ['linked_campaignx_we_vote_id_verified_in_campaignx'])
            status += \
                "{updates_made:,} updates of linked_campaignx_we_vote_id_verified_in_campaignx. " \
                "".format(
                    updates_made=updates_made)
        except Exception as e:
            status += "ERROR_POLITICIAN_BULK_UPDATE_update_campaignx_with_linked_politician_we_vote_id: {e} " \
                      "".format(e=e)
            success = False
    else:
        status += "NO_UPDATES_NEEDED_update_campaignx_with_linked_politician_we_vote_id "

    results = {
        'status': status,
        'success': success,
    }
    return results
