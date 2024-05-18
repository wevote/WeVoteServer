# voter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import string
from base64 import b64encode
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.core.exceptions import RequestDataTooBig
from django.db.models import Q, Subquery
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.timezone import now

import wevote_functions.admin
from admin_tools.views import redirect_to_sign_in_page
from email_outbound.models import EmailAddress, EmailManager
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception, handle_exception
from image.controllers import create_resized_images
from import_export_facebook.models import FacebookLinkToVoter, FacebookManager
from organization.models import Organization, OrganizationManager, INDIVIDUAL
from position.controllers import merge_duplicate_positions_for_voter
from position.models import PositionEntered, PositionForFriends
from share.controllers import update_voter_who_shares_tables_from_shared_item_list
from share.models import SharedItem, VoterWhoSharesSummaryAllTime, VoterWhoSharesSummaryOneYear
from sms.models import SMSManager, SMSPhoneNumber
from stripe_donations.models import StripeManager, StripePayments
from twitter.models import TwitterLinkToOrganization, TwitterLinkToVoter, TwitterUserManager
from volunteer_task.models import VolunteerTeam, VolunteerTeamMember
from voter.models import VoterIssuesLookup
from wevote_functions.functions import convert_to_int, generate_random_string, get_voter_api_device_id, \
    get_voter_device_id, set_voter_api_device_id, positive_value_exists
from wevote_settings.constants import ELECTION_YEARS_AVAILABLE
from voter.controllers import delete_all_voter_information_permanently, process_maintenance_status_flags, \
    voter_merge_two_accounts_action, voter_save_photo_from_file_reader
from .controllers_voter_create import create_dev_user
from .models import fetch_voter_id_from_voter_device_link, \
    PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_UPLOADED, \
    Voter, VoterAddressManager, VoterDeviceLinkManager, \
    voter_has_authority, VoterManager, VoterMergeLog, VoterMergeStatus, voter_setup

logger = wevote_functions.admin.get_logger(__name__)


@login_required
def finish_voter_merge_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'voter_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    from_voter = None
    from_voter_we_vote_id = request.GET.get('from_voter_we_vote_id', '')
    status = ""
    success = True
    to_voter = None
    to_voter_we_vote_id = request.GET.get('to_voter_we_vote_id', '')
    voter_merge_status = None

    if positive_value_exists(from_voter_we_vote_id) and positive_value_exists(to_voter_we_vote_id):
        try:
            from_voter = Voter.objects.get(we_vote_id=from_voter_we_vote_id)
            to_voter = Voter.objects.get(we_vote_id=to_voter_we_vote_id)
        except Exception as e:
            status += "VOTER_MERGE_STATUS_RETRIEVE_VOTER_PROBLEM: " + str(e) + " "
            success = False
    else:
        status += "VOTER_MERGE_STATUS_MISSING_VOTER_ID_PROBLEM "
        success = False

    if success:
        try:
            voter_merge_status = VoterMergeStatus.objects.get(
                from_voter_we_vote_id=from_voter_we_vote_id,
                to_voter_we_vote_id=to_voter_we_vote_id,
            )
        except Exception as e:
            status += "VOTER_MERGE_STATUS_RETRIEVE_PROBLEM: " + str(e) + " "
            success = False

    if success:
        results = voter_merge_two_accounts_action(
            from_voter=from_voter,
            to_voter=to_voter,
            voter_merge_status=voter_merge_status,
        )
        status += results['status']
        if not results['success']:
            success = False

    if success:
        messages.add_message(
            request, messages.INFO, str(status)
        )
    else:
        messages.add_message(
            request, messages.ERROR,
            "VOTER_MERGE_ERROR: " + str(status)
        )

    return HttpResponseRedirect(reverse('voter:voter_list', args=()) + "?show_voter_merge_data=1")


def login_complete_view(request):
    try:
        voter_api_device_id = get_voter_api_device_id(request)
        if not positive_value_exists(voter_api_device_id):
            messages.add_message(request, messages.INFO, 'Missing voter_api_device_id.')
            return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

        voter_object = request.user
        if not voter_object:
            messages.add_message(request, messages.INFO, 'Missing voter.')
            return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

        # TODO Write the Twitter or Facebook information to the voter table so we can access it via the APIs
        # Currently all the twitter authentication for Django is in the separate social_auth* tables

        # Relink this voter_api_device_id to this Voter account
        voter_device_manager = VoterDeviceLinkManager()
        voter_device_link_results = voter_device_manager.retrieve_voter_device_link(voter_api_device_id)
        voter_device_link = voter_device_link_results['voter_device_link']

        update_voter_device_link_results = voter_device_manager.update_voter_device_link(
           voter_device_link, voter_object)
        if update_voter_device_link_results['voter_device_link_updated']:
            messages.add_message(request, messages.INFO, 'Voter updated.')
        else:
            messages.add_message(request, messages.INFO, 'Voter could not be relinked.')
    except Exception as e:
        messages.add_message(request, messages.INFO, 'Voter not updated:' + str(e))

    return HttpResponseRedirect(reverse('login_we_vote', args=()))


