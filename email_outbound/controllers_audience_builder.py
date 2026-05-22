# email_outbound/controllers_audience_builder.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable
from datetime import timedelta

from django.db.models import Q
from django.db.models.functions import Length
from django.template.loader import render_to_string
from django.utils import timezone


from candidate.models import CandidateListManager, CandidateCampaign
from politician.models import Politician
import itertools
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
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
        status += f"AUDIENCE_BUILDER_RETRIEVED: {audience_builder.audience_builder_name} "
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
            status += f"AUDIENCE_FILTER_CHAIN_RETRIEVED: {len(audience_filter_chain_list)} chains "
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


def augment_preview_list_with_candidate_info(
        campaignx_dict={},
        candidate_dict={},
        candidate_to_office_dict={},
        google_civic_election_id='',  # google_civic_election_id_list='',
        preview_list=[]):
    """
    :param campaignx_dict: Dictionary of campaignx data (key: politician_we_vote_id, value: CampaignX object)
    :param candidate_dict: Dictionary of candidate data (key: politician_we_vote_id, value: CandidateCampaign object)
    :param candidate_to_office_dict: Dictionary of candidate-to-office links
            (key1: candidate_we_vote_id, key2: google_civic_election_id, value: office_we_vote_id)
    :param google_civic_election_id: Google Civic Election ID
    :param preview_list: List of dictionaries representing preview items
    :return: Updated preview_list with candidate info
    """
    status = ""
    success = True

    # Augment with politician_passkey (campaignx.passkey_for_creating_campaign_owner)
    modified_preview_list = []
    for preview_dict in preview_list:
        if 'politician_we_vote_id' in preview_dict and positive_value_exists(preview_dict['politician_we_vote_id']):
            if preview_dict['politician_we_vote_id'] in campaignx_dict:
                campaignx = campaignx_dict[preview_dict['politician_we_vote_id']]
                if positive_value_exists(campaignx.passkey_for_creating_campaign_owner):
                    preview_dict['politician_passkey'] = campaignx.passkey_for_creating_campaign_owner
            if preview_dict['politician_we_vote_id'] in candidate_dict:
                candidate = candidate_dict[preview_dict['politician_we_vote_id']]
                if candidate and positive_value_exists(candidate.we_vote_id):
                    preview_dict['candidate_we_vote_id'] = candidate.we_vote_id
        modified_preview_list.append(preview_dict)
    preview_list = modified_preview_list

    # Augment with office_we_vote_id (from CandidateToOfficeLink)
    modified_preview_list = []
    for preview_dict in preview_list:
        if 'candidate_we_vote_id' in preview_dict and positive_value_exists(preview_dict['candidate_we_vote_id']):
            if preview_dict['candidate_we_vote_id'] in candidate_to_office_dict:
                election_to_office_options = candidate_to_office_dict[preview_dict['candidate_we_vote_id']]
                # If we want to pull candidates from multiple elections, how do we narrow down to one election here?
                # Not set up to deal with google_civic_election_id_list yet
                if google_civic_election_id in election_to_office_options \
                        and positive_value_exists(election_to_office_options[google_civic_election_id]):
                    preview_dict['office_we_vote_id'] = election_to_office_options[google_civic_election_id]
                else:
                    try:
                        # Use the last value in the election_to_office_options dictionary
                        preview_dict['office_we_vote_id'] = \
                            election_to_office_options[list(election_to_office_options.keys())[-1]]
                    except Exception as e:
                        status += f'GENERATE_RECIPIENTS_PROBLEM_RETRIEVING_OFFICE_WE_VOTE_ID: {e}'
        modified_preview_list.append(preview_dict)
    preview_list = modified_preview_list

    return {
        'preview_list': preview_list,
        'status':       status,
        'success':      success,
    }


