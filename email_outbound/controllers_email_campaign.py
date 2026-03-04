# email_outbound/controllers_email_campaign.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from config.base import get_environment_variable

from django.db.models import Q
from django.template.loader import render_to_string


from election.models import Election
from email_outbound.functions import convert_html_to_plain_text
from organization.controllers import transform_web_app_url
from politician.models import Politician
from voter.models import VoterManager
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists, STATE_CODE_MAP
from wevote_functions.functions_date import get_current_year_as_integer
from .models import AudienceBuilder, AudienceFilter, AudienceFilterChain, \
    CUSTOMIZATION_TOKEN_CONVERSION_FROM_JAZZ_HR, \
    EmailCampaign, EmailCampaignRecipient, EmailManager, EmailScheduled, \
    EMAIL_TEMPLATE_CUSTOMIZATION_TOKENS, TO_BE_PROCESSED

logger = wevote_functions.admin.get_logger(__name__)

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def augment_email_campaign_recipient(
        email_campaign_recipient,
        campaignx_list_dict={},
        politicians_dict={},
        sender_object={},
        voters_dict={}):
    # NOTE: We may want to bulk retrieve email addresses, voter_we_vote_ids, or politician_we_vote_ids outside
    #  of this function to reduce calls to the database
    save_changes = False
    status = ''
    success = True

    if hasattr(sender_object, 'first_name'):
        email_campaign_recipient.sender_voter_we_vote_id = sender_object.we_vote_id
        email_campaign_recipient.sender_first_name = sender_object.first_name
        email_campaign_recipient.sender_full_name = sender_object.get_full_name()
        email_campaign_recipient.sender_last_name = sender_object.last_name
        save_changes = True

    # Is this email claimed by an existing voter?
    recipient_email_address = ''
    if hasattr(email_campaign_recipient, 'email_address'):
        recipient_email_address = email_campaign_recipient.email_address

    if positive_value_exists(recipient_email_address):
        email_manager = EmailManager()
        temp_voter_we_vote_id = ""
        find_verified_email_results = email_manager.retrieve_primary_email_with_ownership_verified(
            temp_voter_we_vote_id, recipient_email_address, read_only=True)
        if find_verified_email_results['email_address_object_found']:
            verified_email_address_object = find_verified_email_results['email_address_object']
            email_campaign_recipient.recipient_email_we_vote_id = verified_email_address_object.we_vote_id
            email_campaign_recipient.recipient_voter_we_vote_id = verified_email_address_object.voter_we_vote_id
            # The only person who will see this is someone who has access to this verified_email_address
            email_campaign_recipient.recipient_email_subscription_secret_key = \
                verified_email_address_object.subscription_secret_key

    # Retrieve the recipient_voter
    if positive_value_exists(email_campaign_recipient.recipient_voter_we_vote_id):
        recipient_voter = voters_dict.get(email_campaign_recipient.recipient_voter_we_vote_id, {})
        if not hasattr(recipient_voter, 'first_name'):
            try:
                voter_manager = VoterManager()
                results = voter_manager.retrieve_voter_by_we_vote_id(
                    email_campaign_recipient.recipient_voter_we_vote_id)
                if results['voter_found']:
                    recipient_voter = results['voter']
                    voters_dict[email_campaign_recipient.recipient_voter_we_vote_id] = recipient_voter
            except Exception as e:
                status += "VOTER_RETRIEVE_FAILED: " + str(e) + " "
        if hasattr(recipient_voter, 'first_name'):
            email_campaign_recipient.recipient_first_name = recipient_voter.first_name
            email_campaign_recipient.recipient_full_name = recipient_voter.get_full_name()
            email_campaign_recipient.recipient_last_name = recipient_voter.last_name
            save_changes = True

    # Populate politician values from database so we can use in merge_email_campaign_recipient_with_template
    if positive_value_exists(email_campaign_recipient.politician_we_vote_id):
        politician = politicians_dict.get(email_campaign_recipient.politician_we_vote_id, {})
        if not hasattr(politician, 'politician_name'):
            # Retrieve politician from database
            try:
                politician = Politician.objects.get(we_vote_id=email_campaign_recipient.politician_we_vote_id)
                politicians_dict[email_campaign_recipient.politician_we_vote_id] = politician
            except Exception as e:
                status += "POLITICIAN_RETRIEVE_FAILED: " + str(e) + " "
        if hasattr(politician, 'politician_name'):
            email_campaign_recipient.political_party = politician.political_party
            email_campaign_recipient.politician_first_name = politician.first_name
            email_campaign_recipient.politician_full_name = politician.display_full_name()
            email_campaign_recipient.politician_last_name = politician.last_name
            email_campaign_recipient.politician_seo_friendly_path = politician.seo_friendly_path
            email_campaign_recipient.politician_state_code = politician.state_code
            email_campaign_recipient.supporters_count = politician.supporters_count
            save_changes = True

        # Find the upcoming linked candidate and office that this politician is running for office next
        # We need candidate_we_vote_id office_we_vote_id in order to calculate:
        # "[office_url]",

        # Find Campaign Linked to this Politician so we can get the passkey
        try:
            from campaign.models import CampaignX
            # Cannot be read only because we may need to update passkey below
            queryset = CampaignX.objects.all()
            queryset = queryset.filter(linked_politician_we_vote_id=email_campaign_recipient.politician_we_vote_id)
            linked_campaignx_list = list(queryset)
            if len(linked_campaignx_list) > 0:
                linked_campaignx = linked_campaignx_list[0]
                if linked_campaignx and positive_value_exists(linked_campaignx.passkey_for_creating_campaign_owner):
                    email_campaign_recipient.politician_passkey = linked_campaignx.passkey_for_creating_campaign_owner
                    save_changes = True
        except Exception as e:
            status += "CAMPAIGNX_RETRIEVE_FAILED: " + str(e) + " "

    return {
        'campaignx_list_dict':      campaignx_list_dict,
        'email_campaign_recipient': email_campaign_recipient,
        'politicians_dict':         politicians_dict,
        'save_changes':             save_changes,
        'status':                   status,
        'success':                  success,
        'voters_dict':              voters_dict,
    }


