# email_outbound/controllers_audience_builder.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable

from django.db.models import Q
from django.db.models.functions import Length
from django.template.loader import render_to_string


from candidate.models import CandidateListManager
from politician.models import Politician
import itertools
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP
from .models import AudienceBuilder, AudienceFilter, AudienceFilterChain, EmailCampaign, EmailCampaignRecipient

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def audience_builder_data_retrieve(audience_builder_id):
    audience_builder = {}
    audience_filter_chain_dict = {}
    audience_filter_dict = {}
    audience_filter_list = []
    status = ''
    success = True

    if not positive_value_exists(audience_builder_id):
        status += "AUDIENCE_BUILDER_ID_REQUIRED "
        success = True
        return {
            'audience_builder': audience_builder,
            'audience_filter_chain_dict': audience_filter_chain_dict,
            'audience_filter_dict': audience_filter_dict,
            'audience_filter_list': audience_filter_list,
            'status': status,
            'success': success,
        }

    try:
        audience_builder = AudienceBuilder.objects.get(id=audience_builder_id)
    except Exception as e:
        status += f"ERROR_RETRIEVING_AUDIENCE_BUILDER: {e} "
        success = False

    if success:
        try:
            queryset = AudienceFilter.objects.filter(audience_builder_id=audience_builder_id)
            audience_filter_list = list(queryset)
            for audience_filter in audience_filter_list:
                audience_filter_dict[audience_filter.id] = audience_filter
        except Exception as e:
            status += f"ERROR_RETRIEVING_AUDIENCE_FILTER: {e} "
            success = False

    if success:
        try:
            queryset = AudienceFilterChain.objects.filter(audience_builder_id=audience_builder_id)
            audience_filter_chain_list = list(queryset)
            for audience_filter_chain in audience_filter_chain_list:
                audience_filter_chain_dict[audience_filter_chain.id] = audience_filter_chain
        except Exception as e:
            status += f"ERROR_RETRIEVING_AUDIENCE_FILTER_CHAIN: {e} "
            success = False

    return {
        'audience_builder':             audience_builder,
        'audience_filter_chain_dict':   audience_filter_chain_dict,
        'audience_filter_dict':         audience_filter_dict,
        'audience_filter_list':         audience_filter_list,
        'status':                       status,
        'success':                      success,
    }


def generate_email_campaign_recipients_from_audience_builder(audience_builder_id=0, email_campaign_id=''):
    """
    Use this function to create email_campaign_recipients in preparation for sending emails.

    :param audience_builder_id: ID of the audience builder
    :param email_campaign_id: ID of the email campaign to generate recipients for
    """
    preview_list = []
    status = ""
    success = True

    try:
        email_campaign = EmailCampaign.objects.get(id=email_campaign_id)
    except EmailCampaign.DoesNotExist:
        status += "EMAIL_CAMPAIGN_NOT_FOUND_GENERATE_RECIPIENTS "
        return {
            'status':   status,
            'success':  False,
        }
    except Exception as e:
        status += f'GENERATE_RECIPIENTS_PROBLEM_RETRIEVING_EMAIL_CAMPAIGN: {e}'
        return {
            'status':   status,
            'success':  False,
        }

    # Get the email body & subject templates for this campaign
    # TODO: Is this necessary for generating recipients?
    try:
        email_body_template = email_campaign.email_body_template_raw
        email_subject_template = email_campaign.email_subject_template_raw
    except Exception as e:
        status += f'PROBLEM_RETRIEVING_EMAIL_TEMPLATE_RAW: {e}'
        return {
            'status':   status,
            'success':  False,
        }

    # Get all specific recipients for this email campaign, prior to adding recipients formulaically
    try:
        queryset = EmailCampaignRecipient.objects.filter(
            email_campaign_id=email_campaign_id)
        # It turns out we don't want to exclude the EmailCampaignRecipient objects that have already been scheduled yet,
        #  so we can know to not add them from the AudienceBuilder searches.
        # # Filter out recipient entries that have already been sent
        # queryset = queryset.exclude(email_campaign_recipient_id__in=already_scheduled_recipient_ids)
        email_campaign_recipient_list = list(queryset)
    except Exception as e:
        status += f'Problem retrieving email campaign recipients. {e}'
        return {
            'status': status,
            'success': False,
        }

    if not positive_value_exists(audience_builder_id):
        status += "AUDIENCE_BUILDER_ID_REQUIRED "
        return {
            'status': status,
            'success': False,
        }

    results = audience_builder_data_retrieve(audience_builder_id)
    status += results['status']
    if results['success']:
        audience_builder = results['audience_builder']
        audience_builder_name = audience_builder.audience_builder_name
        audience_filter_chain_dict = results['audience_filter_chain_dict']
        audience_filter_dict = results['audience_filter_dict']
    else:
        audience_builder_id = None
        success = False
        return {
            'status': status,
            'success': False,
        }

    results = generate_preview_list_from_audience_builder(
        audience_builder=audience_builder,
        audience_filter_dict=audience_filter_dict)
    status += results['status']
    if results['success']:
        preview_list = results['preview_list']
        # preview_dict = {
        #     'name': politician.politician_name if hasattr(politician, 'politician_name') else '',
        #     'politician_we_vote_id': politician.we_vote_id if hasattr(politician, 'we_vote_id') else '',
        #     'phone': politician.politician_phone_number if hasattr(politician, 'politician_phone_number') else '',
        #     'email': politician.politician_email if hasattr(politician, 'politician_email') else '',
        #     'email_we_vote_id': '',  # Politician model doesn't have this field
        #     'type': 'POLITICIAN',
        #     'state_code': politician.state_code if hasattr(politician, 'state_code') else '',
        # }

    for one_preview in preview_list:
        pass

    return {
        'status': status,
        'success': success,
    }


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


