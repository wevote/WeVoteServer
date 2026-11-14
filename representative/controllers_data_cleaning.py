# representative/controllers_data_cleaning.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db.models import Q
from django.utils.timezone import localtime, now
from config.environment_variable_functions import get_environment_variable

from wevote_functions.functions_date import get_current_year_as_integer
from office_held.models import OfficeHeld
from politician.models import PoliticianManager
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from wevote_functions.functions_date import generate_localized_datetime_from_obj
from .models import Representative

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def batch_process_maintenance_scripts_representative():
    status = ' :||: '
    success = True

    # ##################
    # Update representatives who currently don't have seo_friendly_path, if there is seo_friendly_path
    #  in linked politician
    results = seo_friendly_path_updates(
        number_to_update=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Update representatives who currently don't have a locally cached office_held_district_name
    results = update_representatives_with_office_held_district_name(
        number_to_update=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Update representatives who currently don't have a campaignx_we_vote_id, with value from linked politician
    results = update_representatives_with_campaignx_we_vote_id(
        number_to_update=1000,
    )
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    # ##################
    # Update the representative record from the linked politician record
    results = update_representative_from_politician_batch_process()
    if positive_value_exists(results['status']):
        status += results['status'] + " :||: "

    results = {
        'status': status,
        'success': success,
    }
    return results


def seo_friendly_path_updates(
        number_to_update=1000,
        state_code=None,
):
    representative_list = []
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_needed = False
    updates_made = 0

    # Now get all representatives we want to update, with a single query
    try:
        queryset = Representative.objects.all()
        queryset = queryset.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id="")
        )
        queryset = queryset.filter(
            Q(seo_friendly_path__isnull=True) |
            Q(seo_friendly_path="")
        )
        if positive_value_exists(state_code):
            queryset = queryset.filter(state_code__iexact=state_code)
        # After initial updates to all representatives, include in the search logic to find representatives with
        # seo_friendly_path_date_last_updated older than Politician.seo_friendly_path_date_last_updated
        total_to_convert = queryset.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        representative_list = list(queryset[:number_to_update])
    except Exception as e:
        status += "FAILED_RETRIEVING_REPRESENTATIVES_FOR_SEO_FRIENDLY_PATH: " + str(e) + " "

    # Retrieve all relevant politicians in a single query
    politician_we_vote_id_list = []
    for one_representative in representative_list:
        politician_we_vote_id_list.append(one_representative.politician_we_vote_id)
    politician_manager = PoliticianManager()
    politician_list = []
    if politician_we_vote_id_list and len(politician_we_vote_id_list) > 0:
        politician_results = politician_manager.retrieve_politician_list(
            politician_we_vote_id_list=politician_we_vote_id_list)
        politician_list = politician_results['politician_list']
    politician_dict_list = {}
    for one_politician in politician_list:
        politician_dict_list[one_politician.we_vote_id] = one_politician

    datetime_now = generate_localized_datetime_from_obj()[1]
    for one_representative in representative_list:
        one_politician = politician_dict_list.get(one_representative.politician_we_vote_id)
        if one_politician and positive_value_exists(one_politician.seo_friendly_path):
            one_representative.seo_friendly_path = one_politician.seo_friendly_path
            one_representative.seo_friendly_path_date_last_updated = datetime_now
            update_list.append(one_representative)
            updates_needed = True
            updates_made += 1

    if updates_needed:
        try:
            Representative.objects.bulk_update(
                update_list, ['seo_friendly_path', 'seo_friendly_path_date_last_updated'])
            status += \
                "{updates_made:,} representatives updated with new seo_friendly_path. " \
                "{total_to_convert_after:,} remaining." \
                "".format(total_to_convert_after=total_to_convert_after, updates_made=updates_made)
        except Exception as e:
            status += "FAILED_MAKING_REPRESENTATIVE_SEO_FRIENDLY_PATH_UPDATES: " + str(e) + " "
            success = False
    else:
        status += "NO_SEO_FRIENDLY_PATH_UPDATES_NEEDED "

    if positive_value_exists(status):
        status += "(SEO_UPDATE_SCRIPT) "

    results = {
        'status': status,
        'success': success,
    }
    return results