def delete_audience_filter(audience_filter_id_to_delete=None):
    chain_list = []
    status = ''
    success = True

    if not positive_value_exists(audience_filter_id_to_delete):
        success = False
        status += "DELETE_AUDIENCE_FILTER_MISSING_REQUIRED_VARIABLES "
        return {
            'chain_list': chain_list,
            'status': status,
            'success': success,
        }

    # Retrieve any AudienceFilterChain entries from the database that contain the
    # AudienceFilter.id in any of the following fields:
    # filter1_id, filter2_id, filter3_id,..., filter9_id
    queryset = AudienceFilterChain.objects.filter(
        Q(filter1_id=audience_filter_id_to_delete) |
        Q(filter2_id=audience_filter_id_to_delete) |
        Q(filter3_id=audience_filter_id_to_delete) |
        Q(filter4_id=audience_filter_id_to_delete) |
        Q(filter5_id=audience_filter_id_to_delete) |
        Q(filter6_id=audience_filter_id_to_delete) |
        Q(filter7_id=audience_filter_id_to_delete) |
        Q(filter8_id=audience_filter_id_to_delete) |
        Q(filter9_id=audience_filter_id_to_delete))
    chain_list = list(queryset)

    # Loop through chain_list, and for each AudienceFilterChain set the filter_id to None whenever it matches
    # the audience_filter_id_to_delete
    chain_list_modified = []
    chains_to_update = []
    for chain in chain_list:
        chain_changed = False
        for filter_position in range(1, 10):
            filter_id_attribute = f'filter{filter_position}_id'
            filter_id = getattr(chain, filter_id_attribute, None)

            if positive_value_exists(filter_id) and str(filter_id) == str(audience_filter_id_to_delete):
                setattr(chain, filter_id_attribute, None)
                chain_changed = True
        if chain_changed:
            chains_to_update.append(chain)
        chain_list_modified.append(chain)
    chain_list = chain_list_modified
    if chains_to_update:
        AudienceFilterChain.objects.bulk_update(
            chains_to_update,
            ['filter1_id', 'filter2_id', 'filter3_id', 'filter4_id',
             'filter5_id', 'filter6_id', 'filter7_id', 'filter8_id', 'filter9_id']
        )

    # Loop through the chain_list again, and for any filterX_id that is None and there is an filter_id after it,
    # shift the filterX_to_filterY_operator
    chain_list_modified = []
    chains_to_update = []
    for chain in chain_list:
        chain_changed = False
        for filter_position in range(1, 9):
            filter_id_attribute = f'filter{filter_position}_id'
            filter_id = getattr(chain, filter_id_attribute, None)
            next_filter_id_attribute = f'filter{filter_position + 1}_id'
            next_filter_id = getattr(chain, next_filter_id_attribute, None)

            if not positive_value_exists(filter_id) and positive_value_exists(next_filter_id):
                setattr(chain, filter_id_attribute, next_filter_id)
                setattr(chain, next_filter_id_attribute, None)
                operator_attribute = f'filter{filter_position}_to_filter{filter_position + 1}_operator'
                next_operator_attribute = f'filter{filter_position + 1}_to_filter{filter_position + 2}_operator'
                if positive_value_exists(getattr(chain, next_operator_attribute, None)):
                    setattr(chain, operator_attribute, getattr(chain, next_operator_attribute, None))
                    setattr(chain, next_operator_attribute, None)
                chain_changed = True
        if chain_changed:
            chains_to_update.append(chain)
        chain_list_modified.append(chain)
    chain_list = chain_list_modified
    if chains_to_update:
        AudienceFilterChain.objects.bulk_update(
            chains_to_update,
            ['filter1_id', 'filter2_id', 'filter3_id', 'filter4_id',
             'filter5_id', 'filter6_id', 'filter7_id', 'filter8_id', 'filter9_id',
             'filter1_to_filter2_operator', 'filter2_to_filter3_operator', 'filter3_to_filter4_operator',
             'filter4_to_filter5_operator', 'filter5_to_filter6_operator', 'filter6_to_filter7_operator',
             'filter7_to_filter8_operator', 'filter8_to_filter9_operator']
        )

    # Loop through the chain_list again, and make sure to remove any final filter1_to_filter2_operators that exist
    #  when there is no second filter_id
    chain_list_modified = []
    chains_to_update = []
    for chain in chain_list:
        chain_changed = False
        for filter_position in range(1, 8):  # Stopped at 8 on purpose
            filter_id_attribute = f'filter{filter_position}_id'
            filter_id = getattr(chain, filter_id_attribute, None)
            next_filter_id_attribute = f'filter{filter_position + 1}_id'
            next_filter_id = getattr(chain, next_filter_id_attribute, None)
            if not positive_value_exists(filter_id) or not positive_value_exists(next_filter_id):
                operator_attribute = f'filter{filter_position}_to_filter{filter_position + 1}_operator'
                setattr(chain, operator_attribute, None)
                chain_changed = True
        if chain_changed:
            chains_to_update.append(chain)
        chain_list_modified.append(chain)
    chain_list = chain_list_modified
    if chains_to_update:
        AudienceFilterChain.objects.bulk_update(
            chains_to_update,
            ['filter1_to_filter2_operator', 'filter2_to_filter3_operator', 'filter3_to_filter4_operator',
             'filter4_to_filter5_operator', 'filter5_to_filter6_operator', 'filter6_to_filter7_operator',
             'filter7_to_filter8_operator', 'filter8_to_filter9_operator']
        )

    # Now delete the AudienceFilter itself
    try:
        audience_filter_to_delete = AudienceFilter.objects.get(id=audience_filter_id_to_delete)
        audience_filter_to_delete.delete()
    except Exception as e:
        status += "AUDIENCE_FILTER_DELETE_FAILED: " + str(e) + " "
    return {
        'chain_list':   chain_list,
        'status':       status,
        'success':      success,
    }