@login_required
def process_maintenance_status_flags_view(request):
    """
    Search for voters who haven't had a specific maintenance task done in blocks of X,
    and then execute those changes.
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    results = process_maintenance_status_flags()
    messages.add_message(
        request, messages.INFO,
        "Process maintenance status flags, "
        "voters_updated_task_one: " + str(results['voters_updated_task_one']) +
        ", voters_updated_task_two: " + str(results['voters_updated_task_two'])
    )

    return HttpResponseRedirect(reverse('voter:voter_list', args=()))


# This is open to anyone, and provides psql to update the database directly
def voter_authenticate_manually_view(request):
    messages_on_stage = get_messages(request)

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    store_new_voter_api_device_id_in_cookie = False
    if not positive_value_exists(voter_api_device_id):
        # Create a voter_device_id and voter in the database if one doesn't exist yet
        results = voter_setup(request)
        voter_api_device_id = results['voter_api_device_id']
        store_new_voter_api_device_id_in_cookie = results['store_new_voter_api_device_id_in_cookie']

    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    voter_id = convert_to_int(voter_id)
    voter_on_stage_found = False
    voter_on_stage = Voter()
    try:
        voter_on_stage = Voter.objects.get(id=voter_id)
        voter_on_stage_found = True
    except Voter.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Voter.DoesNotExist:
        # This is fine, we will display an error
        pass

    if voter_on_stage_found:
        set_this_voter_as_admin = "UPDATE voter_voter SET is_admin=True WHERE id={voter_id};".format(voter_id=voter_id)
        unset_this_voter_as_admin = "UPDATE voter_voter SET is_admin=False WHERE id={voter_id};".format(
            voter_id=voter_id)

        set_as_partner_organization = "UPDATE voter_voter SET is_partner_organization=True WHERE id={voter_id};" \
                                      "".format(voter_id=voter_id)
        unset_as_partner_organization = "UPDATE voter_voter SET is_partner_organization=False WHERE id={voter_id};" \
                                        "".format(voter_id=voter_id)

        set_as_political_data_manager = "UPDATE voter_voter SET is_political_data_manager=True WHERE id={voter_id};" \
                                        "".format(voter_id=voter_id)
        unset_as_political_data_manager = "UPDATE voter_voter SET is_political_data_manager=False " \
                                          "WHERE id={voter_id};" \
                                          "".format(voter_id=voter_id)

        set_as_political_data_viewer = "UPDATE voter_voter SET is_political_data_viewer=True WHERE id={voter_id};" \
                                       "".format(voter_id=voter_id)
        unset_as_political_data_viewer = "UPDATE voter_voter SET is_political_data_viewer=False WHERE id={voter_id};" \
                                         "".format(voter_id=voter_id)

        set_as_verified_volunteer = "UPDATE voter_voter SET is_verified_volunteer=True WHERE id={voter_id};" \
                                    "".format(voter_id=voter_id)
        unset_as_verified_volunteer = "UPDATE voter_voter SET is_verified_volunteer=False WHERE id={voter_id};" \
                                      "".format(voter_id=voter_id)
        template_values = {
            'messages_on_stage':                messages_on_stage,
            'voter':                            voter_on_stage,
            'voter_api_device_id':              voter_api_device_id,
            'is_authenticated':                 request.user.is_authenticated,
            'set_this_voter_as_admin':          set_this_voter_as_admin,
            'unset_this_voter_as_admin':        unset_this_voter_as_admin,
            'set_as_partner_organization':      set_as_partner_organization,
            'unset_as_partner_organization':    unset_as_partner_organization,
            'set_as_political_data_manager':    set_as_political_data_manager,
            'unset_as_political_data_manager':  unset_as_political_data_manager,
            'set_as_political_data_viewer':     set_as_political_data_viewer,
            'unset_as_political_data_viewer':   unset_as_political_data_viewer,
            'set_as_verified_volunteer':        set_as_verified_volunteer,
            'unset_as_verified_volunteer':      unset_as_verified_volunteer,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,

        }
    response = render(request, 'voter/voter_authenticate_manually.html', template_values)

    # We want to store the voter_api_device_id cookie if it is new
    # if positive_value_exists(voter_api_device_id) and positive_value_exists(store_new_voter_api_device_id_in_cookie):
    # DALE 2016-02-15 Always set if we have a voter_api_device_id
    if positive_value_exists(store_new_voter_api_device_id_in_cookie):
        set_voter_api_device_id(request, response, voter_api_device_id)

    return response


# This is open to anyone, and provides psql to update the database directly
def voter_authenticate_manually_process_view(request):
    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)

    voter_id = convert_to_int(voter_id)
    voter_signed_in = False
    try:
        voter_on_stage = Voter.objects.get(id=voter_id)
        # If the account associated with this voter_api_device_id is an admin, complete Django authentication
        if voter_on_stage.is_admin:
            voter_on_stage.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, voter_on_stage)
            messages.add_message(request, messages.INFO, 'Voter logged in.')
            voter_signed_in = True
        else:
            messages.add_message(request, messages.INFO, 'This account does not have Admin access.')
    except Voter.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
        messages.add_message(request, messages.ERROR, 'More than one voter found. Voter not logged in.')
    except Voter.DoesNotExist:
        # This is fine, we will display an error
        messages.add_message(request, messages.ERROR, 'Voter not found. Voter not logged in.')

    if voter_signed_in:
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))
    else:
        return HttpResponseRedirect(reverse('voter:authenticate_manually', args=()))



@login_required
def voter_delete_process_view(request):
    """
    Permanently delete a voter
    :param request:
    :return:
    """
    status = ""
    voter_id = convert_to_int(request.POST.get('voter_id', 0))
    confirm_delete = convert_to_int(request.POST.get('confirm_delete', 0))

    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'voter_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if not positive_value_exists(confirm_delete):
        messages.add_message(request, messages.ERROR,
                             'Unable to delete this voter. '
                             'Please check the checkbox to confirm you want to delete this voter permanently.')
        return HttpResponseRedirect(reverse('voter:voter_edit', args=(voter_id,)))

    # Check to see if this voter is already being used anywhere
    voter_on_stage_found = False
    try:
        voter_query = Voter.objects.filter(id=voter_id)
        if len(voter_query):
            voter_on_stage = voter_query[0]
            voter_on_stage_found = True
            results = delete_all_voter_information_permanently(
                voter_to_delete=voter_on_stage, user=request.user)
            status += results['status']
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    if voter_on_stage_found:
        messages.add_message(request, messages.INFO, 'Voter deleted.')
        messages.add_message(request, messages.INFO, 'status: ' + str(status))
    else:
        messages.add_message(request, messages.ERROR, 'Voter not found.')

    return HttpResponseRedirect(reverse('voter:voter_list', args=()))


@login_required
def voter_edit_process_view(request):
    """
    Process the new or edit voter forms
    :param request:
    :return:
    """
    status = ''
    voter_id = request.POST.get('voter_id', 0)
    voter_id = convert_to_int(voter_id)

    # We need to react if the photo is too big to upload
    try:
        voter_device_id = get_voter_device_id(request)  # We standardize how we take in the voter_device_id
    except RequestDataTooBig:
        messages.add_message(request, messages.ERROR, "Voter photo too big to upload.")

        return HttpResponseRedirect(reverse('voter:voter_edit', args=(voter_id,)))
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'voter_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # NOTE: create_twitter_link_to_voter is processed in voter_edit_view

    voter_on_stage = Voter()
    at_least_one_value_changed = False

    add_to_new_team = request.POST.get('add_to_new_team', False)
    email = request.POST.get('email', False)
    first_name = request.POST.get('first_name', False)
    last_name = request.POST.get('last_name', False)
    password_text = request.POST.get('password_text', False)
    profile_image_type_currently_active = request.POST.get('profile_image_type_currently_active', False)
    sms_phone_number = request.POST.get('sms_phone_number', False)
    team_name_new = request.POST.get('team_name_new', False)
    twitter_handle = request.POST.get('twitter_handle', False)
    try:
        voter_photo_file = request.FILES['voter_photo_file']
        voter_photo_file_found = True
    except Exception as e:
        voter_photo_file = None
        voter_photo_file_found = False
    voter_we_vote_id = None

    # Check to see if this voter is already being used anywhere
    voter_on_stage_found = False
    try:
        voter_query = Voter.objects.filter(id=voter_id)
        if len(voter_query):
            voter_on_stage = voter_query[0]
            voter_on_stage_found = True
            voter_we_vote_id = voter_on_stage.we_vote_id
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    email_already_belongs_to_other_voter = False
    email_needs_to_be_created = False
    error_with_email_retrieve = False
    if voter_on_stage_found:
        # Search for this email address in the EmailAddress table
        if positive_value_exists(email):
            try:
                email_belonging_to_other_voter = EmailAddress.objects.exclude(voter_we_vote_id=voter_we_vote_id).get(
                    normalized_email_address__iexact=email,
                    email_ownership_is_verified=True,
                    deleted=False,
                )
                email_already_belongs_to_other_voter = True
                messages.add_message(request, messages.ERROR,
                                     "Email address '{email}' already owned by another voter."
                                     "".format(email=email))
            except EmailAddress.DoesNotExist:
                pass
            except Exception as e:
                error_with_email_retrieve = True
                messages.add_message(request, messages.ERROR,
                                     "Error retrieving email address '{email}': {error}"
                                     "".format(email=email, error=e))

            if not positive_value_exists(email_already_belongs_to_other_voter) and not error_with_email_retrieve:
                # See if there is an EmailAddress for this voter and update the voter table
                try:
                    email_for_this_voter = EmailAddress.objects.get(
                        normalized_email_address__iexact=email,
                        voter_we_vote_id=voter_we_vote_id
                    )
                    if email_for_this_voter.deleted is True:
                        email_for_this_voter.deleted = False
                        email_for_this_voter.save()
                    # Update data in core voter record
                    voter_on_stage.email = email.lower()
                    voter_on_stage.primary_email_we_vote_id = email_for_this_voter.we_vote_id
                    voter_on_stage.email_ownership_is_verified = email_for_this_voter.email_ownership_is_verified
                    at_least_one_value_changed = True
                except EmailAddress.DoesNotExist:
                    email_needs_to_be_created = True
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         "Error retrieving email address for this voter '{email}': {error}"
                                         "".format(email=email, error=e))

                if email_needs_to_be_created:
                    email_manager = EmailManager()
                    email_results = email_manager.create_email_address(
                        normalized_email_address=email,
                        voter_we_vote_id=voter_we_vote_id,
                        email_ownership_is_verified=True)
                    if email_results['success'] and email_results['email_address_object_saved']:
                        # Update data in core voter record
                        email_for_this_voter = email_results['email_address_object']
                        voter_on_stage.email = email.lower()
                        voter_on_stage.primary_email_we_vote_id = email_for_this_voter.we_vote_id
                        voter_on_stage.email_ownership_is_verified = True
                        at_least_one_value_changed = True
        else:
            # If email is empty, wipe out existing email from voter record, but don't delete from EmailAddress table
            voter_on_stage.email = None
            voter_on_stage.email_ownership_is_verified = False
            voter_on_stage.primary_email_we_vote_id = None
            at_least_one_value_changed = True

        # ########################
        # Search for this sms phone number in the SMSPhoneNumber table
        error_with_sms_phone_number_retrieve = False
        sms_phone_number_already_belongs_to_other_voter = False
        sms_phone_number_needs_to_be_created = False
        if positive_value_exists(sms_phone_number):
            try:
                sms_phone_number_belonging_to_other_voter = \
                    SMSPhoneNumber.objects.exclude(voter_we_vote_id=voter_we_vote_id).get(
                        normalized_sms_phone_number__iexact=sms_phone_number,
                        sms_ownership_is_verified=True,
                        deleted=False,
                    )
                sms_phone_number_already_belongs_to_other_voter = True
                messages.add_message(request, messages.ERROR,
                                     "SMS Phone number '{sms_phone_number}' already owned by another voter."
                                     "".format(sms_phone_number=sms_phone_number))
            except SMSPhoneNumber.DoesNotExist:
                pass
            except Exception as e:
                error_with_sms_phone_number_retrieve = True
                messages.add_message(request, messages.ERROR,
                                     "Error retrieving SMS Phone number '{sms_phone_number}': {error}"
                                     "".format(sms_phone_number=sms_phone_number, error=e))

            if not positive_value_exists(sms_phone_number_already_belongs_to_other_voter) \
                    and not error_with_sms_phone_number_retrieve:
                # See if there is an SMSPhoneNumber for this voter and update the voter table
                try:
                    sms_phone_number_for_this_voter = SMSPhoneNumber.objects.get(
                        normalized_sms_phone_number__iexact=sms_phone_number,
                        voter_we_vote_id=voter_we_vote_id
                    )
                    if sms_phone_number_for_this_voter.deleted is True:
                        sms_phone_number_for_this_voter.deleted = False
                        sms_phone_number_for_this_voter.save()
                    # Update data in core voter record
                    voter_on_stage.normalized_sms_phone_number = \
                        sms_phone_number_for_this_voter.normalized_sms_phone_number
                    voter_on_stage.primary_sms_we_vote_id = sms_phone_number_for_this_voter.we_vote_id
                    voter_on_stage.sms_ownership_is_verified = sms_phone_number_for_this_voter.sms_ownership_is_verified
                    at_least_one_value_changed = True
                except SMSPhoneNumber.DoesNotExist:
                    sms_phone_number_needs_to_be_created = True
                except Exception as e:
                    messages.add_message(request, messages.ERROR,
                                         "Error retrieving phone number for this voter '{sms_phone_number}': {error}"
                                         "".format(sms_phone_number=sms_phone_number, error=e))

                if sms_phone_number_needs_to_be_created:
                    sms_manager = SMSManager()
                    sms_results = sms_manager.create_sms_phone_number(
                        normalized_sms_phone_number=sms_phone_number,
                        voter_we_vote_id=voter_we_vote_id,
                        sms_ownership_is_verified=True)
                    if sms_results['success'] and sms_results['sms_phone_number_saved']:
                        # Update data in core voter record
                        sms_phone_number_for_this_voter = sms_results['sms_phone_number']
                        voter_on_stage.normalized_sms_phone_number = \
                            sms_phone_number_for_this_voter.normalized_sms_phone_number
                        voter_on_stage.primary_sms_we_vote_id = sms_phone_number_for_this_voter.we_vote_id
                        voter_on_stage.sms_ownership_is_verified = True
                        at_least_one_value_changed = True
        else:
            # If phone number is empty, wipe out from voter record, but don't delete from SMSPhoneNumber
            voter_on_stage.normalized_sms_phone_number = None
            voter_on_stage.primary_sms_we_vote_id = None
            voter_on_stage.sms_ownership_is_verified = False
            at_least_one_value_changed = True

        # Process incoming photo if there is one
        voter_photo_in_binary_format = None
        voter_photo_converted_to_binary = False
        if voter_photo_file_found:
            try:
                voter_photo_in_binary_format = b64encode(voter_photo_file.read()).decode('utf-8')
                voter_photo_converted_to_binary = True
            except Exception as e:
                messages.add_message(request, messages.ERROR,
                                     "Error converting voter photo to binary: {error}".format(error=e))
        if voter_photo_file_found and voter_photo_converted_to_binary:
            photo_results = voter_save_photo_from_file_reader(
                voter_we_vote_id=voter_we_vote_id,
                voter_photo_binary_file=voter_photo_in_binary_format)
            if photo_results['we_vote_hosted_voter_photo_original_url']:
                we_vote_hosted_voter_photo_original_url = photo_results['we_vote_hosted_voter_photo_original_url']
                # Now we want to resize to a large version
                create_resized_image_results = create_resized_images(
                    voter_we_vote_id=voter_we_vote_id,
                    voter_uploaded_profile_image_url_https=we_vote_hosted_voter_photo_original_url)
                voter_on_stage.we_vote_hosted_profile_uploaded_image_url_large = \
                    create_resized_image_results['cached_resized_image_url_large']
                voter_on_stage.we_vote_hosted_profile_uploaded_image_url_medium = \
                    create_resized_image_results['cached_resized_image_url_medium']
                voter_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny = \
                    create_resized_image_results['cached_resized_image_url_tiny']
                at_least_one_value_changed = True

        if profile_image_type_currently_active is not False:
            if profile_image_type_currently_active in [
                    PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN,
                    PROFILE_IMAGE_TYPE_UPLOADED]:
                at_least_one_value_changed = True
                voter_on_stage.profile_image_type_currently_active = profile_image_type_currently_active
                if profile_image_type_currently_active == PROFILE_IMAGE_TYPE_FACEBOOK:
                    voter_on_stage.we_vote_hosted_profile_image_url_large = \
                        voter_on_stage.we_vote_hosted_profile_facebook_image_url_large
                    voter_on_stage.we_vote_hosted_profile_image_url_medium = \
                        voter_on_stage.we_vote_hosted_profile_facebook_image_url_medium
                    voter_on_stage.we_vote_hosted_profile_image_url_tiny = \
                        voter_on_stage.we_vote_hosted_profile_facebook_image_url_tiny
                elif profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
                    voter_on_stage.we_vote_hosted_profile_image_url_large = \
                        voter_on_stage.we_vote_hosted_profile_twitter_image_url_large
                    voter_on_stage.we_vote_hosted_profile_image_url_medium = \
                        voter_on_stage.we_vote_hosted_profile_twitter_image_url_medium
                    voter_on_stage.we_vote_hosted_profile_image_url_tiny = \
                        voter_on_stage.we_vote_hosted_profile_twitter_image_url_tiny
                elif profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UPLOADED:
                    voter_on_stage.we_vote_hosted_profile_image_url_large = \
                        voter_on_stage.we_vote_hosted_profile_uploaded_image_url_large
                    voter_on_stage.we_vote_hosted_profile_image_url_medium = \
                        voter_on_stage.we_vote_hosted_profile_uploaded_image_url_medium
                    voter_on_stage.we_vote_hosted_profile_image_url_tiny = \
                        voter_on_stage.we_vote_hosted_profile_uploaded_image_url_tiny

        try:
            # Update existing voter
            if first_name is not False:
                voter_on_stage.first_name = first_name
                at_least_one_value_changed = True
            if last_name is not False:
                voter_on_stage.last_name = last_name
                at_least_one_value_changed = True
            if twitter_handle is not False:
                voter_on_stage.twitter_screen_name = twitter_handle
                at_least_one_value_changed = True
            if password_text is not False:
                if len(password_text) == 0:
                    pass
                elif len(password_text) > 5:
                    voter_on_stage.set_password(password_text)
                    at_least_one_value_changed = True
                else:
                    messages.add_message(request, messages.ERROR, 'The password must be 6 digits or more.')

            if at_least_one_value_changed:
                voter_on_stage.save()

            if password_text:
                # Check to see if a login has already been created
                pass
            messages.add_message(request, messages.INFO, 'Voter information updated.')
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR, 'Could not save voter: {error}'.format(error=e))

        # ##################################
        # Deleting or editing a CampaignXSupporter
        if positive_value_exists(voter_we_vote_id):
            from campaign.models import CampaignXSupporter
            supporters_query = CampaignXSupporter.objects.all()
            supporters_query = supporters_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            supporters_list = list(supporters_query)
            update_campaignx_supporter_count = False
            from campaign.views_admin import deleting_or_editing_campaignx_supporter_list
            results = deleting_or_editing_campaignx_supporter_list(
                request=request,
                supporters_list=supporters_list,
            )
            # TODO: Update campaignx_supporter_count
            update_campaignx_supporter_count = update_campaignx_supporter_count or \
                results['update_campaignx_supporter_count']
            update_message = results['update_message']
            if positive_value_exists(update_message):
                messages.add_message(request, messages.INFO, update_message)
    else:
        try:
            # Create new
            voter_on_stage = Voter.objects.create_user(email, email, password_text)

            # Update new voter
            if first_name is not False:
                voter_on_stage.first_name = first_name
                at_least_one_value_changed = True
            if last_name is not False:
                voter_on_stage.last_name = last_name
                at_least_one_value_changed = True
            if twitter_handle is not False:
                voter_on_stage.twitter_screen_name = twitter_handle
                at_least_one_value_changed = True
            if email is not False:
                voter_on_stage.email = email
                at_least_one_value_changed = True

            if at_least_one_value_changed:
                voter_on_stage.save()

            messages.add_message(request, messages.INFO, 'Added new Voter.')
        except Exception as e:
            messages.add_message(request, messages.ERROR, 'Could not save voter:' + str(e))

    # ##########################################################################
    # Update volunteer teams this voter is a member of
    volunteer_team_success = True
    team_name = ''
    team_we_vote_id = ''
    if positive_value_exists(team_name_new):
        volunteer_team_found = False
        try:
            volunteer_team = VolunteerTeam.objects.using('readonly').get(team_name__iexact=team_name_new)
            volunteer_team_found = True
            team_name = volunteer_team.team_name
            team_we_vote_id = volunteer_team.we_vote_id
        except VolunteerTeam.DoesNotExist:
            volunteer_team_found = False
        except Exception as e:
            message = "COULD_NOT_RETRIEVE_EXISTING_VOLUNTEER_TEAM: " + str(e) + " "
            messages.add_message(request, messages.ERROR, message)
            volunteer_team_success = False

        if volunteer_team_success and not positive_value_exists(volunteer_team_found):
            try:
                volunteer_team = VolunteerTeam.objects.create(team_name=team_name_new)
                team_name = volunteer_team.team_name
                team_we_vote_id = volunteer_team.we_vote_id
                volunteer_team_found = True
                message = "Successfully created {team_name}. ".format(team_name=team_name)
                messages.add_message(request, messages.INFO, message)
            except Exception as e:
                message = "COULD_NOT_CREATE_VOLUNTEER_TEAM: " + str(e) + " "
                messages.add_message(request, messages.ERROR, message)

        if positive_value_exists(volunteer_team_found) and positive_value_exists(add_to_new_team):
            if not positive_value_exists(voter_we_vote_id) or not positive_value_exists(team_we_vote_id):
                message = \
                    "MISSING_REQUIRED_TEAM_MEMBER_VARIABLE:"\
                    " team_we_vote_id: {team_we_vote_id}."\
                    " voter_we_vote_id: {voter_we_vote_id}.".format(
                        team_we_vote_id=team_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                messages.add_message(request, messages.ERROR, message)
            else:
                try:
                    defaults = {
                        'team_we_vote_id': team_we_vote_id,
                        'voter_we_vote_id': voter_we_vote_id,
                    }
                    volunteer_team_member, volunteer_team_member_created = \
                        VolunteerTeamMember.objects.update_or_create(
                            team_we_vote_id=team_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            defaults=defaults,
                        )
                    if volunteer_team_member_created:
                        message = \
                            "Successfully added {voter_we_vote_id} to {team_name}. ".format(
                                team_name=team_name,
                                voter_we_vote_id=voter_we_vote_id)
                    else:
                        message = \
                            "{voter_we_vote_id} is already a member of {team_name}. ".format(
                                team_name=team_name,
                                voter_we_vote_id=voter_we_vote_id)
                    messages.add_message(request, messages.INFO, message)
                except Exception as e:
                    message = "COULD_NOT_ADD_TEAM_MEMBER: " + str(e) + " "
                    messages.add_message(request, messages.ERROR, message)

    # ##########################################################################
    # Now delete or add this voter from/to one of the teams
    volunteer_team_list = []
    try:
        queryset = VolunteerTeam.objects.using('readonly').all()
        volunteer_team_list = list(queryset)
    except Exception as e:
        message = "COULD_NOT_GET_VOLUNTEER_TEAM_LIST2: " + str(e) + " "
        messages.add_message(request, messages.ERROR, message)

    for volunteer_team in volunteer_team_list:
        # Delete this voter from the team
        delete_variable_name = "delete_volunteer_team_member_" + str(volunteer_team.id)
        delete_voter_from_team = positive_value_exists(request.POST.get(delete_variable_name, False))
        if positive_value_exists(delete_voter_from_team):
            team_name = volunteer_team.team_name
            team_we_vote_id = volunteer_team.we_vote_id
            if positive_value_exists(team_we_vote_id) and positive_value_exists(voter_we_vote_id):
                try:
                    number_deleted, details = VolunteerTeamMember.objects.using('readonly') \
                        .filter(
                            team_we_vote_id__iexact=team_we_vote_id,
                            voter_we_vote_id__iexact=voter_we_vote_id,
                        ) \
                        .delete()
                    messages.add_message(request, messages.INFO,
                                         "Deleted VolunteerTeamMember ({number_deleted})."
                                         .format(number_deleted=number_deleted))
                except Exception as e:
                    messages.add_message(request, messages.ERROR, 'Could not delete team membership: ' + str(e))
            else:
                messages.add_message(request, messages.ERROR, 'Could not delete team membership.')
        # Add this voter to the team
        add_variable_name = "add_volunteer_team_member_" + str(volunteer_team.id)
        add_voter_to_team = positive_value_exists(request.POST.get(add_variable_name, False))
        if positive_value_exists(add_voter_to_team):
            team_name = volunteer_team.team_name
            team_we_vote_id = volunteer_team.we_vote_id
            if positive_value_exists(team_we_vote_id) and positive_value_exists(voter_we_vote_id):
                try:
                    defaults = {
                        'team_we_vote_id': team_we_vote_id,
                        'voter_we_vote_id': voter_we_vote_id,
                    }
                    volunteer_team_member, volunteer_team_member_created = \
                        VolunteerTeamMember.objects.update_or_create(
                            team_we_vote_id=team_we_vote_id,
                            voter_we_vote_id=voter_we_vote_id,
                            defaults=defaults,
                        )
                    if volunteer_team_member_created:
                        message = \
                            "Successfully added {voter_we_vote_id} to {team_name}. ".format(
                                team_name=team_name,
                                voter_we_vote_id=voter_we_vote_id)
                    else:
                        message = \
                            "{voter_we_vote_id} is already a member of {team_name}. ".format(
                                team_name=team_name,
                                voter_we_vote_id=voter_we_vote_id)
                    messages.add_message(request, messages.INFO, message)
                except Exception as e:
                    messages.add_message(request, messages.ERROR, 'Could not delete team membership: ' + str(e))
            else:
                messages.add_message(request, messages.ERROR, 'Could not delete team membership.')

    return HttpResponseRedirect(reverse('voter:voter_edit', args=(voter_id,)) +
                                "?voter_invitation_password=" + password_text)


def generate_proposed_password():
    # For the create new voter account form, create a proposed default password
    return generate_random_string(
        string_length=8,
        chars=string.ascii_uppercase + string.digits + "!*$",
        remove_confusing_digits=True
    )

@login_required
def voter_edit_view(request, voter_id=0, voter_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'voter_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    create_facebook_link_to_voter = request.GET.get('create_facebook_link_to_voter', False)
    create_organization_for_voter = request.GET.get('create_organization_for_voter', False)
    create_twitter_link_to_voter = request.GET.get('create_twitter_link_to_voter', False)
    cross_link_all_voter_positions = request.GET.get('cross_link_all_voter_positions', False)
    merge_duplicate_positions = request.GET.get('merge_duplicate_positions', False)
    voter_invitation_password = request.GET.get('voter_invitation_password', '')

    voter_id = convert_to_int(voter_id)
    voter_on_stage = Voter()
    voter_on_stage_found = False
    facebook_id_from_link_to_voter = 0
    facebook_id_from_link_to_voter_for_another_voter = False
    twitter_id_from_link_to_voter = 0
    twitter_id_from_link_to_voter_for_another_voter = False
    positions_cross_linked = 0
    positions_not_cross_linked = 0
    status_print_list = ""
    facebook_manager = FacebookManager()
    organization_manager = OrganizationManager()
    twitter_user_manager = TwitterUserManager()
    try:
        if positive_value_exists(voter_id):
            voter_on_stage = Voter.objects.get(id=voter_id)
        elif positive_value_exists(voter_we_vote_id):
            voter_on_stage = Voter.objects.get(we_vote_id=voter_we_vote_id)
        voter_on_stage_found = True
        voter_we_vote_id = voter_on_stage.we_vote_id
    except Voter.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Voter.DoesNotExist:
        # This is fine
        pass

    if voter_on_stage_found:
        # Get FacebookLinkToVoter
        try:
            facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                voter_we_vote_id__iexact=voter_on_stage.we_vote_id)
            if positive_value_exists(facebook_link_to_voter.facebook_user_id):
                facebook_id_from_link_to_voter = facebook_link_to_voter.facebook_user_id
                voter_on_stage.facebook_id_from_link_to_voter = facebook_link_to_voter.facebook_user_id
        except FacebookLinkToVoter.DoesNotExist:
            pass

        # Get TwitterLinkToVoter
        try:
            twitter_link_to_voter = TwitterLinkToVoter.objects.get(
                voter_we_vote_id__iexact=voter_on_stage.we_vote_id)
            if positive_value_exists(twitter_link_to_voter.twitter_id):
                twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                voter_on_stage.twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                # We reach out for the twitter_screen_name
                voter_on_stage.twitter_screen_name_from_link_to_voter = \
                    twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
        except TwitterLinkToVoter.DoesNotExist:
            pass

        # Get TwitterLinkToOrganization
        try:
            if positive_value_exists(twitter_id_from_link_to_voter):
                twitter_id_to_search = twitter_id_from_link_to_voter
                twitter_link_to_organization_twitter_id_source_text = "FROM TW_LINK_TO_VOTER"
            else:
                twitter_id_to_search = voter_on_stage.twitter_id
                twitter_link_to_organization_twitter_id_source_text = "FROM VOTER RECORD"

            if positive_value_exists(twitter_id_to_search):
                twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                    twitter_id=twitter_id_to_search)
                if positive_value_exists(twitter_link_to_organization.twitter_id):
                    voter_on_stage.organization_we_vote_id_from_link_to_organization = \
                        twitter_link_to_organization.organization_we_vote_id
                    voter_on_stage.twitter_id_from_link_to_organization = twitter_link_to_organization.twitter_id
                    # We reach out for the twitter_screen_name
                    voter_on_stage.twitter_screen_name_from_link_to_organization = \
                        twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()
                    voter_on_stage.twitter_link_to_organization_twitter_id_source_text = \
                        twitter_link_to_organization_twitter_id_source_text
        except TwitterLinkToOrganization.DoesNotExist:
            pass

        # ########################################
        # Looks for other voters that have the same Facebook data
        at_least_one_voter_facebook_value_found = False
        voter_facebook_filters = []
        if positive_value_exists(voter_on_stage.facebook_id):
            new_filter = Q(facebook_id=voter_on_stage.facebook_id)
            voter_facebook_filters.append(new_filter)
            at_least_one_voter_facebook_value_found = True

        voter_list_duplicate_facebook_updated = []
        if at_least_one_voter_facebook_value_found:
            voter_list_duplicate_facebook = Voter.objects.all()
            # Add the first query
            final_filters = []
            if len(voter_facebook_filters):
                final_filters = voter_facebook_filters.pop()

                # ...and "OR" the remaining items in the list
                for item in voter_facebook_filters:
                    final_filters |= item

            voter_list_duplicate_facebook = voter_list_duplicate_facebook.filter(final_filters)
            voter_list_duplicate_facebook = voter_list_duplicate_facebook.exclude(id=voter_on_stage.id)
            voter_list_duplicate_facebook = voter_list_duplicate_facebook[:100]

            for one_duplicate_voter in voter_list_duplicate_facebook:
                try:
                    facebook_link_to_another_voter = FacebookLinkToVoter.objects.get(
                        voter_we_vote_id__iexact=one_duplicate_voter.we_vote_id)
                    if positive_value_exists(facebook_link_to_another_voter.facebook_user_id):
                        facebook_id_from_link_to_voter_for_another_voter = True
                        one_duplicate_voter.facebook_id_from_link_to_voter = \
                            facebook_link_to_another_voter.facebook_user_id
                except FacebookLinkToVoter.DoesNotExist:
                    pass

                voter_list_duplicate_facebook_updated.append(one_duplicate_voter)
            list(voter_list_duplicate_facebook_updated)

        # ########################################
        # Looks for voters that have the same Twitter data
        at_least_one_voter_twitter_value_found = False
        voter_twitter_filters = []
        if positive_value_exists(voter_on_stage.twitter_id):
            new_filter = Q(twitter_id=voter_on_stage.twitter_id)
            voter_twitter_filters.append(new_filter)
            at_least_one_voter_twitter_value_found = True
        if positive_value_exists(voter_on_stage.twitter_screen_name):
            new_filter = Q(twitter_screen_name__iexact=voter_on_stage.twitter_screen_name)
            voter_twitter_filters.append(new_filter)
            at_least_one_voter_twitter_value_found = True

        voter_list_duplicate_twitter_updated = []
        if at_least_one_voter_twitter_value_found:
            voter_list_duplicate_twitter = Voter.objects.all()
            # Add the first query
            final_filters = []
            if len(voter_twitter_filters):
                final_filters = voter_twitter_filters.pop()

                # ...and "OR" the remaining items in the list
                for item in voter_twitter_filters:
                    final_filters |= item

            voter_list_duplicate_twitter = voter_list_duplicate_twitter.filter(final_filters)
            voter_list_duplicate_twitter = voter_list_duplicate_twitter.exclude(id=voter_on_stage.id)
            voter_list_duplicate_twitter = voter_list_duplicate_twitter[:100]

            for one_duplicate_voter in voter_list_duplicate_twitter:
                try:
                    twitter_link_to_another_voter = TwitterLinkToVoter.objects.get(
                        voter_we_vote_id__iexact=one_duplicate_voter.we_vote_id)
                    if positive_value_exists(twitter_link_to_another_voter.twitter_id):
                        twitter_id_from_link_to_voter_for_another_voter = True
                        one_duplicate_voter.twitter_id_from_link_to_voter = twitter_link_to_another_voter.twitter_id
                        # We reach out for the twitter_screen_name
                        one_duplicate_voter.twitter_screen_name_from_link_to_voter = \
                            twitter_link_to_another_voter.fetch_twitter_handle_locally_or_remotely()
                except TwitterLinkToVoter.DoesNotExist:
                    pass

                voter_list_duplicate_twitter_updated.append(one_duplicate_voter)
            list(voter_list_duplicate_twitter_updated)

        # ########################################
        # Looks for orgs that have the same Twitter data
        # (excluding the org connected by linked_organization_we_vote_id)
        org_twitter_filters = []
        at_least_one_twitter_value_found = False
        if positive_value_exists(voter_on_stage.twitter_id):
            new_filter = Q(twitter_user_id=voter_on_stage.twitter_id)
            org_twitter_filters.append(new_filter)
            at_least_one_twitter_value_found = True
        if positive_value_exists(voter_on_stage.twitter_screen_name):
            new_filter = Q(organization_twitter_handle__iexact=voter_on_stage.twitter_screen_name)
            org_twitter_filters.append(new_filter)
            at_least_one_twitter_value_found = True

        organization_list_with_duplicate_twitter_updated = []
        final_filters = []
        if at_least_one_twitter_value_found:
            # Add the first query
            if len(org_twitter_filters):
                final_filters = org_twitter_filters.pop()

                # ...and "OR" the remaining items in the list
                for item in org_twitter_filters:
                    final_filters |= item

            organization_list_with_duplicate_twitter = Organization.objects.all()
            organization_list_with_duplicate_twitter = organization_list_with_duplicate_twitter.filter(final_filters)
            organization_list_with_duplicate_twitter = organization_list_with_duplicate_twitter.exclude(
                we_vote_id=voter_on_stage.linked_organization_we_vote_id)

            for one_duplicate_organization in organization_list_with_duplicate_twitter:
                try:
                    linked_voter = Voter.objects.get(
                        linked_organization_we_vote_id__iexact=one_duplicate_organization.we_vote_id)
                    one_duplicate_organization.linked_voter = linked_voter
                except Voter.DoesNotExist:
                    pass

                organization_list_with_duplicate_twitter_updated.append(one_duplicate_organization)

        # ####################################
        # Find the voter that has this organization as their linked_organization_we_vote_id
        linked_organization_we_vote_id_list_updated = []
        linked_organization_we_vote_id_list = Organization.objects.all()
        linked_organization_we_vote_id_list = linked_organization_we_vote_id_list.filter(
            we_vote_id__iexact=voter_on_stage.linked_organization_we_vote_id)

        linked_organization_found = False
        for one_linked_organization in linked_organization_we_vote_id_list:
            try:
                linked_voter = Voter.objects.get(
                    linked_organization_we_vote_id__iexact=one_linked_organization.we_vote_id)
                one_linked_organization.linked_voter = linked_voter
                linked_organization_found = True
            except Voter.DoesNotExist:
                linked_organization_found = False
                pass

            linked_organization_we_vote_id_list_updated.append(one_linked_organization)

        # Search for all email addresses tied to this voter
        email_addresses_query = EmailAddress.objects.filter(
            voter_we_vote_id=voter_we_vote_id,
        )
        email_addresses_list = list(email_addresses_query)

        # Search for all phone numbers tied to this voter
        sms_phone_numbers_query = SMSPhoneNumber.objects.filter(
            voter_we_vote_id=voter_we_vote_id,
        )
        sms_phone_numbers_list = list(sms_phone_numbers_query)

        # Do some checks on all the public positions owned by this voter
        position_filters = []
        new_filter = Q(voter_we_vote_id__iexact=voter_on_stage.we_vote_id)
        position_filters.append(new_filter)
        if positive_value_exists(voter_on_stage.linked_organization_we_vote_id):
            new_filter = Q(organization_we_vote_id__iexact=voter_on_stage.linked_organization_we_vote_id)
            position_filters.append(new_filter)

        final_position_filters = []
        if len(position_filters):
            final_position_filters = position_filters.pop()

            # ...and "OR" the remaining items in the list
            for item in position_filters:
                final_position_filters |= item

        # PositionEntered
        public_positions_owned_by_this_voter = PositionEntered.objects.all()
        public_positions_owned_by_this_voter = public_positions_owned_by_this_voter.filter(final_position_filters)

        if merge_duplicate_positions:
            public_positions_owned_by_this_voter = \
                merge_duplicate_positions_for_voter(public_positions_owned_by_this_voter)

        # PositionForFriends
        positions_for_friends_owned_by_this_voter = PositionForFriends.objects.all()
        positions_for_friends_owned_by_this_voter = \
            positions_for_friends_owned_by_this_voter.filter(final_position_filters)

        if merge_duplicate_positions:
            positions_for_friends_owned_by_this_voter = \
                merge_duplicate_positions_for_voter(positions_for_friends_owned_by_this_voter)

        if cross_link_all_voter_positions and voter_on_stage.linked_organization_we_vote_id \
                and not twitter_id_from_link_to_voter_for_another_voter:
            linked_organization_id = \
                organization_manager.fetch_organization_id(voter_on_stage.linked_organization_we_vote_id)
            if positive_value_exists(linked_organization_id):
                for one_public_position in public_positions_owned_by_this_voter:
                    voter_info_saved = False
                    voter_info_not_saved = False
                    organization_info_saved = False
                    organization_info_not_saved = False
                    # Update the voter information
                    try:
                        one_public_position.voter_id = voter_on_stage.id
                        one_public_position.voter_we_vote_id = voter_on_stage.we_vote_id
                        one_public_position.save()
                        voter_info_saved = True
                    except Exception as e:
                        voter_info_not_saved = True
                    # Update the organization information
                    try:
                        one_public_position.organization_id = linked_organization_id
                        one_public_position.organization_we_vote_id = voter_on_stage.linked_organization_we_vote_id
                        one_public_position.save()
                        organization_info_saved = True
                    except Exception as e:
                        organization_info_not_saved = True

                    if voter_info_saved or organization_info_saved:
                        positions_cross_linked += 1
                    if voter_info_not_saved or organization_info_not_saved:
                        positions_not_cross_linked += 1

                for one_position_for_friends in positions_for_friends_owned_by_this_voter:
                    voter_info_saved = False
                    voter_info_not_saved = False
                    organization_info_saved = False
                    organization_info_not_saved = False
                    # Update the voter information
                    try:
                        one_position_for_friends.voter_id = voter_on_stage.id
                        one_position_for_friends.voter_we_vote_id = voter_on_stage.we_vote_id
                        one_position_for_friends.save()
                        voter_info_saved = True
                    except Exception as e:
                        voter_info_not_saved = True
                    # Update the organization information
                    try:
                        one_position_for_friends.organization_id = linked_organization_id
                        one_position_for_friends.organization_we_vote_id = voter_on_stage.linked_organization_we_vote_id
                        one_position_for_friends.save()
                        organization_info_saved = True
                    except Exception as e:
                        organization_info_not_saved = True

                    if voter_info_saved or organization_info_saved:
                        positions_cross_linked += 1
                    if voter_info_not_saved or organization_info_not_saved:
                        positions_not_cross_linked += 1

        if create_facebook_link_to_voter:
            if not facebook_id_from_link_to_voter \
                    and not facebook_id_from_link_to_voter_for_another_voter:
                # If here, we want to create a TwitterLinkToVoter
                create_results = facebook_manager.create_facebook_link_to_voter(voter_on_stage.facebook_id,
                                                                                voter_on_stage.we_vote_id)
                messages.add_message(request, messages.INFO, 'FacebookLinkToVoter created:' +
                                     " " + create_results['status'])
                if positive_value_exists(create_results['facebook_link_to_voter_saved']):
                    facebook_link_to_voter = create_results['facebook_link_to_voter']
                    if positive_value_exists(facebook_link_to_voter.facebook_user_id):
                        voter_on_stage.facebook_id_from_link_to_voter = facebook_link_to_voter.facebook_user_id
            else:
                if facebook_id_from_link_to_voter:
                    messages.add_message(request, messages.ERROR, 'FacebookLinkToVoter could not be created: '
                                         'There is already a FacebookLinkToVoter for this voter.')
                if facebook_id_from_link_to_voter_for_another_voter:
                    messages.add_message(request, messages.ERROR,
                                         'FacebookLinkToVoter could not be created: '
                                         'There is already a FacebookLinkToVoter for ANOTHER voter.')

        if create_twitter_link_to_voter:
            if not twitter_id_from_link_to_voter \
                    and not twitter_id_from_link_to_voter_for_another_voter:
                # If here, we want to create a TwitterLinkToVoter
                create_results = twitter_user_manager.create_twitter_link_to_voter(voter_on_stage.twitter_id,
                                                                                   voter_on_stage.we_vote_id)
                messages.add_message(request, messages.INFO, 'TwitterLinkToVoter created:' +
                                     " " + create_results['status'])
                if positive_value_exists(create_results['twitter_link_to_voter_saved']):
                    twitter_link_to_voter = create_results['twitter_link_to_voter']
                    if positive_value_exists(twitter_link_to_voter.twitter_id):
                        voter_on_stage.twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                        # We reach out for the twitter_screen_name
                        voter_on_stage.twitter_screen_name_from_link_to_voter = \
                            twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
            else:
                if twitter_id_from_link_to_voter:
                    messages.add_message(request, messages.ERROR, 'TwitterLinkToVoter could not be created: '
                                         'There is already a TwitterLinkToVoter for this voter.')
                if twitter_id_from_link_to_voter_for_another_voter:
                    messages.add_message(request, messages.ERROR,
                                         'TwitterLinkToVoter could not be created: '
                                         'There is already a TwitterLinkToVoter for ANOTHER voter.')

        if create_organization_for_voter:
            do_not_create_organization = linked_organization_found
            if do_not_create_organization:
                do_not_create_organization_message = "Endorser could not be created. "
                if linked_organization_found:
                    do_not_create_organization_message += "Linked organization found. "

                messages.add_message(request, messages.ERROR, do_not_create_organization_message)
            else:
                create_results = organization_manager.create_organization(
                    organization_name=voter_on_stage.get_full_name(),
                    organization_image=voter_on_stage.voter_photo_url(),
                    organization_type=INDIVIDUAL,
                    we_vote_hosted_profile_image_url_large=voter_on_stage.we_vote_hosted_profile_image_url_large,
                    we_vote_hosted_profile_image_url_medium=voter_on_stage.we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=voter_on_stage.we_vote_hosted_profile_image_url_tiny
                )
                if create_results['organization_created']:
                    organization = create_results['organization']
                    try:
                        voter_on_stage.linked_organization_we_vote_id = organization.we_vote_id
                        voter_on_stage.save()
                        status_print_list += "Endorser created.<br />"

                        if twitter_id_from_link_to_voter:
                            results = twitter_user_manager.create_twitter_link_to_organization(
                                twitter_id_from_link_to_voter, organization.we_vote_id)
                            if results['twitter_link_to_organization_saved']:
                                twitter_link_to_organization = results['twitter_link_to_organization']

                    except Exception as e:
                        messages.add_message(request, messages.ERROR,
                                             "Could not update voter.linked_organization_we_vote_id.")
                else:
                    messages.add_message(request, messages.ERROR, "Could not create organization.")

        if positive_value_exists(positions_cross_linked):
            status_print_list += "positions_cross_linked: " + str(positions_cross_linked) + "<br />"
        if positive_value_exists(positions_not_cross_linked):
            status_print_list += "positions_not_cross_linked: " + str(positions_not_cross_linked) + "<br />"

        # ##########################################################################
        # Show all of the campaigns which this voter supports
        supporters_list = []
        if positive_value_exists(voter_we_vote_id):
            from campaign.models import CampaignXSupporter
            supporters_query = CampaignXSupporter.objects.all()
            supporters_query = supporters_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            # if positive_value_exists(only_show_supporters_with_endorsements):
            #     supporters_query = supporters_query.exclude(
            #         Q(supporter_endorsement__isnull=True) |
            #         Q(supporter_endorsement__exact='')
            #     )
            supporters_query = supporters_query.order_by('-date_supported')
            # Limit to only showing 200 on screen
            show_all = request.GET.get('show_all', False)
            show_more = request.GET.get('show_more', False)
            if positive_value_exists(show_more):
                supporters_list = supporters_query[:1000]
            elif positive_value_exists(show_all):
                supporters_list = supporters_query
            else:
                supporters_list = supporters_query[:200]
            # Now augment with campaign data
            campaignx_we_vote_id_list = []
            campaigns_by_we_vote_id_dict = {}
            for supporter in supporters_list:
                if supporter.campaignx_we_vote_id not in campaignx_we_vote_id_list:
                    campaignx_we_vote_id_list.append(supporter.campaignx_we_vote_id)
            if len(campaignx_we_vote_id_list) > 0:
                # Augment with
                from campaign.models import CampaignX
                queryset = CampaignX.objects.filter(we_vote_id__in=campaignx_we_vote_id_list)
                campaign_list = list(queryset)
                for campaign in campaign_list:
                    try:
                        campaigns_by_we_vote_id_dict[campaign.we_vote_id] = campaign
                    except Exception as e:
                        pass
                modified_supporters_list = []
                for supporter in supporters_list:
                    if hasattr(supporter, 'campaignx_we_vote_id'):
                        if supporter.campaignx_we_vote_id in campaigns_by_we_vote_id_dict:
                            one_campaign = campaigns_by_we_vote_id_dict[supporter.campaignx_we_vote_id]
                            if hasattr(one_campaign, 'campaign_title'):
                                supporter.campaignx = campaigns_by_we_vote_id_dict.get(supporter.campaignx_we_vote_id)
                        modified_supporters_list.append(supporter)
                supporters_list = modified_supporters_list

        volunteer_team_member_dict = {}
        try:
            queryset = VolunteerTeamMember.objects.using('readonly').all()\
                .filter(voter_we_vote_id__iexact=voter_we_vote_id)
            volunteer_team_membership_list = list(queryset)
            if len(volunteer_team_membership_list) > 0:
                for volunteer_team_member in volunteer_team_membership_list:
                    if volunteer_team_member.team_we_vote_id not in volunteer_team_member_dict:
                        volunteer_team_member_dict[volunteer_team_member.team_we_vote_id] = True
        except Exception as e:
            message = "COULD_NOT_GET_VOLUNTEER_TEAM_MEMBER_LIST: " + str(e) + " "
            messages.add_message(request, messages.ERROR, message)

        volunteer_team_list = []
        try:
            queryset = VolunteerTeam.objects.using('readonly').all().order_by('team_name')
            volunteer_team_list = list(queryset)
            if len(volunteer_team_list) > 0:
                volunteer_team_list_modified = []
                for volunteer_team in volunteer_team_list:
                    volunteer_team.is_voter_member = (volunteer_team.we_vote_id in volunteer_team_member_dict)
                    volunteer_team_list_modified.append(volunteer_team)
                volunteer_team_list = volunteer_team_list_modified
        except Exception as e:
            message = "COULD_NOT_GET_VOLUNTEER_TEAM_LIST: " + str(e) + " "
            messages.add_message(request, messages.ERROR, message)

        messages.add_message(request, messages.INFO, status_print_list)

        messages_on_stage = get_messages(request)

        template_values = {
            'email_addresses_list':                     email_addresses_list,
            'linked_organization_we_vote_id_list':      linked_organization_we_vote_id_list_updated,
            'messages_on_stage':                        messages_on_stage,
            'organization_list_with_duplicate_twitter': organization_list_with_duplicate_twitter_updated,
            'public_positions_owned_by_this_voter':     public_positions_owned_by_this_voter,
            'positions_for_friends_owned_by_this_voter':    positions_for_friends_owned_by_this_voter,
            'sms_phone_numbers_list':                   sms_phone_numbers_list,
            'stripe_payments':                          StripeManager.retrieve_payments_total(voter_on_stage.we_vote_id),
            'supporters_list':                          supporters_list,
            'volunteer_team_list':                      volunteer_team_list,
            'voter_id':                                 voter_on_stage.id,
            'voter':                                    voter_on_stage,
            'voter_invitation_first_name':              voter_on_stage.first_name,
            'voter_invitation_email':                   voter_on_stage.email,
            'voter_invitation_password':                voter_invitation_password,
            'voter_list_duplicate_facebook':            voter_list_duplicate_facebook_updated,
            'voter_list_duplicate_twitter':             voter_list_duplicate_twitter_updated,
            'password_proposed':                        generate_proposed_password(),
        }
    else:
        messages_on_stage = get_messages(request)
        template_values = {
            'messages_on_stage':    messages_on_stage,
            'voter_id':             0,
        }
    return render(request, 'voter/voter_edit.html', template_values)


@login_required
def voter_change_authority_process_view(request):
    """
    Grant or remove an existing account volunteer or admin rights
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'voter_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_on_stage = Voter()
    authority_changed = False

    voter_id = request.GET.get('voter_id', 0)
    voter_id = convert_to_int(voter_id)
    authority_granted = request.GET.get('authority_granted', False)
    authority_removed = request.GET.get('authority_removed', False)

    # Check to see if this voter is already being used anywhere
    voter_on_stage_found = False
    try:
        voter_query = Voter.objects.filter(id=voter_id)
        if len(voter_query):
            voter_on_stage = voter_query[0]
            voter_on_stage_found = True
    except Exception as e:
        handle_record_not_found_exception(e, logger=logger)

    if voter_on_stage_found:
        try:
            if authority_granted == 'admin':
                voter_on_stage.is_admin = True
                authority_changed = True
            elif authority_granted == 'analytics_admin':
                voter_on_stage.is_analytics_admin = True
                authority_changed = True
            elif authority_granted == 'partner_organization':
                voter_on_stage.is_partner_organization = True
                authority_changed = True
            elif authority_granted == 'political_data_manager':
                voter_on_stage.is_political_data_manager = True
                authority_changed = True
            elif authority_granted == 'political_data_viewer':
                voter_on_stage.is_political_data_viewer = True
                authority_changed = True
            elif authority_granted == 'verified_volunteer':
                voter_on_stage.is_verified_volunteer = True
                authority_changed = True
            elif authority_granted == 'voter_manager':
                voter_on_stage.is_voter_manager = True
                authority_changed = True

            if authority_removed == 'admin':
                voter_on_stage.is_admin = False
                authority_changed = True
            elif authority_removed == 'analytics_admin':
                voter_on_stage.is_analytics_admin = False
                authority_changed = True
            elif authority_removed == 'partner_organization':
                voter_on_stage.is_partner_organization = False
                authority_changed = True
            elif authority_removed == 'political_data_manager':
                voter_on_stage.is_political_data_manager = False
                authority_changed = True
            elif authority_removed == 'political_data_viewer':
                voter_on_stage.is_political_data_viewer = False
                authority_changed = True
            elif authority_removed == 'verified_volunteer':
                voter_on_stage.is_verified_volunteer = False
                authority_changed = True
            elif authority_removed == 'voter_manager':
                voter_on_stage.is_voter_manager = False
                authority_changed = True

            if authority_changed:
                voter_on_stage.save()

            messages.add_message(request, messages.INFO, 'Voter authority updated.')
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR, 'Could not save voter.')
    else:
        messages.add_message(request, messages.ERROR, 'Could not save change to authority.')

    return HttpResponseRedirect(reverse('voter:voter_edit', args=(voter_id,)))