def generate_email_campaign_recipients_from_audience_builder(audience_builder_id=0, email_campaign_id=''):
    """
    Use this function to create email_campaign_recipients in preparation for sending emails.

    :param audience_builder_id: ID of the audience builder
    :param email_campaign_id: ID of the email campaign to generate recipients for
    """
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
        status += f'GENERATE_RECIPIENTS_PROBLEM_RETRIEVING_EMAIL_CAMPAIGN: {e} '
        return {
            'status':   status,
            'success':  False,
        }

    # Get all specific recipients for this email campaign, prior to adding recipients formulaically
    prior_recipient_email_address_simple_list = []
    try:
        queryset = EmailCampaignRecipient.objects.filter(
            email_campaign_id=email_campaign_id)
        # It turns out we don't want to exclude the EmailCampaignRecipient objects that have already been scheduled yet,
        #  so we can know to not add them from the AudienceBuilder searches.
        # # Filter out recipient entries that have already been sent
        # queryset = queryset.exclude(email_campaign_recipient_id__in=already_scheduled_recipient_ids)
        email_campaign_recipient_list = list(queryset)
        # Loop through all recipient entries in email_campaign_recipient_list
        # and store the email_address value in prior_recipient_email_address_simple_list in lower case
        for email_campaign_recipient in email_campaign_recipient_list:
            prior_recipient_email_address_simple_list.append(email_campaign_recipient.email_address.lower())
        status += f'PRIOR_RECIPIENT_EMAIL_ADDRESS_SIMPLE_LIST: {prior_recipient_email_address_simple_list} '
    except Exception as e:
        status += f'PROBLEM_RETRIEVING_PRIOR_EMAIL_CAMPAIGN_RECIPIENTS: {e} '
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
        status += f'AUDIENCE_BUILDER_NAME: {audience_builder_name} '
    else:
        audience_builder_id = None
        status += "AUDIENCE_BUILDER_DATA_RETRIEVE_FAILED "
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
        recipients_to_create = []
        chunk_size = 1000
        total_created = 0

        for preview_dict in preview_list:
            # Make sure the recipient is not already saved as a EmailCampaignRecipient
            if 'email' in preview_dict and positive_value_exists(preview_dict['email']):
                email_address = preview_dict['email'].lower()
                if email_address in prior_recipient_email_address_simple_list:
                    # It means a EmailCampaignRecipient already exists for this email address
                    continue

            recipient_dict = {}
            if 'candidate_we_vote_id' in preview_dict and positive_value_exists(preview_dict['candidate_we_vote_id']):
                recipient_dict['candidate_we_vote_id'] = preview_dict['candidate_we_vote_id']
            if 'email' in preview_dict and positive_value_exists(preview_dict['email']):
                recipient_dict['email_address'] = preview_dict['email']
            recipient_dict['email_campaign_id'] = email_campaign_id
            if 'email_we_vote_id' in preview_dict and positive_value_exists(preview_dict['email_we_vote_id']):
                recipient_dict['recipient_email_we_vote_id'] = preview_dict['email_we_vote_id']
            if 'first_name' in preview_dict and positive_value_exists(preview_dict['first_name']):
                recipient_dict['politician_first_name'] = preview_dict['first_name']  # Is this correct for long run?
                recipient_dict['recipient_first_name'] = preview_dict['first_name']
            if 'full_name' in preview_dict and positive_value_exists(preview_dict['full_name']):
                recipient_dict['politician_full_name'] = preview_dict['full_name']  # Is this correct for long run?
                recipient_dict['recipient_full_name'] = preview_dict['full_name']
            if 'last_name' in preview_dict and positive_value_exists(preview_dict['last_name']):
                recipient_dict['politician_last_name'] = preview_dict['last_name']  # Is this correct for long run?
                recipient_dict['recipient_last_name'] = preview_dict['last_name']
            if 'office_we_vote_id' in preview_dict and positive_value_exists(preview_dict['office_we_vote_id']):
                recipient_dict['office_we_vote_id'] = preview_dict['office_we_vote_id']
            if 'political_party' in preview_dict and positive_value_exists(preview_dict['political_party']):
                recipient_dict['political_party'] = preview_dict['political_party']
            if 'politician_passkey' in preview_dict and positive_value_exists(preview_dict['politician_passkey']):
                recipient_dict['politician_passkey'] = preview_dict['politician_passkey']
            if 'politician_seo_friendly_path' in preview_dict \
                    and positive_value_exists(preview_dict['politician_seo_friendly_path']):
                recipient_dict['politician_seo_friendly_path'] = preview_dict['politician_seo_friendly_path']
            if 'politician_we_vote_id' in preview_dict and positive_value_exists(preview_dict['politician_we_vote_id']):
                recipient_dict['politician_we_vote_id'] = preview_dict['politician_we_vote_id']
            if 'state_code' in preview_dict and positive_value_exists(preview_dict['state_code']):
                recipient_dict['politician_state_code'] = preview_dict['state_code'].upper()
            try:
                # Create a new EmailCampaignRecipient object
                recipient_object = EmailCampaignRecipient(**recipient_dict)
                recipients_to_create.append(recipient_object)

                # When we reach chunk_size, bulk create and reset the list
                if len(recipients_to_create) >= chunk_size:
                    EmailCampaignRecipient.objects.bulk_create(
                        recipients_to_create,
                        ignore_conflicts=True  # Skip duplicates if any
                    )
                    total_created += len(recipients_to_create)
                    status += f"BULK_CREATED_RECIPIENTS: {len(recipients_to_create)} recipients. "
                    recipients_to_create = []  # Reset for next chunk

            except Exception as e:
                status += f"ERROR_PREPARING_RECIPIENT: {str(e)} "

        # Create any remaining recipients that didn't fill a complete chunk
        if len(recipients_to_create) > 0:
            try:
                EmailCampaignRecipient.objects.bulk_create(
                    recipients_to_create,
                    ignore_conflicts=True
                )
                total_created += len(recipients_to_create)
                status += f"BULK_CREATED_FINAL_RECIPIENTS: {len(recipients_to_create)} recipients. "
            except Exception as e:
                status += f"ERROR_BULK_CREATING_FINAL_CHUNK: {str(e)}. "

        status += f"TOTAL_RECIPIENTS_CREATED: {total_created}. "

    return {
        'status': status,
        'success': success,
    }