def delete_audience_filter_chain_and_children(audience_builder, audience_filter_chain_id_to_delete):
    # Find it in current AudienceBuilder
    chain_found = False
    builder_relative_chain_position = None
    status = ''
    success = True

    for builder_relative_chain_id in range(1, 10):
        builder_relative_chain_id_attribute = f'audience_filter_chain{builder_relative_chain_id}_id'
        chain_id = getattr(audience_builder, builder_relative_chain_id_attribute, None)

        if positive_value_exists(chain_id) and str(chain_id) == str(audience_filter_chain_id_to_delete):
            chain_found = True
            builder_relative_chain_position = builder_relative_chain_id
            break

    if chain_found:
        try:
            # Get the AudienceFilterChain object
            audience_filter_chain_to_delete = AudienceFilterChain.objects.get(
                id=audience_filter_chain_id_to_delete)

            # Delete all the AudienceFilter objects that are linked to it first
            filter_ids_to_delete = []
            for filter_position in range(1, 10):
                filter_id_attribute = f'filter{filter_position}_id'
                filter_id = getattr(audience_filter_chain_to_delete, filter_id_attribute, None)

                if positive_value_exists(filter_id):
                    filter_ids_to_delete.append(filter_id)

            # Delete all the filters
            if filter_ids_to_delete:
                deleted_count, _ = AudienceFilter.objects.filter(
                    id__in=filter_ids_to_delete).delete()
                status += f"DELETED_{deleted_count}_AUDIENCE_FILTERS "

            # Remove the chain reference from the AudienceBuilder
            if positive_value_exists(builder_relative_chain_position):
                chain_id_attribute = f'audience_filter_chain{builder_relative_chain_position}_id'
                setattr(audience_builder, chain_id_attribute, None)
                # Remove the chain_to_chain operator reference from the AudienceBuilder
                if builder_relative_chain_position > 1:
                    chain_to_chain_attribute = \
                        f'chain{builder_relative_chain_position - 1}_to_chain{builder_relative_chain_position}_operator'
                    setattr(audience_builder, chain_to_chain_attribute, None)
                audience_builder.save()

            # Then delete the AudienceFilterChain object itself
            audience_filter_chain_to_delete.delete()
            status += "AUDIENCE_FILTER_CHAIN_DELETED "

        except AudienceFilterChain.DoesNotExist:
            status += "AUDIENCE_FILTER_CHAIN_NOT_FOUND "
        except Exception as e:
            status += f"ERROR_DELETING_CHAIN: {str(e)} "
            success = False
    else:
        status += "CHAIN_NOT_FOUND_IN_AUDIENCE_BUILDER "

    return {
        'status':   status,
        'success':  success,
    }


def email_campaign_send(
        email_campaign={},
        email_campaign_id=''):
    status = ""
    success = True

    if not positive_value_exists(email_campaign_id):
        status += "EMAIL_CAMPAIGN_ID_REQUIRED "
        return {
            'status':   status,
            'success':  False,
        }

    if not hasattr(email_campaign, 'email_body_template_raw'):
        try:
            email_campaign = EmailCampaign.objects.get(id=email_campaign_id)
        except EmailCampaign.DoesNotExist:
            status += "SEND_EMAIL_CAMPAIGN_NOT_FOUND "
            return {
                'status':   status,
                'success':  False,
            }
        except Exception as e:
            status += f'PROBLEM_RETRIEVING_EMAIL_CAMPAIGN: {e}'
            return {
                'status':   status,
                'success':  False,
            }

    # Get the email_body_template_raw for this campaign - the EmailTemplate was the starting point,
    #  buy may have been edited
    email_body_raw = email_campaign.email_body_template_raw
    email_subject_raw = email_campaign.email_subject_template_raw

    # Get all the previously sent EmailScheduled entries for this email campaign so we can make sure to
    #  not send the same email to the same recipient more than once
    try:
        queryset = EmailScheduled.objects.filter(
            email_campaign_id=email_campaign_id)
        queryset = queryset.values_list('email_campaign_recipient_id', flat=True)
        already_scheduled_recipient_ids = list(queryset)
    except Exception as e:
        status += f'PROBLEM_RETRIEVING_EMAIL_SCHEDULED: {e}'
        return {
            'status':   status,
            'success':  False,
        }

    # Get all specific recipients for this email campaign.
    # Note that we add recipients formulaically in generate_email_campaign_recipients_from_audience_builder
    try:
        queryset = EmailCampaignRecipient.objects.filter(
            email_campaign_id=email_campaign_id)
        # Filter out recipient entries that have already been sent
        queryset = queryset.exclude(id__in=already_scheduled_recipient_ids)
        email_campaign_recipient_list = list(queryset)
    except Exception as e:
        status += f'PROBLEM_RETRIEVING_EMAIL_CAMPAIGN_RECIPIENT: {e}'
        return {
            'status':   status,
            'success':  False,
        }

    web_app_root_url_verified = transform_web_app_url('')  # Change to client URL if needed

    email_manager = EmailManager()

    # template_variables_for_json = {
    #     "subject":                          subject,
    #     "campaignx_title":                  campaignx_title,
    #     "campaignx_url":                    campaignx_url,
    #     "politician_count":                 politician_count,
    #     "politician_full_sentence_string":  politician_full_sentence_string,
    #     "recipient_name":                   recipient_name,
    #     "recipient_unsubscribe_url":        recipient_unsubscribe_url,
    #     "recipient_voter_email":            recipient_email,
    #     "speaker_voter_name":               speaker_voter_name,
    #     "view_main_discussion_page_url":    web_app_root_url_verified + "/news",
    #     "view_your_ballot_url":             web_app_root_url_verified + "/ballot",
    #     "we_vote_hosted_campaign_photo_large_url":  we_vote_hosted_campaign_photo_large_url,
    # }
    # template_variables_in_json = json.dumps(template_variables_for_json, ensure_ascii=True)
    # from_email_for_daily_summary = "We Vote <info@WeVote.US>"  # TODO DALE Make system variable

    # Loop through all recipients to collect items we want to work on in bulk
    for email_campaign_recipient in email_campaign_recipient_list:
        pass

    emails_scheduled = 0
    emails_sent = 0
    recipient_bulk_update_list = []
    recipient_email_subscription_secret_key = ''  # Temp
    for email_campaign_recipient in email_campaign_recipient_list:
        results = schedule_email_campaign_recipient(
            email_body_raw=email_body_raw,
            email_campaign_recipient=email_campaign_recipient,
            email_subject_raw=email_subject_raw,
            recipient_bulk_update_list=recipient_bulk_update_list)
        recipient_bulk_update_list = results['recipient_bulk_update_list']
        status += results['status'] + " "
        email_scheduled_saved = results['email_scheduled_saved']
        email_scheduled_id = results['email_scheduled_id']
        email_scheduled = results['email_scheduled']

        if email_scheduled_saved:
            emails_scheduled += 1
            send_results = email_manager.send_scheduled_email(email_scheduled)
            email_scheduled_sent = send_results['email_scheduled_sent']
            if email_scheduled_sent:
                emails_sent += 1
            else:
                status += "ERROR_SEND_SCHEDULED_EMAIL: " \
                    "{status} " \
                    "".format(
                        status=send_results['status'])

    # We want to bulk update the email_campaign_recipient objects in recipient_bulk_update_list
    try:
        EmailCampaignRecipient.objects.bulk_update(
            recipient_bulk_update_list, [
                'email_body_assembled',
                'email_scheduled',
                'email_subject_assembled'])
        status += \
            "email_campaign_send, EmailCampaignRecipient.objects.bulk_update: " \
            "{emails_scheduled:,} emails scheduled. " \
            "{emails_sent:,} emails_sent. " \
            "".format(
                emails_scheduled=emails_scheduled,
                emails_sent=emails_sent)
    except Exception as e:
        status += "ERROR_EMAIL_CAMPAIGN_RECIPIENT_BULK_UPDATE: {e} " \
            "".format(e=e)
        success = False

    results = {
        'success':  success,
        'status':   status,
    }
    return results