def update_representative_from_politician_batch_process():
    representative_list = []
    current_year = get_current_year_as_integer()
    politician_dict_list = {}
    status = ""
    success = True

    try:
        queryset = Representative.objects.all()
        if positive_value_exists(current_year):
            year_in_office_key = 'year_in_office_' + str(current_year)
            one_year_filter = Q(**{year_in_office_key: True})
            queryset = queryset.filter(one_year_filter)
        queryset = queryset.filter(updated_from_politician_completed=None)
        queryset = queryset.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id='')
        )
        queryset = queryset[:500]  # Limit to 500 to throttle this process
        representative_list = list(queryset)
    except Exception as e:
        status += "FAILED_RETRIEVING_REPRESENTATIVES_FOR_UPDATE_FROM_POLITICIAN: " + str(e) + " "

    if representative_list and len(representative_list) > 0:
        politician_we_vote_id_list = [
            representative.politician_we_vote_id for representative in representative_list
            if representative.politician_we_vote_id
        ]
        status += "UPDATE_REPRESENTATIVE_FROM_POLITICIAN "
        status += "REPRESENTATIVES_FOUND-" + str(len(representative_list)) + " "
        status += "POLITICIAN_WE_VOTE_IDS_FOUND-" + str(len(politician_we_vote_id_list)) + " "
    else:
        status += "UPDATE_REPRESENTATIVE_FROM_POLITICIAN_NONE_FOUND "
        return {
            'status':                   status,
            'success':                  success,
        }

    try:
        from politician.models import Politician
        queryset = Politician.objects.using('readonly').filter(we_vote_id__in=politician_we_vote_id_list)
        politician_list = list(queryset)
        politician_dict_list = {}
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician
    except Exception as e:
        status += "FAILED_RETRIEVING_POLITICIANS: " + str(e) + " "
        success = False

    all_representative_fields_updated = []
    representative_bulk_update_list = []
    representatives_updated_count = 0
    representatives_not_updated_count = 0
    representative_update_problem_count = 0
    from representative.controllers import update_representative_details_from_politician
    for one_representative in representative_list:
        politician = politician_dict_list.get(one_representative.politician_we_vote_id)
        if politician:
            results = update_representative_details_from_politician(
                politician=politician, representative=one_representative)
            if results['success']:
                save_changes = results['save_changes']
                changed_representative = results['representative']
                changed_representative.updated_from_politician_completed = localtime(now()).date()
                if 'updated_from_politician_completed' not in all_representative_fields_updated:
                    all_representative_fields_updated.append('updated_from_politician_completed')
                if save_changes:
                    changed_representative.date_last_updated = localtime(now()).date()
                    if 'date_last_updated' not in all_representative_fields_updated:
                        all_representative_fields_updated.append('date_last_updated')
                    representatives_updated_count += 1
                    fields_updated = results['fields_updated']
                    for field in fields_updated:
                        if field not in all_representative_fields_updated:
                            all_representative_fields_updated.append(field)
                else:
                    representatives_not_updated_count += 1
                representative_bulk_update_list.append(changed_representative)
            else:
                representative_update_problem_count += 1
                representatives_not_updated_count += 1
                if representative_update_problem_count <= 5:
                    status += results['status']
        else:
            status += f"POLITICIAN_NOT_FOUND_IN_DB-{one_representative.politician_we_vote_id} "
            representatives_not_updated_count += 1

    if len(representative_bulk_update_list) > 0:
        try:
            Representative.objects.bulk_update(representative_bulk_update_list, all_representative_fields_updated)
            status += \
                "[[REPRESENTATIVES_UPDATED: {representatives_updated_count:,} " \
                "NOT_UPDATED: {representatives_not_updated_count:,}]] \n" \
                "".format(
                    representatives_not_updated_count=representatives_not_updated_count,
                    representatives_updated_count=representatives_updated_count,
                )
        except Exception as e:
            status += "FAILED_BULK_UPDATE_OF_REPRESENTATIVES: " + str(e) + " "

    return {
        'status':                   status,
        'success':                  success,
    }