def generate_preview_list_from_audience_builder(
        audience_builder={},
        audience_filter_chain_dict={},
        audience_filter_dict={},
        request=None):
    all_candidates_dict = {}  # Key is candidate_we_vote_id, value is a candidate object
    all_politicians_dict = {}  # Key is politician_we_vote_id, value is a politician object

    preview_list = []
    preview_list_length = 0
    status = ""
    success = True

    # Probably want to call this routine independently for each audience_filter_chain
    results = assemble_basic_dictionaries_from_audience_filters(audience_filter_dict)
    status += results['status']
    election_modifier_dict = results['election_modifier_dict']
    email_address_modifier_dict = results['email_address_modifier_dict']
    # Loop through email_address_modifier_dict and if any of the values equal 'EMAIL_ADDRESS_EXISTS',
    #  then set only_include_entries_with_email_address to True
    only_include_entries_with_email_address = False
    for email_address_modifier in email_address_modifier_dict.values():
        if email_address_modifier == 'EMAIL_ADDRESS_EXISTS':
            only_include_entries_with_email_address = True
            break

    google_civic_election_id_dict = results['google_civic_election_id_dict']
    # google_civic_election_id_expanded_dict is a dictionary of all the election_ids based on the election_modifier
    #  ("is on", "is before", "is on or after", etc.). So google_civic_election_id_dict is just the reference
    #  election, where google_civic_election_id_expanded_dict is all the elections based on google_civic_election_id
    #  and beyond.
    google_civic_election_id_expanded_dict = results['google_civic_election_id_expanded_dict']

    # Pull the election ids from the dictionary values into a simple list for now.
    # 1. Chain all the lists together into a single iterable
    chained_values = itertools.chain.from_iterable(google_civic_election_id_expanded_dict.values())
    # 2. Convert the chained values to a set to remove duplicates
    unique_values_set = set(chained_values)
    # 3. (Optional) Convert the set back to a list if order does not matter
    # Note: Sets do not preserve the original order.
    google_civic_election_id_list = list(unique_values_set)

    # Retrieve candidates and politicians from the database based on google_civic_election_id_dict
    # This routine will be called per audience_filter_chain
    results = retrieve_db_objects_for_audience_filter_chain(
        google_civic_election_id_list=google_civic_election_id_list,
        only_include_entries_with_email_address=only_include_entries_with_email_address,
    )
    politician_list = results['politician_list']
    politician_list_length = results['politician_list_length']
    # all_candidates_dict = results['all_candidates_dict']
    # all_politicians_dict = results['all_politicians_dict']
    # candidate_ids_by_audience_filter_dict = results['candidate_ids_by_audience_filter_dict']
    # politician_ids_by_audience_filter_dict = results['politician_ids_by_audience_filter_dict']

    # We will need to pay attention to which rules come in under a single filter chain
    # For now, we treat all filters as if they are all part of the same filter chain

    results = generate_preview_list_from_politician_list(politician_list=politician_list)
    preview_list = results['preview_list']

    return {
        'preview_list': preview_list,
        'preview_list_length': politician_list_length,
        'status':       status,
        'success':      success,
    }