def reorganize_audience_filter_chains(audience_builder):
    """
    After deleting an AudienceFilterChain, reorganize the chain fields so there are no gaps.
    If audience_filter_chain2_id is None but audience_filter_chain3_id has a value,
    move chain3 to chain2, chain4 to chain3, etc.

    :param audience_builder: AudienceBuilder object
    :return: dict with status and success
    """
    status = ''
    success = True
    changes_made = False

    try:
        # Collect all chain IDs and their operators in order
        chain_data = []
        for position in range(1, 10):
            chain_id_attr = f'audience_filter_chain{position}_id'
            chain_id = getattr(audience_builder, chain_id_attr, None)

            # Get the operator that connects this chain to the next one
            operator_attr = f'chain{position}_to_chain{position + 1}_operator'
            operator = getattr(audience_builder, operator_attr, None) if position < 9 else None

            chain_data.append({
                'position': position,
                'chain_id': chain_id,
                'operator': operator
            })

        # Filter out None values to get only the chains that exist
        existing_chains = [item for item in chain_data if positive_value_exists(item['chain_id'])]

        # If we have the same number of existing chains as total positions with values,
        # there are no gaps to fill
        non_none_count = sum(1 for item in chain_data if positive_value_exists(item['chain_id']))
        if len(existing_chains) == non_none_count and all(
                existing_chains[i]['position'] == i + 1 for i in range(len(existing_chains))
        ):
            status += "NO_REORGANIZATION_NEEDED "
            return {
                'audience_builder': audience_builder,
                'changes_made': changes_made,
                'status': status,
                'success': success,
            }

        # Clear all chain fields first
        for position in range(1, 10):
            chain_id_attr = f'audience_filter_chain{position}_id'
            setattr(audience_builder, chain_id_attr, None)

            if position < 9:
                operator_attr = f'chain{position}_to_chain{position + 1}_operator'
                setattr(audience_builder, operator_attr, None)

        # Reassign chains to sequential positions starting from 1
        for new_position, chain_item in enumerate(existing_chains, start=1):
            chain_id_attr = f'audience_filter_chain{new_position}_id'
            setattr(audience_builder, chain_id_attr, chain_item['chain_id'])

            # Set the operator if this isn't the last chain
            if new_position < len(existing_chains):
                operator_attr = f'chain{new_position}_to_chain{new_position + 1}_operator'
                setattr(audience_builder, operator_attr, chain_item['operator'])

            changes_made = True

        if changes_made:
            audience_builder.save()
            status += f"REORGANIZED_{len(existing_chains)}_CHAINS "

    except Exception as e:
        status += f"ERROR_REORGANIZING_CHAINS: {str(e)} "
        success = False

    return {
        'audience_builder': audience_builder,
        'changes_made': changes_made,
        'status': status,
        'success': success,
    }