def generate_preview_list_from_politician_list(politician_list=[], max_list_length=0):
    preview_count = 0
    preview_list = []
    status = ""
    success = True

    for politician in politician_list:
        preview_count += 1
        state_code = politician.state_code if hasattr(politician, 'state_code') else ''
        state_code_upper = state_code.upper() if state_code else ''
        preview_dict = {
            'first_name': politician.first_name if hasattr(politician, 'first_name') else '',
            'full_name': politician.politician_name if hasattr(politician, 'politician_name') else '',
            'last_name': politician.last_name if hasattr(politician, 'last_name') else '',
            'political_party': politician.political_party if hasattr(politician, 'political_party') else '',
            'politician_seo_friendly_path': politician.seo_friendly_path
            if hasattr(politician, 'seo_friendly_path') else '',
            'politician_we_vote_id': politician.we_vote_id if hasattr(politician, 'we_vote_id') else '',
            'phone': politician.politician_phone_number if hasattr(politician, 'politician_phone_number') else '',
            'email': politician.politician_email if hasattr(politician, 'politician_email') else '',
            'email_we_vote_id': '',  # Politician model doesn't have this field
            'type': 'POLITICIAN',
            'state_code': state_code_upper,
        }
        if max_list_length > 0:
            if preview_count == max_list_length:
                status += "MAX_PREVIEW_LIST_LENGTH_REACHED: " + str(max_list_length) + " "
            if preview_count > max_list_length:
                break
        preview_list.append(preview_dict)
        # In addition to these values, we also add additional values from other data types,
        #  including office_we_vote_id, and politician_passkey

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
        max_list_length=0,
        request=None):
    only_include_politicians_sent_any_of_these_campaigns = []
    only_include_politicians_sent_all_of_these_campaigns = []
    only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns = []
    only_include_politicians_who_were_sent_none_of_these_campaigns = []

    status = ""
    success = True

    # Probably want to call this routine independently for each audience_filter_chain
    results = assemble_basic_dictionaries_from_audience_filters(audience_filter_dict)
    status += results['status']
    audience_type_is_politician = results['audience_type_is_politician']
    election_modifier_dict = results['election_modifier_dict']
    email_address_modifier_dict = results['email_address_modifier_dict']
    has_claimed_politician_modifier_dict = results['has_claimed_politician_modifier_dict']
    was_sent_campaign_list_dict = results['was_sent_campaign_list_dict']
    was_sent_campaign_modifier_dict = results['was_sent_campaign_modifier_dict']

    # FILTER_TYPE_EMAIL_ADDRESS
    # Loop through email_address_modifier_dict and if any of the values equal 'EMAIL_ADDRESS_EXISTS',
    #  then set only_include_entries_with_email_address to True
    only_include_entries_with_email_address = False
    for email_address_modifier in email_address_modifier_dict.values():
        if email_address_modifier == 'EMAIL_ADDRESS_EXISTS':
            only_include_entries_with_email_address = True
            break

    # FILTER_TYPE_HAS_CLAIMED_POLITICIAN
    do_not_include_is_claimed_politicians = False
    is_claimed_profile_date_time_window_length = None
    only_include_is_claimed_politicians = False
    for audience_filter_id, has_claimed_politician_modifier in has_claimed_politician_modifier_dict.items():
        if has_claimed_politician_modifier == 'HAS_CLAIMED_POLITICIAN_AT_LEAST_ONCE':
            only_include_is_claimed_politicians = True
        elif has_claimed_politician_modifier == 'HAS_CLAIMED_POLITICIAN_LAST_DAY':
            only_include_is_claimed_politicians = True
            is_claimed_profile_date_time_window_length = timedelta(days=1)
        elif has_claimed_politician_modifier == 'HAS_CLAIMED_POLITICIAN_LAST_3_DAYS':
            only_include_is_claimed_politicians = True
            is_claimed_profile_date_time_window_length = timedelta(days=3)
        elif has_claimed_politician_modifier == 'HAS_CLAIMED_POLITICIAN_LAST_WEEK':
            only_include_is_claimed_politicians = True
            is_claimed_profile_date_time_window_length = timedelta(weeks=1)
        elif has_claimed_politician_modifier == 'HAS_CLAIMED_POLITICIAN_LAST_MONTH':
            only_include_is_claimed_politicians = True
            is_claimed_profile_date_time_window_length = timedelta(days=30)
        elif has_claimed_politician_modifier == 'HAS_CLAIMED_POLITICIAN_LAST_YEAR':
            only_include_is_claimed_politicians = True
            is_claimed_profile_date_time_window_length = timedelta(days=365)
        elif has_claimed_politician_modifier == 'HAS_CLAIMED_POLITICIAN_NEVER':
            do_not_include_is_claimed_politicians = True

    # FILTER_TYPE_WAS_SENT_CAMPAIGN
    for audience_filter_id, was_sent_campaign_modifier in was_sent_campaign_modifier_dict.items():
        # WAS_SENT_CAMPAIGN_ANY = only_include_politicians_sent_any_of_these_campaigns
        # WAS_SENT_CAMPAIGN_ALL = only_include_politicians_sent_all_of_these_campaigns
        # WAS_NOT_SENT_CAMPAIGN_ANY = only_include_politicians_who_were_sent_none_of_these_campaigns
        # WAS_NOT_SENT_CAMPAIGN_AT_LEAST_ONE = \
        #     only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns

        # Get all the campaign_id values from the was_sent_campaign_list_dict
        was_sent_campaign_list = was_sent_campaign_list_dict[audience_filter_id]
        if was_sent_campaign_modifier == 'WAS_SENT_CAMPAIGN_ANY':
            # Only include politicians who were sent any of these email campaigns
            # We will remove any politicians that were sent to any of these campaigns
            only_include_politicians_sent_any_of_these_campaigns = was_sent_campaign_list
        elif was_sent_campaign_modifier == 'WAS_SENT_CAMPAIGN_ALL':
            # Only include politicians that were sent all these campaigns
            # We will remove any politicians that weren't sent all these campaigns
            only_include_politicians_sent_all_of_these_campaigns = was_sent_campaign_list
        elif was_sent_campaign_modifier == 'WAS_NOT_SENT_CAMPAIGN_ANY':
            # Only include politicians that were NOT sent any of these campaigns
            # We will remove any politicians that were sent to any of these campaigns
            only_include_politicians_who_were_sent_none_of_these_campaigns = was_sent_campaign_list
        elif was_sent_campaign_modifier == 'WAS_NOT_SENT_CAMPAIGN_AT_LEAST_ONE':
            # Only include politicians that weren't sent at least one of these campaigns
            # We will remove any politicians that were sent to any of these campaigns
            only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns = was_sent_campaign_list

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
    # TEMP: Just use one google_civic_election_id for now
    if positive_value_exists(len(google_civic_election_id_list)):
        google_civic_election_id = google_civic_election_id_list[0]
    else:
        google_civic_election_id = 0

    # Retrieve candidates and politicians from the database based on google_civic_election_id_dict
    # This routine will be called per audience_filter_chain
    results = retrieve_db_objects_for_audience_filter_chain(
        audience_type_is_politician=audience_type_is_politician,
        do_not_include_is_claimed_politicians=do_not_include_is_claimed_politicians,
        google_civic_election_id_list=google_civic_election_id_list,
        is_claimed_profile_date_time_window_length=is_claimed_profile_date_time_window_length,
        only_include_entries_with_email_address=only_include_entries_with_email_address,
        only_include_is_claimed_politicians=only_include_is_claimed_politicians,
        only_include_politicians_sent_any_of_these_campaigns=only_include_politicians_sent_any_of_these_campaigns,
        only_include_politicians_sent_all_of_these_campaigns=only_include_politicians_sent_all_of_these_campaigns,
        only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns=
        only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns,
        only_include_politicians_who_were_sent_none_of_these_campaigns=
        only_include_politicians_who_were_sent_none_of_these_campaigns,
    )
    campaignx_dict = results['campaignx_dict']
    candidate_dict = results['candidate_dict']
    candidate_to_office_dict = results['candidate_to_office_dict']
    politician_list = results['politician_list']
    politician_list_length = results['politician_list_length']
    # candidate_ids_by_audience_filter_dict = results['candidate_ids_by_audience_filter_dict']
    # politician_ids_by_audience_filter_dict = results['politician_ids_by_audience_filter_dict']
    status += results['status']

    # We will need to pay attention to which rules come in under a single filter chain
    # For now, we treat all filters as if they are all part of the same filter chain

    results = generate_preview_list_from_politician_list(
        politician_list=politician_list,
        max_list_length=max_list_length)
    preview_list = results['preview_list']
    status += results['status']

    results = augment_preview_list_with_candidate_info(
        campaignx_dict=campaignx_dict,
        candidate_dict=candidate_dict,
        candidate_to_office_dict=candidate_to_office_dict,
        google_civic_election_id=google_civic_election_id,  # Not set up to deal with an election list yet
        preview_list=preview_list)
    preview_list = results['preview_list']
    status += results['status']

    return {
        'preview_list': preview_list,
        'preview_list_length': politician_list_length,
        'status':       status,
        'success':      success,
    }