@login_required
def voter_remove_facebook_auth_process_view(request, voter_id=0, voter_we_vote_id=""):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'voter_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_id = request.GET.get('voter_id', 0)
    voter_id = convert_to_int(voter_id)
    voter_we_vote_id = request.GET.get('voter_we_vote_id', "")

    facebook_user_id = ""
    facebook_manager = FacebookManager()
    return_auth_status = "No Facebook authentication data for this voter was found to remove."

    # Get FacebookLinkToVoter then delete it
    try:
        link_delete_results = facebook_manager.delete_facebook_link_to_voter(voter_we_vote_id)
        facebook_user_id = link_delete_results['facebook_user_id']

        if positive_value_exists(facebook_user_id):
            return_auth_status = "The Facebook link to voter '" + voter_we_vote_id + "' was deleted.  In addition "

            delete_users_results = facebook_manager.delete_facebook_users(facebook_user_id)
            return_auth_status += str(delete_users_results['facebook_users_deleted']) + " Facebook user rows and "

            delete_auth_results = facebook_manager.delete_facebook_auth_responses(facebook_user_id)
            return_auth_status += str(delete_auth_results['facebook_auth_rows_deleted']) + " auth rows were deleted."

    except FacebookLinkToVoter.DoesNotExist:

        pass

    except Exception as e:
        handle_exception(e, logger=logger,
                         exception_message="voter_remove_facebook_auth_process_view exception threw ")
        pass

    messages.add_message(request, messages.INFO, return_auth_status)

    return HttpResponseRedirect(reverse('voter:voter_edit', args=(str(voter_id),)))