def save_all_audience_filter_changes(audience_filter_dict={}, request=None):
    status = ""
    success = True

    # Loop through all AudienceFilter objects in the audience_filter_dict dictionary
    change_list = []
    for audience_filter_id, audience_filter in audience_filter_dict.items():
        any_changes_made = False
        # audience_filter_type
        audience_filter_type_key = f'audience_filter_type_{audience_filter_id}'
        if audience_filter_type_key in request.POST:
            setattr(audience_filter, 'audience_filter_type', request.POST.get(audience_filter_type_key, None))
            any_changes_made = True

        # audience_type
        audience_type_modifier_key = f'audience_type_modifier_{audience_filter_id}'
        if audience_type_modifier_key in request.POST:
            setattr(audience_filter, 'audience_type_modifier', request.POST.get(audience_type_modifier_key, None))
            any_changes_made = True

            # Candidate
            audience_type_candidate = False
            audience_type_candidate_key = f'audience_type_candidate_{audience_filter_id}'
            if audience_type_candidate_key in request.POST:
                audience_type_candidate_value = request.POST.get(audience_type_candidate_key, None)
                if audience_type_candidate_value == "CANDIDATE":
                    audience_type_candidate = True
            setattr(audience_filter, 'audience_type_candidate', audience_type_candidate)

            # Organization
            audience_type_organization = False
            audience_type_organization_key = f'audience_type_organization_{audience_filter_id}'
            if audience_type_organization_key in request.POST:
                audience_type_organization_value = request.POST.get(audience_type_organization_key, None)
                if audience_type_organization_value == "ORGANIZATION":
                    audience_type_organization = True
            setattr(audience_filter, 'audience_type_organization', audience_type_organization)

            # Politician
            audience_type_politician = False
            audience_type_politician_key = f'audience_type_politician_{audience_filter_id}'
            if audience_type_politician_key in request.POST:
                audience_type_politician_value = request.POST.get(audience_type_politician_key, None)
                if audience_type_politician_value == "POLITICIAN":
                    audience_type_politician = True
            setattr(audience_filter, 'audience_type_politician', audience_type_politician)

            # Voter
            audience_type_voter = False
            audience_type_voter_key = f'audience_type_voter_{audience_filter_id}'
            if audience_type_voter_key in request.POST:
                audience_type_voter_value = request.POST.get(audience_type_voter_key, None)
                if audience_type_voter_value == "VOTER":
                    audience_type_voter = True
            setattr(audience_filter, 'audience_type_voter', audience_type_voter)

        # election_modifier
        election_modifier_key = f'election_modifier_{audience_filter_id}'
        if election_modifier_key in request.POST:
            setattr(audience_filter, 'election_modifier', request.POST.get(election_modifier_key, None))
            any_changes_made = True
        election_key = f'google_civic_election_id_{audience_filter_id}'
        if election_key in request.POST:
            setattr(audience_filter, 'google_civic_election_id', request.POST.get(election_key, None))
            any_changes_made = True

        # email_address_modifier
        email_address_modifier_key = f'email_address_modifier_{audience_filter_id}'
        if email_address_modifier_key in request.POST:
            setattr(audience_filter, 'email_address_modifier', request.POST.get(email_address_modifier_key, None))
            any_changes_made = True

        # has_been_contacted_modifier
        has_been_contacted_modifier_key = f'has_been_contacted_modifier_{audience_filter_id}'
        if has_been_contacted_modifier_key in request.POST:
            setattr(audience_filter, 'has_been_contacted_modifier', request.POST.get(has_been_contacted_modifier_key, None))
            any_changes_made = True

        # has_claimed_politician_modifier
        has_claimed_politician_modifier_key = f'has_claimed_politician_modifier_{audience_filter_id}'
        if has_claimed_politician_modifier_key in request.POST:
            setattr(audience_filter, 'has_claimed_politician_modifier', request.POST.get(has_claimed_politician_modifier_key, None))
            any_changes_made = True

        # has_opened_modifier
        has_opened_modifier_key = f'has_opened_modifier_{audience_filter_id}'
        if has_opened_modifier_key in request.POST:
            setattr(audience_filter, 'has_opened_modifier', request.POST.get(has_opened_modifier_key, None))
            any_changes_made = True
            # Get the list of selected state codes
            has_opened_list_key = f'has_opened_{audience_filter_id}[]'
            if has_opened_list_key in request.POST:
                has_opened_selected = request.POST.getlist(f'has_opened_{audience_filter.id}[]')
                # This will return a list like: ['32', '44', '73']
                # Convert the list to a comma-separated string, without any square brackets, commas or spaces
                has_opened_selected_str = ','.join(has_opened_selected)
                setattr(audience_filter, 'has_opened_list', has_opened_selected_str)
            else:
                setattr(audience_filter, 'has_opened_list', None)

        # has_signed_in_modifier
        has_signed_in_modifier_key = f'has_signed_in_modifier_{audience_filter_id}'
        if has_signed_in_modifier_key in request.POST:
            setattr(audience_filter, 'has_signed_in_modifier', request.POST.get(has_signed_in_modifier_key, None))
            any_changes_made = True

        # phone_number_modifier
        phone_number_modifier_key = f'phone_number_modifier_{audience_filter_id}'
        if phone_number_modifier_key in request.POST:
            setattr(audience_filter, 'phone_number_modifier', request.POST.get(phone_number_modifier_key, None))
            any_changes_made = True

        # state_modifier
        if audience_filter.audience_filter_type == 'FILTER_TYPE_STATE_CODE':
            state_modifier_key = f'state_modifier_{audience_filter_id}'
            if state_modifier_key in request.POST:
                setattr(audience_filter, 'state_modifier', request.POST.get(state_modifier_key, None))
                any_changes_made = True
            # Get the list of selected state codes
            state_list_key = f'state_code_{audience_filter_id}[]'
            if state_list_key in request.POST:
                state_codes_selected = request.POST.getlist(f'state_code_{audience_filter.id}[]')
                # This will return a list like: ['CA', 'NY', 'TX']
                # Convert the list to a comma-separated string, without any square brackets, commas or spaces
                state_codes_selected_str = ','.join(state_codes_selected)
                setattr(audience_filter, 'state_code_list', state_codes_selected_str)
                any_changes_made = True
            else:
                setattr(audience_filter, 'state_code_list', None)
                any_changes_made = True

        if any_changes_made:
            change_list.append(audience_filter)

    # Save changes to the change_list in bulk
    try:
        AudienceFilter.objects.bulk_update(change_list, [
            'audience_filter_type',
            'audience_type_candidate',
            'audience_type_modifier',
            'audience_type_organization',
            'audience_type_politician',
            'audience_type_voter',
            'election_modifier',
            'email_address_modifier',
            'google_civic_election_id',
            'has_been_contacted_modifier',
            'has_claimed_politician_modifier',
            'has_opened_list',
            'has_opened_modifier',
            'has_signed_in_modifier',
            'phone_number_modifier',
            'state_code_list',
            'state_modifier'])
    except Exception as e:
        status += f"ERROR_SAVING_AUDIENCE_FILTERS: {str(e)} "
        success = False

    return {
        'status': status,
        'success': success,
    }


def schedule_email_campaign_recipient(
        email_campaign_recipient=None,
        email_body_raw=None,
        email_subject_raw=None,
        recipient_bulk_update_list=[],
        template_variables_in_json=None):
    email_manager = EmailManager()
    status = ""
    template_variables_in_json = {}

    # Generate an open tracking code for the recipient
    if email_campaign_recipient:
        EmailCampaignRecipient.generate_open_tracking_code(email_campaign_recipient)

    email_template_results = merge_email_campaign_recipient_with_template(
        email_body_raw=email_body_raw,
        email_campaign_recipient=email_campaign_recipient,
        email_subject_raw=email_subject_raw,
        template_variables_in_json=template_variables_in_json)
    if email_template_results['success']:
        subject = email_template_results['subject']
        message_text = email_template_results['message_text']
        message_html = email_template_results['message_html']
        schedule_email_results = email_manager.schedule_email_from_email_campaign_recipient(
            email_campaign_recipient=email_campaign_recipient,
            subject=subject,
            message_text=message_text,
            message_html=message_html,
            send_status=TO_BE_PROCESSED)
        success = schedule_email_results['success']
        status += schedule_email_results['status']
        email_scheduled_saved = schedule_email_results['email_scheduled_saved']
        email_scheduled = schedule_email_results['email_scheduled']
        email_scheduled_id = schedule_email_results['email_scheduled_id']
        if positive_value_exists(email_scheduled_saved):
            email_campaign_recipient.email_body_assembled = message_html
            email_campaign_recipient.email_scheduled = True
            email_campaign_recipient.email_subject_assembled = subject
            recipient_bulk_update_list.append(email_campaign_recipient)
    else:
        success = False
        status += "SCHEDULE_EMAIL_TEMPLATE_NOT_PROCESSED "
        status += email_template_results['status'] + " "
        email_scheduled_saved = False
        email_scheduled = EmailScheduled()
        email_scheduled_id = 0

    results = {
        'success': success,
        'status': status,
        'email_scheduled_saved': email_scheduled_saved,
        'email_scheduled_id': email_scheduled_id,
        'email_scheduled': email_scheduled,
        'recipient_bulk_update_list': recipient_bulk_update_list,
    }
    return results