def assemble_basic_dictionaries_from_audience_filters(audience_filter_dict):
    status = ''
    success = True

    audience_type_is_politician = False
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
    has_claimed_politician_modifier_dict = {}  # Key is audience_filter_id, value is has_claimed_politician_modifier
    was_sent_campaign_list_dict = {}  # Key is audience_filter_id, value was_sent_campaign_list (a list of campaign ids)
    was_sent_campaign_modifier_dict = {}  # Key is audience_filter_id, value is was_sent_campaign_modifier

    for filter_id, audience_filter in audience_filter_dict.items():
        if hasattr(audience_filter, 'audience_filter_type'):
            if audience_filter.audience_filter_type == 'FILTER_TYPE_AUDIENCE_TYPE':
                # When we start working with multiple audience_filter_chains, we will need to treat this differently.
                if positive_value_exists(audience_filter.audience_type_politician):
                    audience_type_is_politician = True
            if audience_filter.audience_filter_type == 'FILTER_TYPE_ELECTION_DATE':
                if positive_value_exists(audience_filter.google_civic_election_id):
                    google_civic_election_id_dict[audience_filter.id] = audience_filter.google_civic_election_id
                    if positive_value_exists(audience_filter.election_modifier):
                        election_modifier_dict[audience_filter.id] = audience_filter.election_modifier
            if audience_filter.audience_filter_type == 'FILTER_TYPE_EMAIL_ADDRESS':
                if positive_value_exists(audience_filter.email_address_modifier):
                    email_address_modifier_dict[audience_filter.id] = audience_filter.email_address_modifier
            if audience_filter.audience_filter_type == 'FILTER_TYPE_HAS_CLAIMED_POLITICIAN':
                if positive_value_exists(audience_filter.has_claimed_politician_modifier):
                    has_claimed_politician_modifier_dict[audience_filter.id] = \
                        audience_filter.has_claimed_politician_modifier
            if audience_filter.audience_filter_type == 'FILTER_TYPE_WAS_SENT_CAMPAIGN':
                if positive_value_exists(audience_filter.was_sent_campaign_modifier):
                    # audience_filter.was_sent_campaign_list is a list of campaign ids formatted as
                    #  a comma-separated string.
                    was_sent_campaign_list_temp = audience_filter.was_sent_campaign_list.split(',')
                    was_sent_campaign_list_temp = [int(campaign_id) for campaign_id in was_sent_campaign_list_temp]
                    was_sent_campaign_list_dict[audience_filter.id] = was_sent_campaign_list_temp
                    was_sent_campaign_modifier_dict[audience_filter.id] = audience_filter.was_sent_campaign_modifier

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

    # We will need parallel dicts for candidates, voters, and organizations (re: audience_type_politician_dict)
    return {
        'audience_type_is_politician': audience_type_is_politician,
        'election_modifier_dict': election_modifier_dict,
        'email_address_modifier_dict': email_address_modifier_dict,
        'google_civic_election_id_dict': google_civic_election_id_dict,
        'google_civic_election_id_expanded_dict': google_civic_election_id_expanded_dict,
        'has_claimed_politician_modifier_dict': has_claimed_politician_modifier_dict,
        'status': status,
        'success': success,
        'was_sent_campaign_list_dict': was_sent_campaign_list_dict,
        'was_sent_campaign_modifier_dict': was_sent_campaign_modifier_dict,
    }