def assemble_basic_dictionaries_from_audience_filters(audience_filter_dict):
    status = ''
    success = True

    # Cycle through all filters in audience_filter_dict and find entries with audience_filter_type
    #  equal to 'FILTER_TYPE_ELECTION_DATE', and return the google_civic_election_id and the election_modifier value.
    election_modifier_dict = {}  # Key is audience_filter_id, value is election_modifier
    email_address_modifier_dict = {}  # Key is audience_filter_id, value is email_address_modifier
    google_civic_election_id_dict = {}  # Key is audience_filter_id, value is google_civic_election_id
    # google_civic_election_id_expanded_dict is a dictionary of all the election_ids based on the election_modifier
    #  ("is on", "is before", "is on or after", etc.). So google_civic_election_id_dict is just the reference
    #  election, where google_civic_election_id_expanded_dict is all the elections based on google_civic_election_id
    #  and beyond.
    google_civic_election_id_expanded_dict = {}  # Key is audience_filter_id, value is list of google_civic_election_ids

    for filter_id, audience_filter in audience_filter_dict.items():
        if hasattr(audience_filter, 'audience_filter_type'):
            if audience_filter.audience_filter_type == 'FILTER_TYPE_ELECTION_DATE':
                if positive_value_exists(audience_filter.google_civic_election_id):
                    google_civic_election_id_dict[audience_filter.id] = audience_filter.google_civic_election_id

                    if positive_value_exists(audience_filter.election_modifier):
                        election_modifier_dict[audience_filter.id] = audience_filter.election_modifier
            if audience_filter.audience_filter_type == 'FILTER_TYPE_EMAIL_ADDRESS':
                if positive_value_exists(audience_filter.email_address_modifier):
                    email_address_modifier_dict[audience_filter.id] = audience_filter.email_address_modifier

    if len(google_civic_election_id_dict) > 0:
        status += f'FOUND_ELECTION_FILTERS: {len(google_civic_election_id_dict)} elections '

    # Retrieve google_civic_election_id_expanded_dict based on election_modifier_dict
    for audience_filter_id, election_modifier in election_modifier_dict.items():
        if audience_filter_id not in google_civic_election_id_expanded_dict:
            google_civic_election_id_expanded_dict[audience_filter_id] = []
        if positive_value_exists(election_modifier):
            if election_modifier == 'ELECTION_IS_ON':
                # We just want to send to the Politicians running for office in this one election
                if google_civic_election_id_dict[audience_filter_id] \
                        not in google_civic_election_id_expanded_dict[audience_filter_id]:
                    google_civic_election_id_expanded_dict[audience_filter_id].append(
                        google_civic_election_id_dict[audience_filter_id])
            elif election_modifier == 'ELECTION_IS_AFTER':
                # Get election_id expansion working for these:
                # ELECTION_IS_AFTER
                # ELECTION_IS_BEFORE
                # ELECTION_IS_ON_OR_AFTER
                # ELECTION_IS_ON_OR_BEFORE
                # We will need to do a search in the election database table to get elections before and after this one
                pass

    return {
        'election_modifier_dict': election_modifier_dict,
        'email_address_modifier_dict': email_address_modifier_dict,
        'google_civic_election_id_dict': google_civic_election_id_dict,
        'google_civic_election_id_expanded_dict': google_civic_election_id_expanded_dict,
        'status': status,
        'success': success,
    }


def retrieve_db_objects_for_audience_filter_chain(
        google_civic_election_id_list=[],
        only_include_entries_with_email_address=False):
    # candidate_dict = {}
    # politician_dict = {}
    politician_list = []
    politician_list_length = 0
    status = ''
    success = True

    candidate_list_manager = CandidateListManager()
    results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
        google_civic_election_id_list=google_civic_election_id_list,
    )
    candidate_we_vote_id_list = results['candidate_we_vote_id_list']

    results = candidate_list_manager.retrieve_politician_we_vote_id_list_from_candidate_we_vote_id_list(
        candidate_we_vote_id_list=candidate_we_vote_id_list)
    if results['politician_we_vote_id_list_found']:
        politician_we_vote_id_list = results['politician_we_vote_id_list']

        try:
            queryset = Politician.objects.all()
            queryset = queryset.filter(we_vote_id__in=politician_we_vote_id_list)
            if positive_value_exists(only_include_entries_with_email_address):
                queryset = queryset.annotate(politician_email_address_length=Length('politician_email_address'))
                queryset = queryset.annotate(politician_email_length=Length('politician_email'))
                queryset = queryset.annotate(politician_email2_length=Length('politician_email2'))
                queryset = queryset.annotate(politician_email3_length=Length('politician_email3'))
                queryset = queryset.filter(
                    Q(politician_email_address_length__gt=2) |
                    Q(politician_email_length__gt=2) |
                    Q(politician_email2_length__gt=2) |
                    Q(politician_email3_length__gt=2)
                )
            politician_list_length = queryset.count()
            queryset = queryset.order_by('-date_last_updated')[:100]
            politician_list = list(queryset)
        except Exception as e:
            status += f'PROBLEM_RETRIEVING_POLITICIANS: {e}'
            return {
                'politician_list':          politician_list,
                'politician_list_length':   politician_list_length,
                'status':       status,
                'success':      False,
            }

    return {
        'politician_list': politician_list,
        'politician_list_length': politician_list_length,
        'status': status,
        'success': success,
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

    results = generate_preview_list_from_audience_builder(
        audience_builder=audience_builder,
        audience_filter_chain_dict=audience_filter_chain_dict,
        audience_filter_dict=audience_filter_dict,
        request=request,
    )
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