def merge_email_campaign_recipient_with_template(
        email_body_raw=None,
        email_campaign_recipient=None,
        email_subject_raw=None,
        template_variables_in_json={}):
    email_manager = EmailManager()
    success = True
    status = ''

    try:
        # Merge the email template with the recipient's specific information
        subject = email_subject_raw
    except Exception as e:
        status += "PROBLEM_GETTING_SUBJECT_FROM_TEMPLATE: " + str(e) + " "
        subject = "From We Vote"

    try:
        # Merge the email template with the recipient's specific information
        message_html = email_body_raw
    except Exception as e:
        status += "PROBLEM_GETTING_MESSAGE: " + str(e) + " "
        message_html = ""
        success = False
        # CONSIDER exiting out

    # Unsubscribe link in email
    # recipient_unsubscribe_url = \
    #     web_app_root_url_verified + "/settings/notifications/esk/" + recipient_email_subscription_secret_key
    # recipient_unsubscribe_url = \
    #     "{root_url}/unsubscribe/{email_secret_key}/friendcampaignsupport" \
    #     "".format(
    #         email_secret_key=recipient_email_subscription_secret_key,
    #         root_url=web_app_root_url_verified,
    #     )
    # Instant unsubscribe link in email header
    # list_unsubscribe_url = \
    #     "{root_url}/apis/v1/unsubscribeInstant/{email_secret_key}/friendcampaignsupport/" \
    #     "".format(
    #         email_secret_key=recipient_email_subscription_secret_key,
    #         root_url=WE_VOTE_SERVER_ROOT_URL,
    #     )
    # # Instant unsubscribe email address in email header
    # # from voter.models import NOTIFICATION_VOTER_DAILY_SUMMARY_EMAIL  # To be updated
    # list_unsubscribe_mailto = "unsubscribe@wevote.us?subject=unsubscribe%20{setting}" \
    #                           "".format(setting='friendcampaignsupport')

    # If the template was brought over from JazzHR, convert the JazzHR tokens to We Vote tokens
    for jazz_hr_token, we_vote_token in CUSTOMIZATION_TOKEN_CONVERSION_FROM_JAZZ_HR.items():
        if jazz_hr_token in message_html:
            message_html = message_html.replace(jazz_hr_token, we_vote_token)
        if jazz_hr_token in subject:
            subject = subject.replace(jazz_hr_token, we_vote_token)

    # Build a dictionary of token replacements
    token_replacements = {}

    # We want to replace all instances of these variables in the template with the recipient's specific information
    # Get values from email_campaign_recipient object, pulled from the database in augment_email_campaign_recipient
    if email_campaign_recipient:
        # These are all related to EMAIL_TEMPLATE_CUSTOMIZATION_TOKENS

        #
        open_tracking_code = getattr(email_campaign_recipient, "open_tracking_code", "") or ""
        open_tracking_pixel_html = ""
        # Tracking pixel and footer text only generated if open tracking code is present
        if open_tracking_code:
            open_tracking_pixel_html = (
                f'<img src="{WE_VOTE_SERVER_ROOT_URL}/apis/v1/opened/'
                f'{open_tracking_code}/" width="1" height="1" alt="" />'
            )  # WV-2447 "Open Tracking for Email Campaign System" should go here
            email_footer_html = \
                "<br />This email uses tracking to understand whether messages are opened " \
                "so we can improve our communications. Learn more: " \
                "<a href='https://wevote.us/privacy'>Privacy Policy</a>." \
                "{open_tracking_pixel_html}<br />".format(
                    open_tracking_pixel_html=open_tracking_pixel_html,
                )
        else:
            email_footer_html = ""
        token_replacements['[email_footer]'] = email_footer_html

        # Add link to subscription key

        token_replacements['[my_first_name]'] = getattr(email_campaign_recipient, 'sender_first_name', '')
        token_replacements['[my_full_name]'] = getattr(email_campaign_recipient, 'sender_full_name', '')
        token_replacements['[my_last_name]'] = getattr(email_campaign_recipient, 'sender_last_name', '')

        # Find the upcoming linked candidate and office that this politician is running for office next
        # We need candidate_we_vote_id office_we_vote_id in order to calculate:
        # "[office_url]",
        # "[office_url_with_intro]",  # Add ?office_intro=1 to the office_page URL

        political_party = getattr(email_campaign_recipient, 'political_party', '')
        token_replacements = \
            replace_token_with_unknown_if_no_value('political_party', political_party, token_replacements)

        politician_passkey = getattr(email_campaign_recipient, 'politician_passkey', '')
        token_replacements = \
            replace_token_with_unknown_if_no_value('politician_passkey', politician_passkey, token_replacements)

        token_replacements['[seo_friendly_path]'] = \
            getattr(email_campaign_recipient, 'politician_seo_friendly_path', '')

        # Create HTML that displays we_vote_hosted_profile_image_url_large and places in [politician_photo]

        state_code = getattr(email_campaign_recipient, 'politician_state_code', '')
        token_replacements = \
            replace_token_with_unknown_if_no_value('state_code', state_code, token_replacements)

        recipient_first_name = getattr(email_campaign_recipient, 'recipient_first_name', '')
        token_replacements = replace_token_with_space('recipient_first_name', recipient_first_name, token_replacements)

        recipient_full_name = getattr(email_campaign_recipient, 'recipient_full_name', '')
        token_replacements = replace_token_with_space('recipient_full_name', recipient_full_name, token_replacements)

        recipient_last_name = getattr(email_campaign_recipient, 'recipient_last_name', '')
        token_replacements = replace_token_with_space('recipient_last_name', recipient_last_name, token_replacements)

        token_replacements['[recipient_voter_email]'] = getattr(email_campaign_recipient, 'recipient_voter_email', '')

        token_replacements['[supporters_count]'] = getattr(email_campaign_recipient, 'supporters_count', '0')

        # Sender name parts

        # Unsubscribe link

        # link_to_office
        # link_to_politician

    # Override with values from template_variables_in_json if provided
    if template_variables_in_json:
        for token in EMAIL_TEMPLATE_CUSTOMIZATION_TOKENS:
            # Remove brackets to get the key name
            key = token.strip('[]')
            if key in template_variables_in_json:
                token_replacements[token] = template_variables_in_json[key]

    # Apply all token replacements to subject and message_html
    for token, replacement_value in token_replacements.items():
        if token in subject:
            subject = subject.replace(token, str(replacement_value))
        if token in message_html:
            message_html = message_html.replace(token, str(replacement_value))

    # Convert HTML to plain text for the text version of the email
    message_text = convert_html_to_plain_text(message_html)

    results = {
        'success':      success,
        'status':       status,
        'subject':      subject,
        'message_text': message_text,
        'message_html': message_html,
    }
    return results


