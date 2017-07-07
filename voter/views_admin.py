# voter/views_admin.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from .models import Voter, VoterDeviceLinkManager
from admin_tools.views import redirect_to_sign_in_page
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from exception.models import handle_record_found_more_than_one_exception, handle_record_not_found_exception, \
    handle_record_not_saved_exception
from import_export_facebook.models import FacebookLinkToVoter, FacebookManager
from organization.models import Organization, OrganizationManager
from position.controllers import merge_duplicate_positions_for_voter
from position.models import PositionEntered, PositionForFriends
from twitter.models import TwitterLinkToOrganization, TwitterLinkToVoter, TwitterUserManager
from voter.models import fetch_voter_id_from_voter_device_link, voter_has_authority, voter_setup
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, get_voter_api_device_id, set_voter_api_device_id, \
    positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


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
        # Currently all of the twitter authentication for Django is in the separate social_auth* tables

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
    except:
        messages.add_message(request, messages.INFO, 'Voter not updated.')

    return HttpResponseRedirect(reverse('login_user', args=()))


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

        set_as_verified_volunteer = "UPDATE voter_voter SET is_verified_volunteer=True WHERE id={voter_id};" \
                                    "".format(voter_id=voter_id)
        unset_as_verified_volunteer = "UPDATE voter_voter SET is_verified_volunteer=False WHERE id={voter_id};" \
                                      "".format(voter_id=voter_id)
        template_values = {
            'messages_on_stage':            messages_on_stage,
            'voter':                        voter_on_stage,
            'voter_api_device_id':          voter_api_device_id,
            'is_authenticated':             request.user.is_authenticated(),
            'set_this_voter_as_admin':      set_this_voter_as_admin,
            'unset_this_voter_as_admin':    unset_this_voter_as_admin,
            'set_as_verified_volunteer':    set_as_verified_volunteer,
            'unset_as_verified_volunteer':  unset_as_verified_volunteer,
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
def voter_edit_process_view(request):
    """
    Process the new or edit voter forms
    :param request:
    :return:
    """
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # NOTE: create_twitter_link_to_voter is processed in voter_edit_view

    voter_on_stage = Voter()
    at_least_one_value_changed = False

    voter_id = request.POST.get('voter_id', 0)
    voter_id = convert_to_int(voter_id)
    first_name = request.POST.get('first_name', False)
    last_name = request.POST.get('last_name', False)
    twitter_handle = request.POST.get('twitter_handle', False)
    email = request.POST.get('email', False)
    password_text = request.POST.get('password_text', False)

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
            if email is not False:
                voter_on_stage.email = email
                at_least_one_value_changed = True
            if password_text is not False:
                voter_on_stage.set_password(password_text)
                at_least_one_value_changed = True

            if at_least_one_value_changed:
                voter_on_stage.save()

            if password_text:
                # Check to see if a login has already been created
                pass
            messages.add_message(request, messages.INFO, 'Voter information updated.')
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            messages.add_message(request, messages.ERROR, 'Could not save voter.')
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
            messages.add_message(request, messages.ERROR, 'Could not save voter.')

    return HttpResponseRedirect(reverse('voter:voter_edit', args=(voter_id,)))


@login_required
def voter_edit_view(request, voter_id):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    create_facebook_link_to_voter = request.GET.get('create_facebook_link_to_voter', False)
    create_organization_for_voter = request.GET.get('create_organization_for_voter', False)
    create_twitter_link_to_voter = request.GET.get('create_twitter_link_to_voter', False)
    cross_link_all_voter_positions = request.GET.get('cross_link_all_voter_positions', False)
    merge_duplicate_positions = request.GET.get('merge_duplicate_positions', False)

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
        voter_on_stage = Voter.objects.get(id=voter_id)
        voter_on_stage_found = True
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

        # Do some checks on all of the public positions owned by this voter
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
                do_not_create_organization_message = "Organization could not be created. "
                if linked_organization_found:
                    do_not_create_organization_message += "Linked organization found. "

                messages.add_message(request, messages.ERROR, do_not_create_organization_message)
            else:
                organization_name = voter_on_stage.get_full_name()
                organization_website = ""
                organization_twitter_handle = ""
                organization_email = ""
                organization_facebook = ""
                organization_image = voter_on_stage.voter_photo_url()
                create_results = organization_manager.create_organization(
                    organization_name, organization_website, organization_twitter_handle,
                    organization_email, organization_facebook, organization_image)
                if create_results['organization_created']:
                    organization = create_results['organization']
                    try:
                        voter_on_stage.linked_organization_we_vote_id = organization.we_vote_id
                        voter_on_stage.save()
                        status_print_list += "Organization created.<br />"

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

        messages.add_message(request, messages.INFO, status_print_list)

        messages_on_stage = get_messages(request)

        template_values = {
            'messages_on_stage':                    messages_on_stage,
            'voter_id':                             voter_on_stage.id,
            'voter':                                voter_on_stage,
            'voter_list_duplicate_facebook':        voter_list_duplicate_facebook_updated,
            'voter_list_duplicate_twitter':         voter_list_duplicate_twitter_updated,
            'organization_list_with_duplicate_twitter': organization_list_with_duplicate_twitter_updated,
            'linked_organization_we_vote_id_list':  linked_organization_we_vote_id_list_updated,
            'public_positions_owned_by_this_voter': public_positions_owned_by_this_voter,
            'positions_for_friends_owned_by_this_voter':    positions_for_friends_owned_by_this_voter,
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
    authority_required = {'admin'}  # admin, verified_volunteer
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
            if authority_granted == 'verified_volunteer':
                voter_on_stage.is_verified_volunteer = True
                authority_changed = True
            elif authority_granted == 'admin':
                voter_on_stage.is_admin = True
                authority_changed = True

            if authority_removed == 'verified_volunteer':
                voter_on_stage.is_verified_volunteer = False
                authority_changed = True
            elif authority_removed == 'admin':
                voter_on_stage.is_admin = False
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
def voter_list_view(request):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    voter_id = fetch_voter_id_from_voter_device_link(voter_api_device_id)
    voter_id = convert_to_int(voter_id)

    messages_on_stage = get_messages(request)
    voter_list = Voter.objects.order_by('-is_admin', '-is_verified_volunteer', 'email', 'twitter_screen_name',
                                        'linked_organization_we_vote_id', 'facebook_email', 'last_name', 'first_name')
    voter_list = voter_list[:200]

    template_values = {
        'messages_on_stage': messages_on_stage,
        'voter_list': voter_list,
        'voter_id_signed_in': voter_id,
    }
    return render(request, 'voter/voter_list.html', template_values)


@login_required
def voter_summary_view(request, voter_id):
    authority_required = {'admin'}  # admin, verified_volunteer
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    messages_on_stage = get_messages(request)
    voter_id = convert_to_int(voter_id)
    voter_on_stage_found = False
    voter_on_stage = Voter()
    try:
        voter_on_stage = Voter.objects.get(id=voter_id)
        voter_on_stage_found = True
    except Voter.MultipleObjectsReturned as e:
        handle_record_found_more_than_one_exception(e, logger=logger)
    except Voter.DoesNotExist:
        # This is fine, create new
        pass

    if voter_on_stage_found:
        template_values = {
            'messages_on_stage':    messages_on_stage,
            'voter':                voter_on_stage,
        }
    else:
        template_values = {
            'messages_on_stage': messages_on_stage,
        }
    return render(request, 'voter/voter_summary.html', template_values)