def update_representatives_with_campaignx_we_vote_id(
        number_to_update=1000,
        state_code=None,
):
    politician_list = []
    politician_we_vote_id_list = []
    representative_list = []
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_made = 0
    updates_needed = False

    # Now get all representatives that need CampaignX augmentation
    try:
        campaignx_update_query = Representative.objects.all()
        campaignx_update_query = campaignx_update_query.exclude(
            Q(politician_we_vote_id__isnull=True) |
            Q(politician_we_vote_id="")
        )
        campaignx_update_query = campaignx_update_query.filter(
            Q(linked_campaignx_we_vote_id__isnull=True) |
            Q(linked_campaignx_we_vote_id="")
        )
        if positive_value_exists(state_code):
            campaignx_update_query = campaignx_update_query.filter(state_code__iexact=state_code)
        # After initial updates to all representatives, include in the search logic to find representatives with
        # linked_campaignx_we_vote_id_date_last_updated older than
        # Politician.linked_campaignx_we_vote_id_date_last_updated
        total_to_convert = campaignx_update_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        campaignx_update_query = campaignx_update_query.order_by('-id')
        representative_list = list(campaignx_update_query[:number_to_update])
        for one_representative in representative_list:
            if positive_value_exists(one_representative.politician_we_vote_id):
                politician_we_vote_id_list.append(one_representative.politician_we_vote_id)
    except Exception as e:
        status += "FAILED_RETRIEVING_REPRESENTATIVES_FOR_CAMPAIGNX_AUGMENTATION: " + str(e) + " "

    politician_dict_list = {}
    if politician_we_vote_id_list and len(politician_we_vote_id_list) > 0:
        politician_manager = PoliticianManager()
        if len(politician_we_vote_id_list) > 0:
            politician_results = politician_manager.retrieve_politician_list(
                politician_we_vote_id_list=politician_we_vote_id_list)
            politician_list = politician_results['politician_list']
        for one_politician in politician_list:
            politician_dict_list[one_politician.we_vote_id] = one_politician

        datetime_now = generate_localized_datetime_from_obj()[1]
        linked_campaignx_we_vote_id_missing = 0

        try:
            for one_representative in representative_list:
                one_politician = politician_dict_list.get(one_representative.politician_we_vote_id)
                if not hasattr(one_politician, 'linked_campaignx_we_vote_id'):
                    continue
                if positive_value_exists(one_politician.linked_campaignx_we_vote_id):
                    one_representative.linked_campaignx_we_vote_id = one_politician.linked_campaignx_we_vote_id
                    one_representative.linked_campaignx_we_vote_id_date_last_updated = datetime_now
                    update_list.append(one_representative)
                    updates_needed = True
                    updates_made += 1
                else:
                    linked_campaignx_we_vote_id_missing += 1
        except Exception as e:
            status += "FAILED_MATCHING_REPRESENTATIVES_WITH_POLITICIAN_DATA: " + str(e) + " "

        if positive_value_exists(linked_campaignx_we_vote_id_missing):
            status += "{linked_campaignx_we_vote_id_missing:,} missing linked_campaignx_we_vote_id." \
                      "".format(linked_campaignx_we_vote_id_missing=linked_campaignx_we_vote_id_missing)

    if updates_needed:
        try:
            Representative.objects.bulk_update(
                update_list, ['linked_campaignx_we_vote_id', 'linked_campaignx_we_vote_id_date_last_updated'])
            status += \
                "{updates_made:,} representatives updated with new linked_campaignx_we_vote_id. " \
                "{total_to_convert_after:,} remaining." \
                "".format(total_to_convert_after=total_to_convert_after, updates_made=updates_made)
        except Exception as e:
            status += "FAILED_MAKING_REPRESENTATIVE_CAMPAIGNX_UPDATES: " + str(e) + " "
            success = False
    else:
        status += "NO_CAMPAIGNX_UPDATES_NEEDED "

    if positive_value_exists(status):
        status += "(CAMPAIGNX_UPDATES) "

    results = {
        'status': status,
        'success': success,
    }
    return results