def render_audience_builder_html(
        audience_builder={},
        audience_filter_chain_dict={},
        audience_filter_dict={},
        request=None):
    audience_builder_html = ''
    audience_filter_html_dict = {}
    chain_operand_to_follow_dict = {}
    filter_operand_to_follow_dict = {}
    status = ''
    success = True

    # Gather collection of all EmailCampaign rows so we can offer them in the AudienceFilter
    campaign_list = []
    try:
        queryset = EmailCampaign.objects.all()
        queryset = queryset.filter(deleted=False)
        queryset = queryset.order_by('-date_last_updated')
        campaign_list = list(queryset)
    except Exception as e:
        status += f"ERROR_RETRIEVING_EMAIL_CAMPAIGNS: {e}"
        success = False

    # Gather data used by multiple chains and filters
    election_list = []
    try:
        this_year = get_current_year_as_integer()
        election_list_query = Election.objects.all()
        election_list_query = election_list_query.order_by('election_day_text', 'election_name')
        first_day_of_year_to_show = "{year}-01-01".format(year=this_year)
        last_day_of_year_to_show = "{year}-12-31".format(year=this_year)
        election_list_query = election_list_query.filter(
            election_day_text__gte=first_day_of_year_to_show,
            election_day_text__lte=last_day_of_year_to_show)
        election_list = list(election_list_query)
    except Exception as e:
        status += f"ERROR_RETRIEVING_ELECTIONS: {e}"
        success = False

    # Render each chain one at a time
    for builder_relative_chain_id in range(1, 10):
        builder_relative_chain_id_string_list = []
        builder_relative_chain_id_attribute = f'audience_filter_chain{builder_relative_chain_id}_id'
        chain_id = getattr(audience_builder, builder_relative_chain_id_attribute, None)

        # Operands between chains
        builder_relative_chain_id_next = builder_relative_chain_id + 1
        if builder_relative_chain_id_next < 10:
            # chain_to_chain_operand_key must match builder_relative_chain_id_string below
            chain_to_chain_operand_key = f'filter{builder_relative_chain_id}'
            chain_to_chain_operand_attribute = \
                f'chain{builder_relative_chain_id}_to_chain{builder_relative_chain_id_next}_operator'
            chain_to_chain_operand = getattr(audience_builder, chain_to_chain_operand_attribute, '')
            chain_operand_to_follow_dict[chain_to_chain_operand_key] = chain_to_chain_operand

        # Operands between filters in this chain
        if positive_value_exists(chain_id):
            if chain_id in audience_filter_chain_dict:
                audience_filter_chain = audience_filter_chain_dict[chain_id]
                for filter_relative_id in range(1, 10):
                    builder_relative_chain_id_string = f'filter{builder_relative_chain_id}'
                    filter_relative_id_next = filter_relative_id + 1
                    if filter_relative_id_next < 10:
                        filter_operator_attribute = \
                            f'filter{filter_relative_id}_to_filter{builder_relative_chain_id_next}_operator'
                        operand = getattr(audience_filter_chain, filter_operator_attribute, '')
                        filter_operand_to_follow_dict[builder_relative_chain_id_string] = operand

        # Render all audience_filters and the enclosing audience_filter_chain info for this chain
        if positive_value_exists(chain_id):
            if chain_id in audience_filter_chain_dict:
                audience_filter_chain = audience_filter_chain_dict[chain_id]
                chain_results = render_audience_filter_chain_html(
                    audience_builder=audience_builder,
                    audience_filter_chain=audience_filter_chain,
                    audience_filter_dict=audience_filter_dict,
                    campaign_list=campaign_list,
                    election_list=election_list,
                    request=request)
                if chain_results['success']:
                    builder_relative_chain_id_string = f'filter{builder_relative_chain_id}'
                    audience_filter_html_dict[builder_relative_chain_id_string] = \
                        chain_results['audience_filter_chain_html']
                    builder_relative_chain_id_string_list.append(builder_relative_chain_id_string)

                    context = {
                        'audience_builder_id': audience_builder.id,
                        'audience_filter_html_dict': audience_filter_html_dict,
                        'audience_builder_relative_chain_id_string_list': builder_relative_chain_id_string_list,
                        'chain_operand_to_follow_dict': chain_operand_to_follow_dict,
                        'filter_operand_to_follow_dict': filter_operand_to_follow_dict,
                    }
                    audience_builder_filter_chain_list_html = render_to_string(
                        "email_outbound/audience_builder_filter_chain_list.html",
                        context, request=request)
                    audience_builder_html += audience_builder_filter_chain_list_html
                else:
                    status += "RENDER_NOT_SUCCESSFUL: " + chain_results['status'] + " "
            else:
                status += f"AUDIENCE_FILTER_CHAIN_NOT_FOUND_IN_DICT: {chain_id} "

    return {
        'audience_builder_html': audience_builder_html,
        'status': status,
        'success': success,
    }