@login_required
def voter_list_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'voter_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_search = request.GET.get('voter_search', '')
    is_admin = request.GET.get('is_admin', '')
    is_analytics_admin = request.GET.get('is_analytics_admin', '')
    is_partner_organization = request.GET.get('is_partner_organization', '')
    is_political_data_manager = request.GET.get('is_political_data_manager', '')
    is_political_data_viewer = request.GET.get('is_political_data_viewer', '')
    is_verified_volunteer = request.GET.get('is_verified_volunteer', '')
    is_voter_manager = request.GET.get('is_voter_manager', '')
    has_contributed = request.GET.get('has_contributed', '')
    has_friends = request.GET.get('has_friends', '')
    voter_invitation_email = request.GET.get('voter_invitation_email', '')
    voter_invitation_first_name = request.GET.get('voter_invitation_first_name', '')
    voter_invitation_password = request.GET.get('voter_invitation_password', '')
    # run_scripts = positive_value_exists(request.GET.get('run_scripts', False))
    run_scripts = True
    show_voter_merge_data = request.GET.get('show_voter_merge_data', '')
    has_voter_merge_problem = request.GET.get('has_voter_merge_problem', '')

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_manager = VoterManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id)
    voter_id = 0
    if results['voter_found']:
        voter = results['voter']
        voter_id = voter.id
        voter_id = convert_to_int(voter_id)

    # If there is an entry in the VoterIssuesLookup table for a voter_we_vote_id, mark the voter table
    voter_issues_lookup_repair = True
    if voter_issues_lookup_repair and run_scripts:
        voter_issues_query = VoterIssuesLookup.objects.using('readonly').all()
        voter_issues_list = list(voter_issues_query)
        voter_we_vote_id_list_to_update = []
        for one_voter_issue in voter_issues_list:
            voter_we_vote_id_list_to_update.append(one_voter_issue.voter_we_vote_id)
        voter_update_query = Voter.objects.all()
        voter_update_query = voter_update_query.filter(we_vote_id__in=voter_we_vote_id_list_to_update)
        voter_update_query.update(voter_issues_lookup_updated=True)

    # Populate the VoterIssuesLookup table
    number_to_update = 100000
    voter_issues_lookup_updates = True
    if voter_issues_lookup_updates and run_scripts:
        voter_issues_lookup_updates_status = ""
        voter_query = Voter.objects.all()
        voter_query = voter_query.exclude(voter_issues_lookup_updated=True)
        total_to_convert = voter_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        voter_list_one_batch = list(voter_query[:number_to_update])
        voter_we_vote_id_list_one_batch = []
        for one_voter in voter_list_one_batch:
            voter_we_vote_id_list_one_batch.append(one_voter.we_vote_id)

        # Retrieve all relevant FollowIssue entries in a single query
        from follow.models import FOLLOWING, FollowIssue
        follow_issue_query = FollowIssue.objects.using('readonly').all()
        follow_issue_query = follow_issue_query.filter(voter_we_vote_id__in=voter_we_vote_id_list_one_batch)
        follow_issue_query = follow_issue_query.filter(following_status=FOLLOWING)
        follow_issue_list = list(follow_issue_query)

        dict_of_voter_issue_defaults = {}  # voter_we_vote_id as key, value is list of defaults

        from issue.models import VOTER_ISSUES_LOOKUP_DICT
        deprecated_issues_count = 0
        for one_follow in follow_issue_list:
            voter_we_vote_id = one_follow.voter_we_vote_id
            issue_we_vote_id = one_follow.issue_we_vote_id
            if voter_we_vote_id not in dict_of_voter_issue_defaults:
                dict_of_voter_issue_defaults[voter_we_vote_id] = {}
            try:
                issue_key = VOTER_ISSUES_LOOKUP_DICT[issue_we_vote_id]
                if positive_value_exists(issue_key):
                    dict_of_voter_issue_defaults[voter_we_vote_id][issue_key] = True
                else:
                    voter_issues_lookup_updates_status += "MISSING_ISSUE_KEY: " + issue_we_vote_id + " "
            except Exception as e:
                deprecated_issues_count += 1
        if deprecated_issues_count > 0:
            voter_issues_lookup_updates_status += "DEPRECATED_ISSUES: " + str(deprecated_issues_count) + " "

        voter_issues_create_list = []
        voter_issues_creates_made = 0
        voter_issues_creates_needed = False
        updates_made = 0
        voter_update_list = []
        voter_updates_made = 0
        for voter_we_vote_id in voter_we_vote_id_list_one_batch:
            if voter_we_vote_id not in dict_of_voter_issue_defaults:
                continue
            defaults = dict_of_voter_issue_defaults[voter_we_vote_id]
            if voter_we_vote_id and len(defaults) > 0:
                voter_issues_create_list.append(
                    VoterIssuesLookup(
                        voter_we_vote_id=voter_we_vote_id,
                        **defaults,
                    )
                )
                voter_issues_creates_made += 1
                voter_issues_creates_needed = True
        voter_issues_create_failed = False
        if voter_issues_creates_needed:
            try:
                VoterIssuesLookup.objects.bulk_create(voter_issues_create_list)
                voter_issues_lookup_updates_status += \
                    "{updates_made:,} VoterIssuesLookup entries created. " \
                    "{total_to_convert_after:,} remaining. " \
                    "".format(
                        total_to_convert_after=total_to_convert_after,
                        updates_made=voter_issues_creates_made)
            except Exception as e:
                voter_issues_create_failed = True
                voter_issues_lookup_updates_status += \
                    "{updates_made:,} VoterIssuesLookup entries NOT created. " \
                    "{total_to_convert_after:,} remaining. ERROR: {error}" \
                    "".format(
                         error=str(e),
                         total_to_convert_after=total_to_convert_after,
                         updates_made=updates_made)
        if not voter_issues_create_failed:
            for one_voter in voter_list_one_batch:
                one_voter.voter_issues_lookup_updated = True
                voter_update_list.append(one_voter)
                voter_updates_made += 1

        if voter_updates_made > 0:
            try:
                Voter.objects.bulk_update(
                    voter_update_list, ['voter_issues_lookup_updated'])
                voter_issues_lookup_updates_status += "Voter entries updated: {voter_updates_made:,}. " \
                                                      "".format(voter_updates_made=voter_updates_made)
            except Exception as e:
                voter_issues_lookup_updates_status += "Voter entries (" + str(voter_updates_made) + ") " \
                    "NOT updated: " + str(e) + " "
        if positive_value_exists(voter_issues_lookup_updates_status) or positive_value_exists(total_to_convert_after):
            voter_issues_lookup_updates_status += \
                "Updates remaining: {total_to_convert_after:,}. " \
                "".format(
                    total_to_convert_after=total_to_convert_after)
            messages.add_message(request, messages.INFO, voter_issues_lookup_updates_status)

    likely_political_party_analysis = True
    number_to_update = 10000
    updates_made = 0
    if likely_political_party_analysis and run_scripts:
        voter_issues_lookup_updates_status = ''
        voter_issues_update_list = []
        voter_issues_query = VoterIssuesLookup.objects.all()
        voter_issues_query = voter_issues_query.exclude(likely_party_from_issues_analyzed=True)
        voter_issues_list = list(voter_issues_query[:number_to_update])
        from issue.controllers import calculate_likely_political_party_from_issues
        for voter_issues_lookup in voter_issues_list:
            results = calculate_likely_political_party_from_issues(voter_issues_lookup=voter_issues_lookup)
            if results['success']:
                # Left/Right
                voter_issues_lookup.likely_left_from_issues = results['likely_left_from_issues']
                voter_issues_lookup.likely_right_from_issues = results['likely_right_from_issues']
                # We are only setting one party per person
                voter_issues_lookup.likely_democrat_from_issues = results['likely_democrat_from_issues']
                voter_issues_lookup.likely_green_from_issues = results['likely_green_from_issues']
                voter_issues_lookup.likely_libertarian_from_issues = results['likely_libertarian_from_issues']
                voter_issues_lookup.likely_republican_from_issues = results['likely_republican_from_issues']
                voter_issues_lookup.likely_party_from_issues_analyzed = True
                updates_made += 1
                voter_issues_update_list.append(voter_issues_lookup)
        if positive_value_exists(updates_made):
            try:
                VoterIssuesLookup.objects.bulk_update(
                    voter_issues_update_list, [
                        'likely_left_from_issues',
                        'likely_right_from_issues',
                        'likely_democrat_from_issues',
                        'likely_green_from_issues',
                        'likely_libertarian_from_issues',
                        'likely_republican_from_issues',
                        'likely_party_from_issues_analyzed',
                    ])
                voter_issues_lookup_updates_status += "VoterIssuesLookup entries updated: {updates_made:,}" \
                                                      "".format(updates_made=updates_made)
            except Exception as e:
                voter_issues_lookup_updates_status += "VoterIssuesLookup entries (" + str(updates_made) + ") " \
                                                      "NOT updated: " + str(e) + " "
        if positive_value_exists(voter_issues_lookup_updates_status):
            messages.add_message(request, messages.INFO, voter_issues_lookup_updates_status)

    # Set is_signed_in_cached True if a voter has signed in (needed for voterListAnalytics)
    number_to_update = 10000
    voter_is_signed_in_cached_updates = True
    if voter_is_signed_in_cached_updates and run_scripts:
        voter_is_signed_in_status = ""
        voter_query = Voter.objects.all()
        voter_query = voter_query.exclude(is_signed_in_cached=True)
        # Focus on voters who have signed in for now
        # In the future, we can also mark 'is_signed_in_cached' to be False for older records. Now, leave Null.

        voter_raw_filters = []
        new_voter_filter = Q(twitter_id__isnull=False)
        voter_raw_filters.append(new_voter_filter)
        new_voter_filter = Q(twitter_id__gt=0)
        voter_raw_filters.append(new_voter_filter)

        new_voter_filter = Q(facebook_id__isnull=False)
        voter_raw_filters.append(new_voter_filter)
        new_voter_filter = Q(facebook_id__gt=0)
        voter_raw_filters.append(new_voter_filter)

        # Does this catch voters signed in with Apple?
        new_voter_filter = Q(primary_email_we_vote_id__isnull=False)
        voter_raw_filters.append(new_voter_filter)

        new_voter_filter = Q(primary_sms_we_vote_id__isnull=False)
        voter_raw_filters.append(new_voter_filter)

        final_voter_filters = voter_raw_filters.pop()

        # ...and "OR" the remaining items in the list
        for item in voter_raw_filters:
            final_voter_filters |= item

        voter_query = voter_query.filter(final_voter_filters)

        total_to_convert = voter_query.count()
        total_to_convert_after = total_to_convert - number_to_update if total_to_convert > number_to_update else 0
        updates_made = 0
        voter_list_one_batch = list(voter_query[:number_to_update])
        voter_signed_in_update_list = []
        for one_voter in voter_list_one_batch:
            one_voter.is_signed_in_cached = True
            voter_signed_in_update_list.append(one_voter)
            updates_made += 1
        if positive_value_exists(updates_made):
            Voter.objects.bulk_update(
                voter_signed_in_update_list, [
                    'is_signed_in_cached',
                ])
            voter_is_signed_in_status += (
                "Voter entries updated with is_signed_in_cached: {updates_made:,} "
                "".format(updates_made=updates_made))
        if positive_value_exists(total_to_convert_after):
            voter_is_signed_in_status += (
                "is_signed_in_cached updates needed: {total_to_convert_after:,} "
                "".format(total_to_convert_after=total_to_convert_after))
        if positive_value_exists(voter_is_signed_in_status):
            messages.add_message(request, messages.INFO, voter_is_signed_in_status)

    messages_on_stage = get_messages(request)
    if positive_value_exists(voter_search):
        # Search for an email address - do not require to be verified
        voter_we_vote_ids_with_email_query = EmailAddress.objects.filter(
            normalized_email_address__icontains=voter_search,
        ).values_list('voter_we_vote_id', flat=True)
        voter_we_vote_ids_with_email = list(voter_we_vote_ids_with_email_query)

        # Search for a phone number
        voter_we_vote_ids_with_sms_phone_number_query = SMSPhoneNumber.objects.filter(
            normalized_sms_phone_number__icontains=voter_search,
        ).values_list('voter_we_vote_id', flat=True)
        voter_we_vote_ids_with_sms_phone_number = list(voter_we_vote_ids_with_sms_phone_number_query)

        # Now search voter object
        voter_query = Voter.objects.all()
        search_words = voter_search.split()
        for one_word in search_words:
            filters = []  # Reset for each search word
            new_filter = Q(first_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(middle_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(last_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(we_vote_id__iexact=one_word)
            filters.append(new_filter)

            if len(voter_we_vote_ids_with_email) > 0:
                new_filter = Q(we_vote_id__in=voter_we_vote_ids_with_email)
                filters.append(new_filter)

            if len(voter_we_vote_ids_with_sms_phone_number) > 0:
                new_filter = Q(we_vote_id__in=voter_we_vote_ids_with_sms_phone_number)
                filters.append(new_filter)

            new_filter = Q(email__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(normalized_sms_phone_number__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(facebook_email__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(twitter_screen_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(twitter_name__icontains=one_word)
            filters.append(new_filter)

            new_filter = Q(linked_organization_we_vote_id__iexact=one_word)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                voter_query = voter_query.filter(final_filters)
    else:
        voter_query = Voter.objects.order_by(
            '-date_last_changed')

    if positive_value_exists(is_admin):
        voter_query = voter_query.filter(is_admin=True)
    if positive_value_exists(is_analytics_admin):
        voter_query = voter_query.filter(is_analytics_admin=True)
    if positive_value_exists(is_partner_organization):
        voter_query = voter_query.filter(is_partner_organization=True)
    if positive_value_exists(is_political_data_manager):
        voter_query = voter_query.filter(is_political_data_manager=True)
    if positive_value_exists(is_political_data_viewer):
        voter_query = voter_query.filter(is_political_data_viewer=True)
    if positive_value_exists(is_voter_manager):
        voter_query = voter_query.filter(is_voter_manager=True)
    if positive_value_exists(has_contributed):
        payments = StripePayments.objects.all()
        voter_query = voter_query.filter(we_vote_id__in=Subquery(payments.values('voter_we_vote_id')))
    if positive_value_exists(has_friends):
        voter_query = voter_query.filter(friend_count__gt=0)
        voter_query = voter_query.order_by('-friend_count')
    from_merge_status_dict = {}
    to_merge_status_dict = {}
    if positive_value_exists(has_voter_merge_problem) or positive_value_exists(show_voter_merge_data):
        queryset = VoterMergeStatus.objects.all().order_by('-id')
        if positive_value_exists(has_voter_merge_problem):
            queryset = queryset.filter(total_merge_complete=False)
        voter_merge_status_list = list(queryset[:500])
        queryset_from_ids = queryset.values_list('from_voter_we_vote_id', flat=True).distinct()
        from_list = list(queryset_from_ids[:500])
        queryset_to_ids = queryset.values_list('to_voter_we_vote_id', flat=True).distinct()
        to_list = list(queryset_to_ids[:500])
        merge_data_we_vote_id_list = list(set(from_list + to_list))
        voter_query = voter_query.filter(we_vote_id__in=merge_data_we_vote_id_list)
        for voter_merge_status in voter_merge_status_list:
            log_queryset = VoterMergeLog.objects.filter(
                from_voter_we_vote_id__iexact=voter_merge_status.from_voter_we_vote_id,
                to_voter_we_vote_id__iexact=voter_merge_status.to_voter_we_vote_id,
            ).order_by('id')
            voter_merge_log_list = list(log_queryset)
            voter_merge_status.voter_merge_log_list = voter_merge_log_list
            if voter_merge_status.from_voter_we_vote_id in from_merge_status_dict:
                from_merge_status_dict[voter_merge_status.from_voter_we_vote_id].append(voter_merge_status)
            else:
                from_merge_status_dict[voter_merge_status.from_voter_we_vote_id] = [voter_merge_status]
            if voter_merge_status.to_voter_we_vote_id in to_merge_status_dict:
                to_merge_status_dict[voter_merge_status.to_voter_we_vote_id].append(voter_merge_status)
            else:
                to_merge_status_dict[voter_merge_status.to_voter_we_vote_id] = [voter_merge_status]

    voter_list_found_count = voter_query.count()

    voter_list = voter_query[:50]
    modified_voter_list = []

    facebook_manager = FacebookManager()
    twitter_user_manager = TwitterUserManager()
    for one_voter in voter_list:
        one_voter.twitter_handle = twitter_user_manager.fetch_twitter_handle_from_voter_we_vote_id(one_voter.we_vote_id)
        one_voter.retrieved_facebook_id = facebook_manager.fetch_facebook_id_from_voter_we_vote_id(one_voter.we_vote_id)
        spent = StripeManager.retrieve_payments_total(one_voter.we_vote_id)
        one_voter.amount_spent = spent if spent != '$0.00' else ''
        if one_voter.we_vote_id in from_merge_status_dict:
            one_voter.from_voter_merge_status_list = from_merge_status_dict[one_voter.we_vote_id]
        if one_voter.we_vote_id in to_merge_status_dict:
            one_voter.to_voter_merge_status_list = to_merge_status_dict[one_voter.we_vote_id]
        modified_voter_list.append(one_voter)

    template_values = {
        'is_admin':                     is_admin,
        'is_analytics_admin':           is_analytics_admin,
        'is_partner_organization':      is_partner_organization,
        'is_political_data_manager':    is_political_data_manager,
        'is_political_data_viewer':     is_political_data_viewer,
        'is_verified_volunteer':        is_verified_volunteer,
        'is_voter_manager':             is_voter_manager,
        'has_contributed':              has_contributed,
        'has_friends':                  has_friends,
        'has_voter_merge_problem':      has_voter_merge_problem,
        'messages_on_stage':            messages_on_stage,
        'password_proposed':            generate_proposed_password(),
        'show_voter_merge_data':        show_voter_merge_data,
        'voter_invitation_email':       voter_invitation_email,
        'voter_invitation_first_name':  voter_invitation_first_name,
        'voter_invitation_password':    voter_invitation_password,
        'voter_list':                   modified_voter_list,
        'voter_list_found_count':       voter_list_found_count,
        'voter_id_signed_in':           voter_id,
        'voter_search':                 voter_search,
    }
    return render(request, 'voter/voter_list.html', template_values)


@login_required
def voter_summary_view(request, voter_id=0, voter_we_vote_id=''):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    exclude_remind_contact = positive_value_exists(request.GET.get('exclude_remind_contact', False))
    limit_to_last_90_days = positive_value_exists(request.GET.get('limit_to_last_90_days', False))
    number_to_update = convert_to_int(request.GET.get('number_to_update', False))
    show_shares_with_zero_clicks = positive_value_exists(request.GET.get('show_shares_with_zero_clicks', False))
    voter_summary_search = request.GET.get('voter_summary_search', '')
    show_more = positive_value_exists(request.GET.get('show_more', False))
    show_this_year = convert_to_int(request.GET.get('show_this_year', 0))

    voter_id = convert_to_int(voter_id)
    voter_on_stage_found = False
    voter_on_stage = Voter()
    if positive_value_exists(voter_id):
        try:
            voter_on_stage = Voter.objects.get(id=voter_id)
            voter_we_vote_id = voter_on_stage.we_vote_id
            voter_on_stage_found = True
        except Voter.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except Voter.DoesNotExist:
            # This is fine, create new below
            pass
    elif positive_value_exists(voter_we_vote_id):
        try:
            voter_on_stage = Voter.objects.get(we_vote_id=voter_we_vote_id)
            voter_id = voter_on_stage.id
            voter_on_stage_found = True
        except Voter.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
        except Voter.DoesNotExist:
            # This is fine, create new below
            pass

    voter_address_manager = VoterAddressManager()
    address_results = voter_address_manager.retrieve_voter_address_list(voter_id=voter_id)
    voter_address_list = address_results['voter_address_list']

    update_statistics = True
    if update_statistics and positive_value_exists(voter_we_vote_id):
        by_year_mode = positive_value_exists(show_this_year)
        voter_dict_by_voter_we_vote_id = {}
        voter_dict_by_voter_we_vote_id[voter_we_vote_id] = voter_on_stage

        queryset = SharedItem.objects.using('readonly').all()
        queryset = queryset.order_by('id')
        queryset = queryset.filter(shared_by_voter_we_vote_id=voter_we_vote_id)
        shared_item_list = list(queryset)

        update_results = update_voter_who_shares_tables_from_shared_item_list(
            by_year_mode=by_year_mode,
            shared_item_list=shared_item_list,
            voter_dict_by_voter_we_vote_id=voter_dict_by_voter_we_vote_id,
        )
        message_to_print = \
            "UPDATE_VOTER_WHO_SHARES_FOR_THIS_VOTER: \n" \
            "sharing_summary_items_changed: {sharing_summary_items_changed:,}, " \
            "sharing_summary_items_not_changed: {sharing_summary_items_not_changed:,} \n" \
            "status: {status} \n" \
            "".format(
                sharing_summary_items_changed=update_results['sharing_summary_items_changed'],
                sharing_summary_items_not_changed=update_results['sharing_summary_items_not_changed'],
                status=update_results['status'],
            )
        messages.add_message(request, messages.INFO, message_to_print)

    if positive_value_exists(show_this_year):
        # If filtering by year, use VoterWhoSharesSummaryOneYear object
        voter_who_shares_query = VoterWhoSharesSummaryOneYear.objects.using('readonly').all()
        voter_who_shares_query = voter_who_shares_query.filter(year_as_integer=show_this_year)
    else:
        # Otherwise, use VoterWhoSharesSummaryAllTime object
        voter_who_shares_query = VoterWhoSharesSummaryAllTime.objects.using('readonly').all()
    voter_who_shares_query = voter_who_shares_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
    voter_who_shares_summary_list = list(voter_who_shares_query)

    voter_who_shares_summary_list_modified = []
    for voter_who_shares_summary in voter_who_shares_summary_list:
        # Now retrieve all shared items to show under this voter summary
        shared_item_query = SharedItem.objects.using('readonly').all()
        shared_item_query = \
            shared_item_query.filter(shared_by_voter_we_vote_id=voter_who_shares_summary.voter_we_vote_id)
        shared_item_query = shared_item_query.order_by('-date_first_shared')

        if positive_value_exists(voter_summary_search):
            # Search for an email address - do not require to be verified
            voter_we_vote_ids_with_email_query = EmailAddress.objects.filter(
                normalized_email_address__icontains=voter_summary_search,
            ).values_list('voter_we_vote_id', flat=True)
            voter_we_vote_ids_with_email = list(voter_we_vote_ids_with_email_query)

            # Search for a phone number
            voter_we_vote_ids_with_sms_phone_number_query = SMSPhoneNumber.objects.filter(
                normalized_sms_phone_number__icontains=voter_summary_search,
            ).values_list('voter_we_vote_id', flat=True)
            voter_we_vote_ids_with_sms_phone_number = list(voter_we_vote_ids_with_sms_phone_number_query)

            search_words = voter_summary_search.split()
            for one_word in search_words:
                filters = []  # Reset for each search word
                if len(voter_we_vote_ids_with_email) > 0:
                    new_filter = Q(shared_by_voter_we_vote_id__in=voter_we_vote_ids_with_email)
                    filters.append(new_filter)

                if len(voter_we_vote_ids_with_sms_phone_number) > 0:
                    new_filter = Q(shared_by_voter_we_vote_id__in=voter_we_vote_ids_with_sms_phone_number)
                    filters.append(new_filter)

                new_filter = Q(destination_full_url__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(shared_by_display_name__icontains=one_word)
                filters.append(new_filter)

                new_filter = Q(shared_by_voter_we_vote_id__iexact=one_word)
                filters.append(new_filter)

                # Add the first query
                if len(filters):
                    final_filters = filters.pop()

                    # ...and "OR" the remaining items in the list
                    for item in filters:
                        final_filters |= item

                    shared_item_query = shared_item_query.filter(final_filters)

        if positive_value_exists(exclude_remind_contact):
            shared_item_query = shared_item_query.exclude(is_remind_contact_share=True)
        if not positive_value_exists(show_shares_with_zero_clicks):
            shared_item_query = shared_item_query.filter(shared_link_clicked_count__gt=0)
        if positive_value_exists(limit_to_last_90_days):
            when_process_must_stop = now() - timedelta(days=90)
            shared_item_query = shared_item_query.filter(date_first_shared__gt=when_process_must_stop)
        if positive_value_exists(show_this_year):
            shared_item_query = shared_item_query.filter(date_first_shared__year=show_this_year)

        voter_who_shares_summary.shared_item_list_count = shared_item_query.count()

        shared_item_list = shared_item_query[:2000]
        voter_who_shares_summary.shared_item_list = shared_item_list
        voter_who_shares_summary_list_modified.append(voter_who_shares_summary)

    messages_on_stage = get_messages(request)

    if voter_on_stage_found:
        template_values = {
            'election_years_available':         ELECTION_YEARS_AVAILABLE,
            'exclude_remind_contact':           exclude_remind_contact,
            'limit_to_last_90_days':            limit_to_last_90_days,
            'messages_on_stage':                messages_on_stage,
            'show_shares_with_zero_clicks':     show_shares_with_zero_clicks,
            'show_this_year':                   show_this_year,
            'voter':                            voter_on_stage,
            'voter_address_list':               voter_address_list,
            'voter_summary_search':             voter_summary_search,
            'voter_we_vote_id':                 voter_we_vote_id,
            'voter_who_shares_summary_list':    voter_who_shares_summary_list_modified,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'voter/voter_summary.html', template_values)


def create_dev_user_view(request):
    create_dev_user()
    return None