def update_representatives_with_office_held_district_name(
        number_to_update=1000,
        state_code=None,
):
    office_held_we_vote_id_list = []
    status = ''
    success = True
    total_to_convert_after = 0
    update_list = []
    updates_made = 0
    updates_needed = False

    # Now get all representatives that need office_held augmentation
    try:
        cache_query = Representative.objects.all()
        cache_query = cache_query.exclude(
            Q(office_held_we_vote_id__isnull=True) |
            Q(office_held_we_vote_id="")
        )
        cache_query = cache_query.filter(
            Q(office_held_district_name__isnull=True) |
            Q(office_held_district_name="")
        )
        if positive_value_exists(state_code):
            cache_query = cache_query.filter(state_code__iexact=state_code)
        cache_query = cache_query.values_list('office_held_we_vote_id', flat=True).distinct()
        total_to_convert = cache_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        office_held_we_vote_id_list = cache_query[:number_to_update]
    except Exception as e:
        status += "FAILED_RETRIEVING_REPRESENTATIVES_TO_FIND_OFFICE_HELD_ENTRIES: " + str(e) + " "

    office_held_dict_list = {}
    if len(office_held_we_vote_id_list) > 0:
        try:
            # Retrieve all relevant OfficeHeld data in a single query so we can use the data to update representatives
            office_held_queryset = OfficeHeld.objects.all()
            office_held_queryset = office_held_queryset.filter(we_vote_id__in=office_held_we_vote_id_list)
            office_held_list = list(office_held_queryset)
            for office_held in office_held_list:
                if office_held.we_vote_id not in office_held_dict_list:
                    office_held_dict_list[office_held.we_vote_id] = office_held
        except Exception as e:
            status += "FAILED_RETRIEVING_OFFICE_HELD_DATA_FOR_REPRESENTATIVE_AUGMENTING: " + str(e) + " "

        try:
            # Retrieve list of representatives to update based on office_held_we_vote_id_list
            cache_query2 = Representative.objects.all()
            cache_query2 = cache_query2.filter(office_held_we_vote_id__in=office_held_we_vote_id_list)
            cache_query2 = cache_query2.filter(
                Q(office_held_district_name__isnull=True) |
                Q(office_held_district_name="")
            )
            representative_list_to_update = list(cache_query2)
            for representative in representative_list_to_update:
                one_office_held = office_held_dict_list.get(representative.office_held_we_vote_id)
                if positive_value_exists(one_office_held.district_name):
                    representative.office_held_district_name = one_office_held.district_name
                    update_list.append(representative)
                    updates_needed = True
                    updates_made += 1
        except Exception as e:
            status += "FAILED_RETRIEVING_REPRESENTATIVES_FOR_OFFICE_HELD_AUGMENTING: " + str(e) + " "

    if updates_needed:
        try:
            Representative.objects.bulk_update(
                update_list, ['office_held_district_name'])
            status += \
                "{updates_made:,} representatives updated with new district_name. " \
                "{total_to_convert_after:,} remaining." \
                "".format(total_to_convert_after=total_to_convert_after, updates_made=updates_made)
        except Exception as e:
            status += "FAILED_MAKING_REPRESENTATIVE_OFFICE_HELD_DISTRICT_NAME_UPDATES: " + str(e) + " "
            success = False
    else:
        status += "NO_OFFICE_HELD_DISTRICT_NAME_UPDATES_NEEDED "

    if positive_value_exists(status):
        status += "(OFFICE_HELD_DISTRICT_NAME) "

    results = {
        'status': status,
        'success': success,
    }
    return results
