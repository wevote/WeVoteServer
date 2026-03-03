# email_outbound/controllers_audience_builder_preview.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable

from django.db.models import Q
from django.template.loader import render_to_string


from election.models import Election
from email_outbound.functions import convert_html_to_plain_text
from email_outbound.models import AudienceBuilder, AudienceFilter, AudienceFilterChain
from organization.controllers import transform_web_app_url
from politician.models import Politician
from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP
from wevote_functions.functions_date import get_current_year_as_integer
from .models import CUSTOMIZATION_TOKEN_CONVERSION_FROM_JAZZ_HR, \
    EmailCampaign, EmailCampaignRecipient, EmailManager, EmailScheduled, \
    EMAIL_TEMPLATE_CUSTOMIZATION_TOKENS, TO_BE_PROCESSED

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def generate_preview_list_from_politician_list(politician_list=[]):
    preview_list = []
    status = ""
    success = True

    for politician in politician_list:
        preview_dict = {
            'name': politician.politician_name if hasattr(politician, 'politician_name') else '',
            'politician_we_vote_id': politician.we_vote_id if hasattr(politician, 'we_vote_id') else '',
            'phone': politician.politician_phone_number if hasattr(politician, 'politician_phone_number') else '',
            'email': politician.politician_email if hasattr(politician, 'politician_email') else '',
            'email_we_vote_id': '',  # Politician model doesn't have this field
            'type': 'POLITICIAN',
            'state_code': politician.state_code if hasattr(politician, 'state_code') else '',
        }
        preview_list.append(preview_dict)

    if len(preview_list) > 0:
        status += f'PREVIEW_LIST_GENERATED: {len(preview_list)} politicians '
    else:
        status += 'NO_POLITICIANS_IN_LIST '

    return {
        'preview_list': preview_list,
        'status':       status,
        'success':      success,
    }


def generate_preview_list_from_audience_builder(audience_builder_id=0):
    preview_list = []
    preview_list_length = 0
    status = ""
    success = True

    try:
        queryset = Politician.objects.all()
        preview_list_length = queryset.count()
        queryset = queryset.order_by('-date_last_updated')[:100]
        politician_list = list(queryset)
    except Exception as e:
        status += f'PROBLEM_RETRIEVING_POLITICIANS: {e}'
        return {
            'preview_list': preview_list,
            'preview_list_length': preview_list_length,
            'status':       status,
            'success':      False,
        }

    results = generate_preview_list_from_politician_list(politician_list=politician_list)
    preview_list = results['preview_list']

    return {
        'preview_list': preview_list,
        'preview_list_length': preview_list_length,
        'status':       status,
        'success':      success,
    }


def render_audience_builder_preview_html(
        audience_builder={},
        audience_filter_chain_dict={},
        audience_filter_dict={},
        request=None):
    audience_builder_preview_html = ''
    audience_filter_html_dict = {}
    chain_operand_to_follow_dict = {}
    filter_operand_to_follow_dict = {}
    status = ''
    success = True

    results = generate_preview_list_from_audience_builder(audience_builder_id=audience_builder.id)
    preview_list = results['preview_list']
    preview_list_length = results['preview_list_length']

    context = {
        'audience_builder_id': audience_builder.id,
        'preview_list': preview_list,
        'preview_list_length': preview_list_length,
    }
    audience_builder_preview_html = render_to_string(
        "email_outbound/audience_builder_preview_list.html",
        context, request=request)

    return {
        'audience_builder_preview_html': audience_builder_preview_html,
        'status': status,
        'success': success,
    }
