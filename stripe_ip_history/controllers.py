# stripe_ip_history/controllers.py
# Brought to you by We Vote. Be good.

# -*- coding: UTF-8 -*-
import json

from django.http import HttpResponse

from stripe_ip_history.models import StripeIpHistoryManager
from wevote_functions.admin import get_logger

logger = get_logger(__name__)

# with these constant settings, one IP can load /more/donate 5 times in 60 minutes, or no more than 30 times in a week
MAX_NUMBER_OF_STRIPE_FORM_RENDERS_MINUTES = 5
NUMBER_OF_MINUTES_RANGE = 60
MAX_NUMBER_OF_STRIPE_FORM_RENDERS_DAYS = 30
NUMBER_OF_HOURS_RANGE = 24*7    # a week


def check_for_excessive_stripe_access(ip_address, country_code, voter_we_vote_id, email, captcha_score, captcha_success,
                                      blocked_by_captcha, blocked_by_country):
    blocked_by_frequency_hours = False
    blocked_by_frequency_days = False
    count_results = StripeIpHistoryManager.count_stripe_ip_records_for_ip(ip_address, NUMBER_OF_MINUTES_RANGE,
                                                                          NUMBER_OF_HOURS_RANGE)
    status = count_results['status']
    if count_results['success']:
        if count_results['minutes_match_count'] > MAX_NUMBER_OF_STRIPE_FORM_RENDERS_MINUTES:
            blocked_by_frequency_hours = True
        if count_results['days_match_count'] > MAX_NUMBER_OF_STRIPE_FORM_RENDERS_DAYS:
            blocked_by_frequency_days = True

        record_status = StripeIpHistoryManager.create_ip_history_record(
            ip_address, country_code, voter_we_vote_id, email, captcha_score, captcha_success, blocked_by_captcha,
            blocked_by_country, blocked_by_frequency_hours, blocked_by_frequency_days)

        status += record_status['status']

    results = {
        'success':                      True,
        'status':                       status,
        'blocked_by_frequency_hours':   blocked_by_frequency_hours,
        'blocked_by_frequency_days':    blocked_by_frequency_days,
    }

    return results


def stripe_ip_history_clear_for_one_ip_for_api(ip_address):  # ipHistoryClearForOneIp

    results = StripeIpHistoryManager.clear_ip_history_records_for_one_ip(ip_address)

    json_data = {
        'success': results['success'],
        'status': results['status'],
        'records_cleared': results['records_cleared'],
        'ip_address': ip_address,
    }

    return HttpResponse(json.dumps(json_data), content_type='application/json')
