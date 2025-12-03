# import_export_batches/controllers_data_cleaning.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.utils.timezone import now
import pytz

from wevote_functions.functions import positive_value_exists
from wevote_functions.functions_date import convert_date_to_date_as_integer, get_current_year_as_integer


def full_deduplication_for_next_state(is_for_candidates=False):
    all_states_deduplication_complete = False
    date_now_as_integer = 0
    deduplication_needed = {}
    status = ''
    success = True
    next_state_code = None

    try:
        pacific_tz = pytz.timezone('US/Pacific')
        date_now = now().astimezone(pacific_tz)
        date_now_as_integer = convert_date_to_date_as_integer(date_now)
    except Exception as e:
        status += "DATE_NOW_COULD_NOT_BE_GENERATED: {e} ".format(e=e)
        success = False
    current_year = get_current_year_as_integer()

    try:
        if is_for_candidates:
            from candidate.models import DeduplicationNeededForStateToday
        else:
            from politician.models import DeduplicationNeededForStateToday
        deduplication_needed, created = DeduplicationNeededForStateToday.objects.get_or_create(
            date_now_as_integer=date_now_as_integer,
        )
        if created:
            status += "CREATED_DeduplicationNeededForStateToday: " + str(date_now_as_integer) + ' '
        else:
            status += "FOUND_DeduplicationNeededForStateToday " + str(date_now_as_integer) + ' '

        # Find the next state that needs deduplication
        fields = sorted([field.name for field in DeduplicationNeededForStateToday._meta.get_fields()
                         if field.name.endswith('_deduplication_needed')])
        for field_name in fields:
            if getattr(deduplication_needed, field_name):
                next_state_code = field_name.split('_')[0]
                break

        if next_state_code:
            status += f"NEXT_STATE_TO_DEDUPLICATE: {next_state_code} "
        else:
            status += "NO_STATES_LEFT_TO_DEDUPLICATE_TODAY "

    except Exception as e:
        status += "FAILED_TO_GET_OR_CREATE_DeduplicationNeededForStateToday: {e} ".format(e=e)
        success = False

    if next_state_code:
        if is_for_candidates:
            from candidate.controllers_data_cleaning import candidate_deduplication_for_one_state
            state_results = candidate_deduplication_for_one_state(
                candidate_year=current_year, state_code=next_state_code)
            status += state_results['status']
        else:
            from politician.controllers_data_cleaning import politician_deduplication_for_one_state
            state_results = politician_deduplication_for_one_state(state_code=next_state_code)
            status += state_results['status']
        if state_results['success']:
            try:
                setattr(deduplication_needed, f"{next_state_code}_deduplication_needed", False)
                deduplication_needed.save()
            except Exception as e:
                status += f"FAILED_TO_UPDATE_DeduplicationNeededForStateToday: {e} "
    else:
        # If here, we want to signal that it is time to check to see if any deduplication needs to started again
        all_states_deduplication_complete = True

    results = {
        'all_states_deduplication_complete': all_states_deduplication_complete,
        'status': status,
        'success': success,
    }
    return results