def render_audience_filter_chain_html(
        audience_builder={},
        audience_filter_chain={},
        audience_filter_dict={},
        campaign_list=[],
        election_list=[],
        request=None):
    audience_filter_id_dict = {}
    audience_filter_html_dict = {}
    status = ''
    success = True

    # Cycle through all the audience_filters in this chain
    # Loop through filter1_id to filter9_id
    filter_operand_to_follow_dict = {}
    chain_relative_filter_id_string_list = []
    for chain_relative_filter_id in range(1, 10):
        # This is the attribute in audience_filter_chain which holds the id of the audience_filter
        chain_relative_filter_id_attribute = f'filter{chain_relative_filter_id}_id'
        audience_filter_id = getattr(audience_filter_chain, chain_relative_filter_id_attribute, None)

        if positive_value_exists(audience_filter_id):
            # If we recognize the id of the audience_filter, we can proceed to rendering the audience_filter html
            if audience_filter_id in audience_filter_dict:
                audience_filter = audience_filter_dict[audience_filter_id]
                filter_results = render_audience_filter_html(
                    audience_filter=audience_filter,
                    audience_filter_chain=audience_filter_chain,
                    campaign_list=campaign_list,
                    election_list=election_list,
                    request=request)
                if filter_results['success']:
                    chain_relative_filter_id_string = f'filter{chain_relative_filter_id}'
                    audience_filter_html_dict[chain_relative_filter_id_string] = filter_results['audience_filter_html']
                    audience_filter_id_dict[chain_relative_filter_id_string] = audience_filter_id
                    chain_relative_filter_id_string_list.append(chain_relative_filter_id_string)
                    chain_relative_filter_id_next = chain_relative_filter_id + 1
                    if chain_relative_filter_id_next < 10:
                        filter_operator_attribute = \
                            f'filter{chain_relative_filter_id}_to_filter{chain_relative_filter_id_next}_operator'
                        operand = getattr(audience_filter_chain, filter_operator_attribute, '')
                        filter_operand_to_follow_dict[chain_relative_filter_id_string] = operand
                else:
                    status += "RENDER_NOT_SUCCESSFUL: " + filter_results['status'] + " "
                    success = False
            else:
                status += f"AUDIENCE_FILTER_NOT_FOUND: {audience_filter_id} "
    context = {
        'audience_filter_html_dict':            audience_filter_html_dict,
        'audience_filter_id_dict':              audience_filter_id_dict,
        'chain_id':                             audience_filter_chain.id,
        'chain_relative_filter_id_string_list': chain_relative_filter_id_string_list,
        'filter_operand_to_follow_dict':        filter_operand_to_follow_dict,
    }
    audience_filter_chain_html = render_to_string("email_outbound/audience_filter_chain.html",
                                                  context, request=request)

    return {
        'audience_filter_chain_html': audience_filter_chain_html,
        'status': status,
        'success': success,
    }


def render_audience_filter_html(
        audience_filter={},
        audience_filter_chain={},
        campaign_list=[],
        election_list=[],
        request=None):
    audience_type_list = [
        'audience_type_candidate',
        'audience_type_organization',
        'audience_type_politician',
        'audience_type_voter',
    ]
    audience_types_selected_string = ''
    election_name_selected = ''
    has_opened_selected = []
    has_opened_selected_string = ''
    state_codes_selected = []
    state_codes_selected_string = ''
    status = ''
    success = True
    # If a valid audience_filter was passed in, render the audience_filter html
    if hasattr(audience_filter, 'google_civic_election_id'):
        # If any of the following audience_type_ values are true (like audience_type_candidate,
        # audience_type_voter, etc.), create a string that shows "Candidate, Voter" etc.
        if positive_value_exists(audience_filter.audience_type_candidate) or \
                positive_value_exists(audience_filter.audience_type_voter) or \
                positive_value_exists(audience_filter.audience_type_organization) or \
                positive_value_exists(audience_filter.audience_type_politician):
            audience_type_name_dict = {
                'audience_type_candidate': 'Candidate',
                'audience_type_organization': 'Organization',
                'audience_type_politician': 'Politician',
                'audience_type_voter': 'Voter',
            }
            # Loop through audience_type_list. If audience_filter.audience_type_... is true, append the corresponding
            # name from audience_type_name_list to audience_types_selected_string
            for audience_type in audience_type_list:
                if positive_value_exists(getattr(audience_filter, audience_type)):
                    audience_types_selected_string += audience_type_name_dict[audience_type] + ', '
            # Remove the trailing comma and space
            audience_types_selected_string = audience_types_selected_string[:-2]

        if positive_value_exists(audience_filter.google_civic_election_id):
            # loop through election_list and find the election with the same google_civic_election_id
            audience_filter_election_id = convert_to_int(audience_filter.google_civic_election_id)
            for one_election in election_list:
                one_election_id = convert_to_int(one_election.google_civic_election_id)
                if one_election_id == audience_filter_election_id:
                    election_name_selected = one_election.election_name
                    break

        if positive_value_exists(audience_filter.has_opened_list):
            # Convert a comma separated list of EmailCampaign ids (ex/ "34,53") in has_opened_list,
            #  to a python list
            has_opened_selected = audience_filter.has_opened_list.split(',')
            has_opened_selected_name_list = []
            for one_campaign in campaign_list:
                if str(one_campaign.id) in has_opened_selected:
                    has_opened_selected_name_list.append(one_campaign.email_campaign_name)
            has_opened_selected_string = ', '.join(has_opened_selected_name_list)

        if positive_value_exists(audience_filter.state_code_list):
            # Convert a comma separated list of state codes (ex/ "CA,AZ") in state_code_list, to a python list
            state_code_list = audience_filter.state_code_list.split(',')
            # Convert each state code in state_code_list to uppercase
            state_code_list = [state_code.upper() for state_code in state_code_list]
            state_codes_selected = state_code_list
            state_codes_selected_string = ', '.join(state_code_list)

    context = {
        'audience_filter': audience_filter,
        'audience_filter_chain': audience_filter_chain,
        'audience_types_selected_string': audience_types_selected_string,
        'campaign_list': campaign_list,
        'election_name_selected': election_name_selected,
        'election_list': election_list,
        'has_opened_selected': has_opened_selected,
        'has_opened_selected_string': has_opened_selected_string,
        'state_code_map': STATE_CODE_MAP,
        'state_codes_selected': state_codes_selected,
        'state_codes_selected_string': state_codes_selected_string,
    }
    audience_filter_html = \
        render_to_string("email_outbound/audience_filter_body.html", context, request=request)
    results = {
        'audience_filter_html': audience_filter_html,
        'audience_filter_id': audience_filter.id,
        'status': status,
        'success': success,
    }
    return results


def replace_token_with_space(token_key_without_square_brackets, value, token_replacements):
    token_key_with_square_brackets = f'[{token_key_without_square_brackets}]'
    if positive_value_exists(value):
        token_replacements[token_key_with_square_brackets] = value
    else:
        token_key_with_square_brackets_and_space = f' [{token_key_without_square_brackets}]'
        token_replacements[token_key_with_square_brackets_and_space] = ''  # Replace the space before also if empty
        token_replacements[token_key_with_square_brackets] = ''
    return token_replacements


def replace_token_with_unknown_if_no_value(token_key_without_square_brackets, value, token_replacements):
    token_key_with_square_brackets = f'[{token_key_without_square_brackets}]'
    if positive_value_exists(value):
        token_replacements[token_key_with_square_brackets] = value
    else:
        token_replacements[token_key_with_square_brackets] = '<ital>Unknown</ital>'
    return token_replacements
