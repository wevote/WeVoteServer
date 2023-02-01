# stripe_ip_history/views_donation.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import re
import json

from django.http import HttpResponse

from stripe_ip_history.controllers import stripe_ip_history_clear_for_one_ip_for_api


def stripe_ip_history_clear_for_one_ip(request):  # ipHistoryClearForOneIp
    ip_address = request.GET.get('ip_address', '')
    match = re.match(r"[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}", ip_address)
    if not bool(match):
        json_data = {
            'success': False,
            'status': 'INVALID_IP_ADDRESS_RECEIVED',
            'records_count': 0,
            'ip_address': ip_address,
        }
        http_response = HttpResponse(json.dumps(json_data), content_type='application/json')

    else:
        http_response = stripe_ip_history_clear_for_one_ip_for_api(ip_address)
    return http_response