def retrieve_db_objects_for_audience_filter_chain(
        audience_type_is_politician=False,
        do_not_include_is_claimed_politicians=False,
        google_civic_election_id_list=[],
        is_claimed_profile_date_time_window_length=None,
        only_include_entries_with_email_address=False,
        only_include_is_claimed_politicians=False,
        only_include_politicians_sent_any_of_these_campaigns=[],
        only_include_politicians_sent_all_of_these_campaigns=[],
        only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns=[],
        only_include_politicians_who_were_sent_none_of_these_campaigns=[],
):
    campaignx_dict = {}
    candidate_dict = {}
    candidate_to_office_dict = {}
    candidate_we_vote_id_list = []
    politician_list = []
    politician_list_length = 0
    status = ''
    success = True
    error_results = {
        'campaignx_dict': campaignx_dict,
        'candidate_dict': candidate_dict,
        'candidate_to_office_dict': candidate_to_office_dict,
        'politician_list': politician_list,
        'politician_list_length': politician_list_length,
        'status': status,
        'success': success,
    }

    politician_we_vote_id_list_from_election_list = []
    are_politician_we_vote_ids_expected_from_election_list = False
    if len(google_civic_election_id_list) > 0:
        are_politician_we_vote_ids_expected_from_election_list = True
        candidate_list_manager = CandidateListManager()
        results = candidate_list_manager.retrieve_candidate_we_vote_id_list_from_election_list(
            google_civic_election_id_list=google_civic_election_id_list,
        )
        candidate_we_vote_id_list = results['candidate_we_vote_id_list']

        try:
            candidate_query = CandidateCampaign.objects.using('readonly').all()
            candidate_query = candidate_query.filter(we_vote_id__in=candidate_we_vote_id_list)
            candidate_query = candidate_query.exclude(
                Q(politician_we_vote_id__isnull=True) | Q(politician_we_vote_id="")
            )
            candidate_list = list(candidate_query)
            # Create a candidate_dictionary with politician_we_vote_id as key and candidate object as value
            candidate_dict = {candidate.politician_we_vote_id: candidate for candidate in candidate_list}

            candidate_query_limited = candidate_query.values_list('politician_we_vote_id', flat=True).distinct()
            politician_we_vote_id_list_from_election_list = list(candidate_query_limited)
        except Exception as e:
            success = False
            status += "COULD_NOT_RETRIEVE_POLITICIAN_LIST: " + str(e) + ' '

    # Now adjust the politician_we_vote_id_list based on "Was sent campaign(s)" filters
    # only_include_politicians_sent_any_of_these_campaigns = [],
    # only_include_politicians_sent_all_of_these_campaigns = [],
    # only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns = [],
    # only_include_politicians_who_were_sent_none_of_these_campaigns = [],

    # Create a list of all possible email campaign IDs pulled from all variables starting with "only_include_..."
    # NOTE: Originally retrieved to check to see if the EmailCampaign had all been sent.
    # all_possible_email_campaign_ids = set(only_include_politicians_sent_any_of_these_campaigns +
    #                                       only_include_politicians_sent_all_of_these_campaigns +
    #                                       only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns +
    #                                       only_include_politicians_who_were_sent_none_of_these_campaigns)
    # if len(all_possible_email_campaign_ids):
    #     try:
    #         queryset = EmailCampaign.objects.using('readonly').all()
    #         queryset = queryset.filter(id__in=all_possible_email_campaign_ids)
    #         email_campaign_list = list(queryset)
    #     except Exception as e:
    #         success = False
    #         status += "COULD_NOT_RETRIEVE_EMAIL_CAMPAIGN_LIST: " + str(e) + ' '

    # WAS_SENT_CAMPAIGN_ANY = only_include_politicians_sent_any_of_these_campaigns
    # WAS_SENT_CAMPAIGN_ALL = only_include_politicians_sent_all_of_these_campaigns
    # WAS_NOT_SENT_CAMPAIGN_ANY = only_include_politicians_who_were_sent_none_of_these_campaigns
    # WAS_NOT_SENT_CAMPAIGN_AT_LEAST_ONE = only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns

    are_politician_we_vote_ids_expected_from_any_campaigns = False
    politician_we_vote_id_list_sent_any_of_these_campaigns = []
    if positive_value_exists(len(only_include_politicians_sent_any_of_these_campaigns)):
        are_politician_we_vote_ids_expected_from_any_campaigns = True
        try:
            queryset = EmailCampaignRecipient.objects.using('readonly').all()
            queryset = queryset.filter(email_campaign_id__in=only_include_politicians_sent_any_of_these_campaigns)
            queryset = queryset.values_list('politician_we_vote_id', flat=True).distinct()
            politician_we_vote_id_list_sent_any_of_these_campaigns = list(queryset)
        except Exception as e:
            success = False
            status += "COULD_NOT_RETRIEVE_RECIPIENTS__WAS_SENT_CAMPAIGN_ANY: " + str(e) + ' '

    are_politician_we_vote_ids_expected_from_all_campaigns = False
    politician_we_vote_id_list_sent_all_of_these_campaigns = []
    if positive_value_exists(len(only_include_politicians_sent_all_of_these_campaigns)):
        are_politician_we_vote_ids_expected_from_all_campaigns = True
        dict_of_recipient_lists_of_each_campaign = {}
        for campaign_id in only_include_politicians_sent_all_of_these_campaigns:
            try:
                queryset = EmailCampaignRecipient.objects.using('readonly').all()
                queryset = queryset.filter(email_campaign_id=campaign_id)
                queryset = queryset.values_list('politician_we_vote_id', flat=True).distinct()
                dict_of_recipient_lists_of_each_campaign[campaign_id] = list(queryset)
            except Exception as e:
                success = False
                status += "COULD_NOT_RETRIEVE_RECIPIENTS__WAS_SENT_CAMPAIGN_ALL: " + str(e) + ' '
        # Create a list of politician_we_vote_ids that are in all the lists
        #  within dict_of_recipient_lists_of_each_campaign
        politician_we_vote_id_list_sent_all_of_these_campaigns = list(
            set.intersection(*dict_of_recipient_lists_of_each_campaign.values()))

    are_politician_we_vote_ids_expected_from_none_campaigns = False
    politician_we_vote_id_list_to_remove_sent_none = []
    if positive_value_exists(len(only_include_politicians_who_were_sent_none_of_these_campaigns)):
        are_politician_we_vote_ids_expected_from_none_campaigns = True
        try:
            queryset = EmailCampaignRecipient.objects.using('readonly').all()
            queryset = queryset.filter(
                email_campaign_id__in=only_include_politicians_who_were_sent_none_of_these_campaigns)
            queryset = queryset.values_list('politician_we_vote_id', flat=True).distinct()
            politician_we_vote_id_list_to_remove_sent_none = list(queryset)
        except Exception as e:
            success = False
            status += "COULD_NOT_RETRIEVE_RECIPIENTS__WAS_NOT_SENT_CAMPAIGN_ANY: " + str(e) + ' '

    # TODO: Think through this logic again -- kind of complicated! Maybe we don't need this option?
    # if positive_value_exists(len(only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns)):
    #     try:
    #         queryset = EmailCampaignRecipient.objects.using('readonly').all()
    #         queryset = queryset.filter(
    #             email_campaign_id__in=only_include_politicians_who_were_not_sent_at_least_one_of_these_campaigns)
    #         queryset = queryset.values_list('politician_we_vote_id', flat=True).distinct()
    #         politician_we_vote_id_list_sent_at_least_one = list(queryset)
    #         # politician_we_vote_id_list_who_were_not_sent_at_least_one
    #         if positive_value_exists(len(politician_we_vote_id_list_sent_at_least_one)):
    #             # politician_we_vote_id_list should be the previous values minus any politician_we_vote_ids
    #             #  in politician_we_vote_id_list_sent_at_least_one
    #
    #             pass
    #         else:
    #             # No politicians found who received any of these campaigns.
    #             politician_we_vote_id_list = []
    #     except Exception as e:
    #         success = False
    #         status += "COULD_NOT_RETRIEVE_RECIPIENTS__WAS_NOT_SENT_CAMPAIGN_AT_LEAST_ONE: " + str(e) + ' '

    # Generating the "big list" of politician_we_vote_ids
    politician_we_vote_id_list = []
    politician_we_vote_id_list_required = \
        are_politician_we_vote_ids_expected_from_all_campaigns or \
        are_politician_we_vote_ids_expected_from_any_campaigns or \
        are_politician_we_vote_ids_expected_from_none_campaigns
    if are_politician_we_vote_ids_expected_from_election_list:
        # We are getting the "big list" of politician_we_vote_ids from the election list
        politician_we_vote_id_list = politician_we_vote_id_list_from_election_list
    elif politician_we_vote_id_list_required or audience_type_is_politician:
        # We need to get the "big list" of politician_we_vote_ids from "Audience type is Politician"
        #  captured in FILTER_TYPE_AUDIENCE_TYPE
        queryset = Politician.objects.all()
        queryset = queryset.values_list('we_vote_id', flat=True).distinct()
        politician_we_vote_id_list = list(queryset)

    # Do the logical combination of politician_we_vote_id_lists into single list
    if are_politician_we_vote_ids_expected_from_none_campaigns:
        if positive_value_exists(len(politician_we_vote_id_list_to_remove_sent_none)):
            # Remove from politician_we_vote_id_list any politician_we_vote_ids
            #  in politician_we_vote_id_list_sent_at_least_one
            politician_we_vote_id_list = list(set(politician_we_vote_id_list) -
                                              set(politician_we_vote_id_list_to_remove_sent_none))
        else:
            # Leave politician_we_vote_id_list as is
            pass

    if are_politician_we_vote_ids_expected_from_all_campaigns:
        if positive_value_exists(len(politician_we_vote_id_list_sent_all_of_these_campaigns)):
            # politician_we_vote_id_list should be the values that are in both politician_we_vote_id_list
            #  and politician_we_vote_id_list_sent_all_of_these_campaigns
            politician_we_vote_id_list = list(set(politician_we_vote_id_list) &
                                              set(politician_we_vote_id_list_sent_all_of_these_campaigns))
        else:
            # No politicians found who received all of these campaigns.
            politician_we_vote_id_list = []

    if are_politician_we_vote_ids_expected_from_any_campaigns:
        if positive_value_exists(len(politician_we_vote_id_list_sent_any_of_these_campaigns)):
            # politician_we_vote_id_list should be the values that are in both politician_we_vote_id_list
            #  and politician_we_vote_id_list_sent_any_of_these_campaigns
            politician_we_vote_id_list = list(set(politician_we_vote_id_list) &
                                              set(politician_we_vote_id_list_sent_any_of_these_campaigns))
        else:
            # No politicians found who received any of these campaigns.
            politician_we_vote_id_list = []

    if politician_we_vote_id_list_required and len(politician_we_vote_id_list) == 0:
        status += 'NO_POLITICIANS_FOUND_IN_AUDIENCE_FILTER_CHAIN '
        error_results['politician_list_length'] = politician_list_length
        error_results['status'] = status
        error_results['success'] = True
        return error_results

    try:
        queryset = Politician.objects.all()
        if are_politician_we_vote_ids_expected_from_election_list or len(politician_we_vote_id_list) > 0:
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
        if positive_value_exists(do_not_include_is_claimed_politicians):
            queryset = queryset.exclude(is_claimed_profile=True)
        elif positive_value_exists(only_include_is_claimed_politicians):
            queryset = queryset.filter(is_claimed_profile=True)
            if positive_value_exists(is_claimed_profile_date_time_window_length):
                # Calculate the cutoff datetime
                cutoff_datetime = timezone.now() - is_claimed_profile_date_time_window_length
                # Only include politicians whose profile was claimed after the cutoff date
                queryset = queryset.filter(is_claimed_profile_date_time__gte=cutoff_datetime)
        politician_list_length = queryset.count()
        queryset = queryset.order_by('-date_last_updated')
        politician_list = list(queryset)
    except Exception as e:
        status += f'PROBLEM_RETRIEVING_POLITICIANS: {e}'
        error_results['politician_list_length'] = politician_list_length
        error_results['status'] = status
        error_results['success'] = False
        return error_results

    try:
        from campaign.models import CampaignX
        queryset = CampaignX.objects.using('readonly').filter(
            linked_politician_we_vote_id__in=politician_we_vote_id_list)
        campaignx_list = list(queryset)
        # Put all the campaigns into a dictionary for easy lookup, with politician_we_vote_id as the key
        campaignx_dict = {campaign.linked_politician_we_vote_id: campaign for campaign in campaignx_list}
        # We need: passkey_for_creating_campaign_owner
    except Exception as e:
        status += f'PROBLEM_RETRIEVING_CAMPAIGNX: {e}'
        error_results['politician_list'] = politician_list
        error_results['politician_list_length'] = politician_list_length
        error_results['status'] = status
        error_results['success'] = False
        return error_results

    if len(candidate_we_vote_id_list) > 0:
        try:
            from candidate.models import CandidateToOfficeLink
            # In the WeVote data model, we only have one candidate entry per election cycle.
            # We have a different Office entry per election, so if a candidate is in the primary
            # and then the general election, the same candidate will be linked to two offices,
            # one per election.
            queryset = CandidateToOfficeLink.objects.using('readonly').filter(
                candidate_we_vote_id__in=candidate_we_vote_id_list)
            candidate_to_office_link_list = list(queryset)
            # Create a dictionary for easy lookup, with candidate_we_vote_id as the first key,
            # and google_civic_election_id as the second key. The value should be the office_we_vote_id.
            for one_candidate_to_office_link in candidate_to_office_link_list:
                if one_candidate_to_office_link.candidate_we_vote_id not in candidate_to_office_dict:
                    candidate_to_office_dict[one_candidate_to_office_link.candidate_we_vote_id] = {}
                candidate_to_office_dict[one_candidate_to_office_link.candidate_we_vote_id][
                    one_candidate_to_office_link.google_civic_election_id
                ] = one_candidate_to_office_link.contest_office_we_vote_id
        except Exception as e:
            status += f'PROBLEM_RETRIEVING_CAMPAIGNX: {e}'
            error_results['politician_list'] = politician_list
            error_results['politician_list_length'] = politician_list_length
            error_results['status'] = status
            error_results['success'] = False
            return error_results

    return {
        'campaignx_dict': campaignx_dict,
        'candidate_dict': candidate_dict,
        'candidate_to_office_dict': candidate_to_office_dict,
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
    status = ''
    success = True

    results = generate_preview_list_from_audience_builder(
        audience_builder=audience_builder,
        audience_filter_chain_dict=audience_filter_chain_dict,
        audience_filter_dict=audience_filter_dict,
        max_list_length=500,
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
