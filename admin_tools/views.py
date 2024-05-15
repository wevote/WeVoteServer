# admin_tools/views.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
import os

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

import wevote_functions
from ballot.models import BallotReturned, VoterBallotSaved
from candidate.controllers import candidates_import_from_sample_file
from candidate.models import CandidateCampaign, CandidateManager
from config.base import get_environment_variable, LOGIN_URL, BASE_DIR, PROJECT_PATH
from election.controllers import elections_import_from_sample_file
from election.models import Election
from email_outbound.models import EmailAddress
from follow.models import FollowOrganizationList
from friend.models import CurrentFriend, FriendManager, SuggestedFriend
from import_export_ctcl.models import CTCLApiCounterManager
from import_export_facebook.models import FacebookLinkToVoter, FacebookManager
from import_export_google_civic.models import GoogleCivicApiCounterManager
from import_export_vote_usa.models import VoteUSAApiCounterManager
from measure.models import ContestMeasure, ContestMeasureManager
from office.controllers import offices_import_from_sample_file
from office.models import ContestOffice
from organization.controllers import organizations_import_from_sample_file
from organization.models import Organization, OrganizationManager, INDIVIDUAL
from polling_location.controllers import import_and_save_all_polling_locations_data
from position.controllers import find_organizations_referenced_in_positions_for_this_voter, \
    positions_import_from_sample_file
from position.models import PositionEntered, PositionForFriends, PositionMetricsManager
from share.models import ShareManager
from twitter.functions import retrieve_twitter_rate_limit_info
from twitter.models import TwitterApiCounterManager, TwitterLinkToOrganization, TwitterLinkToVoter, TwitterUserManager
from voter.models import Voter, VoterAddress, VoterAddressManager, VoterDeviceLinkManager, \
    VoterManager, VoterMetricsManager, \
    voter_has_authority, voter_setup
from wevote_functions.functions import convert_to_int, delete_voter_api_device_id_cookie, generate_voter_device_id, \
    get_voter_api_device_id, positive_value_exists, set_voter_api_device_id, STATE_CODE_MAP
from wevote_functions.utils import get_node_version, get_postgres_version, get_python_version, get_git_commit_hash, \
    get_git_commit_date

BALLOT_ITEMS_SYNC_URL = get_environment_variable("BALLOT_ITEMS_SYNC_URL")  # ballotItemsSyncOut
BALLOT_RETURNED_SYNC_URL = get_environment_variable("BALLOT_RETURNED_SYNC_URL")  # ballotReturnedSyncOut
ELECTIONS_SYNC_URL = get_environment_variable("ELECTIONS_SYNC_URL")  # electionsSyncOut
ISSUES_SYNC_URL = get_environment_variable("ISSUES_SYNC_URL")  # issuesSyncOut
ORGANIZATIONS_SYNC_URL = get_environment_variable("ORGANIZATIONS_SYNC_URL")  # organizationsSyncOut
ORGANIZATION_LINK_TO_ISSUE_SYNC_URL = \
    get_environment_variable("ORGANIZATION_LINK_TO_ISSUE_SYNC_URL")  # organizationLinkToIssueSyncOut
OFFICES_SYNC_URL = get_environment_variable("OFFICES_SYNC_URL")  # officesSyncOut
CANDIDATES_SYNC_URL = get_environment_variable("CANDIDATES_SYNC_URL")  # candidatesSyncOut
MEASURES_SYNC_URL = get_environment_variable("MEASURES_SYNC_URL")  # measuresSyncOut
POLITICIANS_SYNC_URL = get_environment_variable("POLITICIANS_SYNC_URL")  # politiciansSyncOut
POLLING_LOCATIONS_SYNC_URL = get_environment_variable("POLLING_LOCATIONS_SYNC_URL")  # pollingLocationsSyncOut
POSITIONS_SYNC_URL = get_environment_variable("POSITIONS_SYNC_URL")  # positionsSyncOut
VOTER_GUIDES_SYNC_URL = get_environment_variable("VOTER_GUIDES_SYNC_URL")  # voterGuidesSyncOut
WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


logger = wevote_functions.admin.get_logger(__name__)

@login_required
def admin_home_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin', 'partner_organization', 'political_data_manager', 'political_data_viewer',
                          'verified_volunteer', 'voter_manager'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # logger.info("AdminHome BASE_DIR: %s", BASE_DIR)
    # logger.info("AdminHome PROJECT_PATH: %s", PROJECT_PATH)
    # pth_root_static_css = os.path.join(BASE_DIR, 'static/v1/apis_v1.css')
    # logger.info("AdminHome os.path.isfile BASE_DIR, static/v1/apis_v1.css : %s", os.path.isfile(pth_root_static_css))
    #  May 1, 2024 --  Nginix error:  Not Found: /apis/v1/static/apis_v1.css

    # Create a voter_device_id and voter in the database if one doesn't exist yet
    results = voter_setup(request)
    voter_api_device_id = results['voter_api_device_id']
    store_new_voter_api_device_id_in_cookie = results['store_new_voter_api_device_id_in_cookie']

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    state_code = request.GET.get('state_code', '')

    voter_metrics_manager = VoterMetricsManager()
    voter_accounts_count = voter_metrics_manager.fetch_voter_count_with_sign_in()
    voter_twitter_accounts_count = voter_metrics_manager.fetch_voter_count_with_twitter()
    voter_facebook_accounts_count = voter_metrics_manager.fetch_voter_count_with_facebook()
    voter_email_accounts_count = voter_metrics_manager.fetch_voter_count_with_verified_email()
    voter_sms_accounts_count = voter_metrics_manager.fetch_voter_count_with_verified_sms()
    voters_with_plan_count = voter_metrics_manager.fetch_voters_with_plan_count()

    voter_address_manager = VoterAddressManager()
    voter_address_basic_count = voter_address_manager.fetch_address_basic_count()
    voter_address_full_address_count = voter_address_manager.fetch_address_full_address_count()

    friend_manager = FriendManager()
    friendlinks = friend_manager.fetch_voters_with_friends_dataset_improved()
    (voters_with_friends_for_graph, voter_with_friends_counts) = \
        friend_manager.fetch_voters_with_friends_for_graph(friendlinks)
    voter_friendships_count = friend_manager.fetch_voter_friendships_count()

    position_metrics_manager = PositionMetricsManager()
    total_public_endorsements_count = position_metrics_manager.fetch_positions_public()
    total_public_endorsements_with_commentary_count = position_metrics_manager.fetch_positions_public_with_comments()
    total_friends_only_endorsements_count = position_metrics_manager.fetch_positions_friends_only()
    total_friends_only_endorsements_with_commentary_count = \
        position_metrics_manager.fetch_positions_friends_only_with_comments()

    share_manager = ShareManager()
    shared_link_clicked_unique_sharer_count = share_manager.fetch_shared_link_clicked_unique_sharer_count()
    shared_link_clicked_unique_viewer_count = share_manager.fetch_shared_link_clicked_unique_viewer_count()
    shared_links_count = share_manager.fetch_shared_link_clicked_shared_links_count()
    # shared_links_click_count = share_manager.fetch_shared_link_clicked_shared_links_click_count()
    shared_links_click_without_reclick_count = \
        share_manager.fetch_shared_link_clicked_shared_links_click_without_reclick_count()

    template_values = {
        'google_civic_election_id':           google_civic_election_id,
        'python_version':                     get_python_version(),
        'node_version':                       get_node_version(),
        'git_commit_hash':                    get_git_commit_hash(False),
        'git_commit_hash_url':                get_git_commit_hash(True),
        'git_commit_date':                    get_git_commit_date(),
        'postgres_version':                   get_postgres_version(),
        'shared_link_clicked_unique_sharer_count': shared_link_clicked_unique_sharer_count,
        'shared_link_clicked_unique_viewer_count': shared_link_clicked_unique_viewer_count,
        'shared_links_count':                 shared_links_count,
        # 'shared_links_click_count':         shared_links_click_count,
        'shared_links_click_without_reclick_count': shared_links_click_without_reclick_count,
        'state_code':                         state_code,
        'total_public_endorsements_count':    total_public_endorsements_count,
        'total_public_endorsements_with_commentary_count':  total_public_endorsements_with_commentary_count,
        'total_friends_only_endorsements_count':  total_friends_only_endorsements_count,
        'total_friends_only_endorsements_with_commentary_count':  total_friends_only_endorsements_with_commentary_count,
        'voter_accounts_count':               voter_accounts_count,
        'voter_address_basic_count':          voter_address_basic_count,
        'voter_address_full_address_count':   voter_address_full_address_count,
        'voter_email_accounts_count':         voter_email_accounts_count,
        'voter_facebook_accounts_count':      voter_facebook_accounts_count,
        'voter_twitter_accounts_count':       voter_twitter_accounts_count,
        'voter_sms_accounts_count':           voter_sms_accounts_count,
        'voters_with_1_friend_count':         friend_manager.get_count_of_friendlinks(friendlinks, "==", 1),
        'voters_with_1_plus_friend_count':    friend_manager.get_count_of_friendlinks(friendlinks, ">=", 1),
        'voters_with_2_friends_count':        friend_manager.get_count_of_friendlinks(friendlinks, "==", 2),
        'voters_with_3_friends_count':        friend_manager.get_count_of_friendlinks(friendlinks, "==", 3),
        'voters_with_3_plus_friends_count':   friend_manager.get_count_of_friendlinks(friendlinks, ">=", 3),
        'voters_with_10_plus_friends_count':  friend_manager.get_count_of_friendlinks(friendlinks, ">=", 10),
        'voters_with_10_to_20_friends_count': friend_manager.get_count_of_friendlinks(friendlinks, "range", 10, 19),
        'voters_with_20_plus_friends_count':  friend_manager.get_count_of_friendlinks(friendlinks, ">=", 20),
        'voters_with_friends_for_graph':      voters_with_friends_for_graph,
        'voter_with_friends_counts':          voter_with_friends_counts,
        'voters_with_plan_count':             voters_with_plan_count,
        'voter_friendships_count':            friend_manager.get_count_of_friendships(friendlinks),
        'WE_VOTE_SERVER_ROOT_URL':            WE_VOTE_SERVER_ROOT_URL,
    }
    response = render(request, 'admin_tools/index.html', template_values)

    # We want to store the voter_api_device_id cookie if it is new
    if positive_value_exists(voter_api_device_id) and positive_value_exists(store_new_voter_api_device_id_in_cookie):
        set_voter_api_device_id(request, response, voter_api_device_id)

    return response


@login_required
def data_cleanup_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    template_values = {
    }
    response = render(request, 'admin_tools/data_cleanup.html', template_values)

    return response


@login_required
def data_cleanup_organization_analysis_view(request):
    """
    Analyze a single organization
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_we_vote_id = request.GET.get('organization_we_vote_id')
    organization_found = False
    organization = Organization()

    twitter_link_to_this_organization_exists = False
    twitter_link_to_another_organization_exists = False
    try:
        organization = Organization.objects.get(we_vote_id__iexact=organization_we_vote_id)
        organization_found = True
        try:
            organization.linked_voter = Voter.objects.get(
                linked_organization_we_vote_id__iexact=organization.we_vote_id)
        except Voter.DoesNotExist:
            pass

        try:
            twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                organization_we_vote_id__iexact=organization.we_vote_id)
            if positive_value_exists(twitter_link_to_organization.twitter_id):
                twitter_link_to_this_organization_exists = True
                organization.twitter_id_from_link_to_organization = twitter_link_to_organization.twitter_id
                # We reach out for the twitter_screen_name
                organization.twitter_screen_name_from_link_to_organization = \
                    twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()
        except TwitterLinkToOrganization.DoesNotExist:
            pass
    except Organization.MultipleObjectsReturned as e:
        pass
    except Organization.DoesNotExist:
        pass

    # If this organization doesn't have a TwitterLinkToOrganization for the local twitter data,
    #  check to see if anyone else owns it.
    if not twitter_link_to_this_organization_exists and organization.twitter_user_id:
        try:
            twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                twitter_id=organization.twitter_user_id)
            if positive_value_exists(twitter_link_to_organization.twitter_id):
                if twitter_link_to_organization.organization_we_vote_id != organization.we_vote_id:
                    twitter_link_to_another_organization_exists = True
        except TwitterLinkToOrganization.DoesNotExist:
            pass

    # Voter that is linked to this Organization
    voter_linked_organization_we_vote_id_list = Voter.objects.all()
    voter_linked_organization_we_vote_id_list = voter_linked_organization_we_vote_id_list.filter(
        linked_organization_we_vote_id__iexact=organization.we_vote_id)
    voter_linked_organization_we_vote_id_list = voter_linked_organization_we_vote_id_list[:10]

    voter_linked_organization_we_vote_id_list_updated = []
    for one_linked_voter in voter_linked_organization_we_vote_id_list:
        if positive_value_exists(one_linked_voter.we_vote_id):
            try:
                twitter_link_to_voter = TwitterLinkToVoter.objects.get(
                    voter_we_vote_id__iexact=one_linked_voter.we_vote_id)
                if positive_value_exists(twitter_link_to_voter.twitter_id):
                    one_linked_voter.twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                    # We reach out for the twitter_screen_name
                    one_linked_voter.twitter_screen_name_from_link_to_voter = \
                        twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
            except TwitterLinkToVoter.DoesNotExist:
                pass

        voter_linked_organization_we_vote_id_list_updated.append(one_linked_voter)

    organization_list_with_duplicate_twitter_updated = []
    if organization_found:
        organization_filters = []
        if positive_value_exists(organization.twitter_user_id):
            new_organization_filter = Q(twitter_user_id=organization.twitter_user_id)
            organization_filters.append(new_organization_filter)
        if positive_value_exists(organization.organization_twitter_handle):
            new_organization_filter = Q(organization_twitter_handle__iexact=organization.organization_twitter_handle)
            organization_filters.append(new_organization_filter)

        if len(organization_filters):
            final_organization_filters = organization_filters.pop()

            # ...and "OR" the remaining items in the list
            for item in organization_filters:
                final_organization_filters |= item

            organization_list_with_duplicate_twitter = Organization.objects.all()
            organization_list_with_duplicate_twitter = organization_list_with_duplicate_twitter.filter(
                final_organization_filters)
            organization_list_with_duplicate_twitter = organization_list_with_duplicate_twitter.exclude(
                we_vote_id__iexact=organization_we_vote_id)

            for one_duplicate_organization in organization_list_with_duplicate_twitter:
                try:
                    linked_voter = \
                        Voter.objects.get(linked_organization_we_vote_id__iexact=one_duplicate_organization.we_vote_id)
                    one_duplicate_organization.linked_voter = linked_voter
                except Voter.DoesNotExist:
                    pass

                organization_list_with_duplicate_twitter_updated.append(one_duplicate_organization)

    # Voters that share the same local twitter data
    # (excluding voter linked to this org with linked_organization_we_vote_id)
    voter_raw_filters = []
    if positive_value_exists(organization.twitter_user_id):
        new_voter_filter = Q(twitter_id=organization.twitter_user_id)
        voter_raw_filters.append(new_voter_filter)
    if positive_value_exists(organization.organization_twitter_handle):
        new_voter_filter = Q(twitter_screen_name__iexact=organization.organization_twitter_handle)
        voter_raw_filters.append(new_voter_filter)

    voter_list_duplicate_twitter_updated = []
    if len(voter_raw_filters):
        final_voter_filters = voter_raw_filters.pop()

        # ...and "OR" the remaining items in the list
        for item in voter_raw_filters:
            final_voter_filters |= item

        voter_list_duplicate_twitter = Voter.objects.all()
        voter_list_duplicate_twitter = voter_list_duplicate_twitter.filter(final_voter_filters)
        voter_list_duplicate_twitter = voter_list_duplicate_twitter.exclude(
            linked_organization_we_vote_id__iexact=organization.we_vote_id)
        voter_list_duplicate_twitter = voter_list_duplicate_twitter

        for one_duplicate_voter in voter_list_duplicate_twitter:
            try:
                twitter_link_to_voter = TwitterLinkToVoter.objects.get(
                    voter_we_vote_id__iexact=one_duplicate_voter.we_vote_id)
                if positive_value_exists(twitter_link_to_voter.twitter_id):
                    one_duplicate_voter.twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                    # We reach out for the twitter_screen_name
                    one_duplicate_voter.twitter_screen_name_from_link_to_voter = \
                        twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
            except TwitterLinkToVoter.DoesNotExist:
                pass

                voter_list_duplicate_twitter_updated.append(one_duplicate_voter)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                        messages_on_stage,
        'organization':                             organization,
        'voter_linked_organization_we_vote_id_list': voter_linked_organization_we_vote_id_list_updated,
        'organization_list_with_duplicate_twitter': organization_list_with_duplicate_twitter_updated,
        'voter_list_duplicate_twitter':             voter_list_duplicate_twitter_updated,
        'twitter_link_to_this_organization_exists':     twitter_link_to_this_organization_exists,
        'twitter_link_to_another_organization_exists':  twitter_link_to_another_organization_exists,
    }
    response = render(request, 'admin_tools/data_cleanup_organization_analysis.html', template_values)

    return response


@login_required
def data_cleanup_organization_list_analysis_view(request):
    """
    Analyze all endorsers
    :param request:
    :return:
    """
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    create_twitter_link_to_organization = request.GET.get('create_twitter_link_to_organization', False)

    organization_list = Organization.objects.all()

    # Goal: Create TwitterLinkToOrganization
    # Goal: Look for opportunities to link Voters with Orgs

    # Cycle through all endorsers and identify which ones have duplicate Twitter data so we know
    #  we need to take a deeper look
    organizations_with_twitter_id = {}
    organizations_with_twitter_handle = {}
    duplicate_twitter_id_count = 0
    duplicate_twitter_handle_count = 0
    for one_organization in organization_list:
        if positive_value_exists(one_organization.twitter_user_id):
            twitter_user_id_string = str(one_organization.twitter_user_id)
            if twitter_user_id_string in organizations_with_twitter_id:
                organizations_with_twitter_id[twitter_user_id_string] += 1
            else:
                organizations_with_twitter_id[twitter_user_id_string] = 1
            if organizations_with_twitter_id[twitter_user_id_string] == 2:
                # Only update the counter the first time we find more than one entry
                duplicate_twitter_id_count += 1
        if positive_value_exists(one_organization.organization_twitter_handle):
            twitter_handle_string = str(one_organization.organization_twitter_handle)
            if twitter_handle_string in organizations_with_twitter_handle:
                organizations_with_twitter_handle[twitter_handle_string] += 1
            else:
                organizations_with_twitter_handle[twitter_handle_string] = 1
            if organizations_with_twitter_handle[twitter_handle_string] == 2:
                # Only update the counter the first time we find more than one entry
                duplicate_twitter_handle_count += 1

    # Cycle through the endorsers again. If the organization has a unique twitter_id and twitter_handle,
    #  proceed with tests:
    #  *) Is there a voter who is linked to this same Twitter account?
    #    *) Is that voter linked to a different Organization? (If so: Merge them,
    #       If not: add voter.linked_organization_we_vote_id)
    #    *) Update voter's positions with organization ID
    #    *) Update organization's positions with voter ID
    organizations_with_a_twitter_collision = []
    organizations_with_unique_twitter_data = []
    organizations_with_correctly_linked_twitter_data = []
    organizations_with_unique_twitter_data_count = 0
    organizations_with_correctly_linked_twitter_data_count = 0
    organizations_without_twitter_data_count = 0
    twitter_link_mismatch_count = 0
    twitter_user_manager = TwitterUserManager()
    for one_organization in organization_list:
        unique_twitter_user_id_found = False
        twitter_id_collision_found = False
        unique_twitter_handle_found = False
        twitter_handle_collision_found = False
        if positive_value_exists(one_organization.twitter_user_id):
            twitter_user_id_string = str(one_organization.twitter_user_id)
            if twitter_user_id_string in organizations_with_twitter_id:
                if organizations_with_twitter_id[twitter_user_id_string] == 1:
                    unique_twitter_user_id_found = True
                elif organizations_with_twitter_id[twitter_user_id_string] > 1:
                    twitter_id_collision_found = True

        if positive_value_exists(one_organization.organization_twitter_handle):
            twitter_handle_string = str(one_organization.organization_twitter_handle)
            if twitter_handle_string in organizations_with_twitter_handle:
                if organizations_with_twitter_handle[twitter_handle_string] == 1:
                    unique_twitter_handle_found = True
                elif organizations_with_twitter_handle[twitter_handle_string] > 1:
                    twitter_handle_collision_found = True

        twitter_collision_found = twitter_id_collision_found or twitter_handle_collision_found

        if unique_twitter_user_id_found or unique_twitter_handle_found and not twitter_collision_found:
            # If here, we know we have an organization without multiple twitter ids or handles

            # Retrieve the linked_voter
            linked_voter_exists = False
            try:
                linked_voter = Voter.objects.get(
                    linked_organization_we_vote_id__iexact=one_organization.we_vote_id)
                one_organization.linked_voter = linked_voter
                linked_voter_exists = True
            except Voter.DoesNotExist:
                pass

            # Check to see if there is an existing TwitterLinkToOrganization
            if positive_value_exists(one_organization.twitter_user_id):
                try:
                    twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                        twitter_id=one_organization.twitter_user_id)
                    if positive_value_exists(twitter_link_to_organization.organization_we_vote_id):
                        one_organization.organization_we_vote_id_from_link_to_organization = \
                            twitter_link_to_organization.organization_we_vote_id
                        one_organization.twitter_id_from_link_to_organization = twitter_link_to_organization.twitter_id
                        # We reach out for the twitter_screen_name
                        one_organization.twitter_screen_name_from_link_to_organization = \
                            twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()
                except TwitterLinkToOrganization.DoesNotExist:
                    pass
            elif positive_value_exists(one_organization.organization_twitter_handle):
                twitter_user_manager = TwitterUserManager()
                twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                    0, one_organization.organization_twitter_handle)
                if twitter_results['twitter_user_found']:
                    twitter_user = twitter_results['twitter_user']
                    twitter_id = twitter_user.twitter_id
                    try:
                        twitter_link_to_organization = TwitterLinkToOrganization.objects.get(twitter_id=twitter_id)
                        if positive_value_exists(twitter_link_to_organization.organization_we_vote_id):
                            one_organization.organization_we_vote_id_from_link_to_organization = \
                                twitter_link_to_organization.organization_we_vote_id
                            one_organization.twitter_id_from_link_to_organization = \
                                twitter_link_to_organization.twitter_id
                            one_organization.twitter_screen_name_from_link_to_organization = twitter_user.twitter_handle
                    except TwitterLinkToOrganization.DoesNotExist:
                        pass

            # Check to see if there is an existing TwitterLinkToVoter
            if positive_value_exists(one_organization.twitter_user_id):
                try:
                    twitter_link_to_voter = TwitterLinkToVoter.objects.get(
                        twitter_id=one_organization.twitter_user_id)
                    if positive_value_exists(twitter_link_to_voter.voter_we_vote_id):
                        one_organization.voter_we_vote_id_from_link_to_voter = twitter_link_to_voter.voter_we_vote_id
                        one_organization.twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                        # We reach out for the twitter_screen_name
                        one_organization.twitter_screen_name_from_link_to_voter = \
                            twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
                except TwitterLinkToVoter.DoesNotExist:
                    pass
            elif positive_value_exists(one_organization.organization_twitter_handle):
                twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                    0, one_organization.organization_twitter_handle)
                if twitter_results['twitter_user_found']:
                    twitter_user = twitter_results['twitter_user']
                    twitter_id = twitter_user.twitter_id
                    try:
                        twitter_link_to_voter = TwitterLinkToVoter.objects.get(twitter_id=twitter_id)
                        if positive_value_exists(twitter_link_to_voter.voter_we_vote_id):
                            one_organization.voter_we_vote_id_from_link_to_voter = \
                                twitter_link_to_voter.voter_we_vote_id
                            one_organization.twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                            one_organization.twitter_screen_name_from_link_to_voter = twitter_user.twitter_handle
                    except TwitterLinkToVoter.DoesNotExist:
                        pass

            # Are there any data mismatches?  TODO DALE

            # Does TwitterLinkToOrganization exist? If so, does it match Twitter account in TwitterLinkToVoter?
            if hasattr(one_organization, 'twitter_id_from_link_to_voter') and \
                    positive_value_exists(one_organization.twitter_id_from_link_to_voter) and \
                    hasattr(one_organization, 'twitter_id_from_link_to_organization') and \
                    positive_value_exists(one_organization.twitter_id_from_link_to_organization):
                if one_organization.twitter_id_from_link_to_voter != \
                        one_organization.twitter_id_from_link_to_organization:
                    one_organization.twitter_link_mismatch = True
                    twitter_link_mismatch_count += 1
            elif hasattr(one_organization, 'twitter_id_from_link_to_voter') and \
                    positive_value_exists(one_organization.twitter_id_from_link_to_voter) and \
                    positive_value_exists(one_organization.twitter_user_id):
                if one_organization.twitter_id_from_link_to_voter != \
                        one_organization.twitter_user_id:
                    one_organization.twitter_link_mismatch = True
                    twitter_link_mismatch_count += 1
            elif hasattr(one_organization, 'twitter_screen_name_from_link_to_voter') and \
                    positive_value_exists(one_organization.twitter_screen_name_from_link_to_voter) and \
                    positive_value_exists(one_organization.organization_twitter_handle):
                if one_organization.twitter_screen_name_from_link_to_voter != \
                        one_organization.organization_twitter_handle:
                    one_organization.twitter_link_mismatch = True
                    twitter_link_mismatch_count += 1

            # If there isn't a Twitter link mismatch, and create_twitter_link_to_organization is True, do it
            if create_twitter_link_to_organization \
                    and not hasattr(one_organization, 'twitter_id_from_link_to_organization') \
                    and not hasattr(one_organization, 'twitter_link_mismatch'):
                twitter_user_manager = TwitterUserManager()
                twitter_id_to_create = one_organization.twitter_user_id
                if positive_value_exists(one_organization.organization_twitter_handle) \
                        and not positive_value_exists(twitter_id_to_create):
                    twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(
                        0, one_organization.organization_twitter_handle)
                    if twitter_results['twitter_user_found']:
                        twitter_user = twitter_results['twitter_user']
                        twitter_id_to_create = twitter_user.twitter_id

                results = twitter_user_manager.create_twitter_link_to_organization(
                    twitter_id_to_create, one_organization.we_vote_id)
                if results['twitter_link_to_organization_saved']:
                    twitter_link_to_organization = results['twitter_link_to_organization']
                    one_organization.organization_we_vote_id_from_link_to_organization = \
                        twitter_link_to_organization.organization_we_vote_id
                    one_organization.twitter_id_from_link_to_organization = \
                        twitter_link_to_organization.twitter_id
                    one_organization.twitter_screen_name_from_link_to_organization = \
                        twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()

            if hasattr(one_organization, 'twitter_id_from_link_to_voter') and \
                    positive_value_exists(one_organization.twitter_id_from_link_to_voter) and \
                    hasattr(one_organization, 'twitter_id_from_link_to_organization') and \
                    positive_value_exists(one_organization.twitter_id_from_link_to_organization) and \
                    one_organization.twitter_id_from_link_to_voter == \
                    one_organization.twitter_id_from_link_to_organization:
                organizations_with_correctly_linked_twitter_data.append(one_organization)
                organizations_with_correctly_linked_twitter_data_count += 1
            else:
                organizations_with_unique_twitter_data.append(one_organization)
                organizations_with_unique_twitter_data_count += 1
        elif twitter_collision_found:
            organizations_with_a_twitter_collision.append(one_organization)
        elif not (unique_twitter_user_id_found or unique_twitter_handle_found):
            organizations_without_twitter_data_count += 1

    org_list_analysis_message = ""
    org_list_analysis_message += "duplicate_twitter_id_count: " + \
                                 str(duplicate_twitter_id_count) + "<br />"
    org_list_analysis_message += "duplicate_twitter_handle_count: " + \
                                 str(duplicate_twitter_handle_count) + "<br />"
    org_list_analysis_message += "organizations_with_correctly_linked_twitter_data_count: " + \
                                 str(organizations_with_correctly_linked_twitter_data_count) + "<br />"
    org_list_analysis_message += "organizations_with_unique_twitter_data_count: " + \
                                 str(organizations_with_unique_twitter_data_count) + "<br />"
    org_list_analysis_message += "organizations_without_twitter_data_count: " + \
                                 str(organizations_without_twitter_data_count) + "<br />"
    org_list_analysis_message += "twitter_link_mismatch_count: " + \
                                 str(twitter_link_mismatch_count) + "<br />"

    messages.add_message(request, messages.INFO, org_list_analysis_message)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                        messages_on_stage,
        'organizations_with_correctly_linked_twitter_data': organizations_with_correctly_linked_twitter_data,
        'organizations_with_unique_twitter_data':   organizations_with_unique_twitter_data,
        'organizations_with_a_twitter_collision':   organizations_with_a_twitter_collision,
    }
    response = render(request, 'admin_tools/data_cleanup_organization_list_analysis.html', template_values)

    return response


@login_required
def data_cleanup_position_list_analysis_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    organization_we_vote_id_added = 0
    organization_we_vote_id_added_failed = 0
    voter_we_vote_id_added = 0
    voter_we_vote_id_added_failed = 0

    candidate_manager = CandidateManager()
    measure_manager = ContestMeasureManager()
    organization_manager = OrganizationManager()
    voter_manager = VoterManager()

    google_civic_election_id = convert_to_int(request.GET.get('google_civic_election_id', 0))
    election_list = Election.objects.order_by('-election_day_text')

    add_election_id = request.GET.get('add_election_id', False)
    add_organization_to_position_owner = request.GET.get('add_organization_to_position_owner', False)

    # #######################
    # REPAIR CODE
    # PositionEntered: Find Positions that have an organization_id but not an organization_we_vote_id and repair
    public_positions_with_organization_id_only = PositionEntered.objects.all()
    if positive_value_exists(google_civic_election_id):
        public_positions_with_organization_id_only = public_positions_with_organization_id_only.filter(
            google_civic_election_id=google_civic_election_id)
    public_positions_with_organization_id_only = \
        public_positions_with_organization_id_only.filter(organization_id__gt=0)
    public_positions_with_organization_id_only = public_positions_with_organization_id_only.filter(
        Q(organization_we_vote_id=None) | Q(organization_we_vote_id=""))
    # We limit these to 20 since we are doing other lookup
    public_positions_with_organization_id_only = public_positions_with_organization_id_only[:200]
    for one_position in public_positions_with_organization_id_only:
        results = organization_manager.retrieve_organization_from_id(one_position.organization_id)
        if results['organization_found']:
            try:
                organization = results['organization']
                one_position.organization_we_vote_id = organization.we_vote_id
                one_position.save()
                organization_we_vote_id_added += 1
            except Exception as e:  # Look for positions where:
                organization_we_vote_id_added_failed += 1

    # PositionForFriends: Find Positions that have an organization_id but not an organization_we_vote_id and repair
    public_positions_with_organization_id_only = PositionForFriends.objects.all()
    if positive_value_exists(google_civic_election_id):
        public_positions_with_organization_id_only = public_positions_with_organization_id_only.filter(
            google_civic_election_id=google_civic_election_id)
    public_positions_with_organization_id_only = \
        public_positions_with_organization_id_only.filter(organization_id__gt=0)
    public_positions_with_organization_id_only = public_positions_with_organization_id_only.filter(
        Q(organization_we_vote_id=None) | Q(organization_we_vote_id=""))
    # We limit these to 20 since we are doing other lookup
    public_positions_with_organization_id_only = public_positions_with_organization_id_only[:200]
    for one_position in public_positions_with_organization_id_only:
        results = organization_manager.retrieve_organization_from_id(one_position.organization_id)
        if results['organization_found']:
            try:
                organization = results['organization']
                one_position.organization_we_vote_id = organization.we_vote_id
                one_position.save()
                organization_we_vote_id_added += 1
            except Exception as e:  # Look for positions where:
                organization_we_vote_id_added_failed += 1

    # PositionEntered: Find Positions that have a voter_id but not a voter_we_vote_id
    public_positions_with_voter_id_only = PositionEntered.objects.all()
    if positive_value_exists(google_civic_election_id):
        public_positions_with_voter_id_only = public_positions_with_voter_id_only.filter(
            google_civic_election_id=google_civic_election_id)
    public_positions_with_voter_id_only = \
        public_positions_with_voter_id_only.filter(voter_id__gt=0)
    public_positions_with_voter_id_only = public_positions_with_voter_id_only.filter(
        Q(voter_we_vote_id=None) | Q(voter_we_vote_id=""))
    # We limit these to 20 since we are doing other lookup
    public_positions_with_voter_id_only = public_positions_with_voter_id_only[:200]
    for one_position in public_positions_with_voter_id_only:
        results = voter_manager.retrieve_voter_by_id(one_position.voter_id)
        if results['voter_found']:
            try:
                voter = results['voter']
                one_position.voter_we_vote_id = voter.we_vote_id
                one_position.save()
                voter_we_vote_id_added += 1
            except Exception as e:  # Look for positions where:
                voter_we_vote_id_added_failed += 1

    # PositionForFriends: Find Positions that have a voter_id but not a voter_we_vote_id
    positions_for_friends_with_voter_id_only = PositionForFriends.objects.all()
    if positive_value_exists(google_civic_election_id):
        positions_for_friends_with_voter_id_only = positions_for_friends_with_voter_id_only.filter(
            google_civic_election_id=google_civic_election_id)
    positions_for_friends_with_voter_id_only = \
        positions_for_friends_with_voter_id_only.filter(voter_id__gt=0)
    positions_for_friends_with_voter_id_only = positions_for_friends_with_voter_id_only.filter(
        Q(voter_we_vote_id=None) | Q(voter_we_vote_id=""))
    # We limit these to 20 since we are doing other lookup
    positions_for_friends_with_voter_id_only = positions_for_friends_with_voter_id_only[:200]
    for one_position in positions_for_friends_with_voter_id_only:
        results = voter_manager.retrieve_voter_by_id(one_position.voter_id)
        if results['voter_found']:
            try:
                voter = results['voter']
                one_position.voter_we_vote_id = voter.we_vote_id
                one_position.save()
                voter_we_vote_id_added += 1
            except Exception as e:  # Look for positions where:
                voter_we_vote_id_added_failed += 1

    # Heal data: Make sure that we have a google_civic_election_id for all positions
    # PositionEntered: Find Positions that have a candidate_we_vote_id, or contest_measure_we_vote_id,
    # but no google_civic_election_id, and update with the correct google_civic_election_id
    public_positions_without_election_id = PositionEntered.objects.all()
    public_positions_without_election_id = public_positions_without_election_id.filter(
        Q(google_civic_election_id=None) | Q(google_civic_election_id=0))
    public_positions_without_election_id_count = public_positions_without_election_id.count()
    google_civic_id_added_to_public_position = 0
    google_civic_id_not_added_to_public_position = 0
    if add_election_id:
        # We limit these to x so we don't time-out the page
        public_positions_without_election_id = public_positions_without_election_id[:2000]
        for one_position in public_positions_without_election_id:
            if positive_value_exists(one_position.candidate_campaign_id):
                # Retrieve the candidate and get the election it is for
                candidate_results = candidate_manager.retrieve_candidate_from_id(
                    one_position.candidate_campaign_id)
                if candidate_results['candidate_found']:
                    candidate = candidate_results['candidate']
                    if positive_value_exists(candidate.google_civic_election_id):
                        try:
                            one_position.google_civic_election_id = candidate.google_civic_election_id
                            one_position.save()
                            google_civic_id_added_to_public_position += 1
                        except Exception as e:
                            google_civic_id_not_added_to_public_position += 1
                    else:
                        google_civic_id_not_added_to_public_position += 1
            elif positive_value_exists(one_position.contest_measure_id):
                # Retrieve the measure and get the election it is for
                measure_results = measure_manager.retrieve_contest_measure_from_id(
                    one_position.contest_measure_id)
                if measure_results['contest_measure_found']:
                    measure = measure_results['contest_measure']
                    if positive_value_exists(measure.google_civic_election_id):
                        try:
                            one_position.google_civic_election_id = measure.google_civic_election_id
                            one_position.save()
                            google_civic_id_added_to_public_position += 1
                        except Exception as e:
                            google_civic_id_not_added_to_public_position += 1
                    else:
                        google_civic_id_not_added_to_public_position += 1
            else:
                google_civic_id_not_added_to_public_position += 1
        # Now get the updated count
        public_positions_without_election_id = PositionEntered.objects.all()
        public_positions_without_election_id = public_positions_without_election_id.filter(
            Q(google_civic_election_id=None) | Q(google_civic_election_id=0))
        public_positions_without_election_id_count = public_positions_without_election_id.count()

    # PositionForFriends: Find Positions that have a candidate_we_vote_id, or contest_measure_we_vote_id,
    # but no google_civic_election_id, and update with the correct google_civic_election_id
    positions_for_friends_without_election_id = PositionForFriends.objects.all()
    positions_for_friends_without_election_id = positions_for_friends_without_election_id.filter(
        Q(google_civic_election_id=None) | Q(google_civic_election_id=0))
    positions_for_friends_without_election_id_count = positions_for_friends_without_election_id.count()
    google_civic_id_added_to_friends_position = 0
    google_civic_id_not_added_to_friends_position = 0
    if add_election_id:
        # We limit these to x so we don't time-out the page
        positions_for_friends_without_election_id = positions_for_friends_without_election_id[:2000]
        for one_position in positions_for_friends_without_election_id:
            if positive_value_exists(one_position.candidate_campaign_id):
                # Retrieve the candidate and get the election it is for
                candidate_results = candidate_manager.retrieve_candidate_from_id(
                    one_position.candidate_campaign_id)
                if candidate_results['candidate_found']:
                    candidate = candidate_results['candidate']
                    if positive_value_exists(candidate.google_civic_election_id):
                        try:
                            one_position.google_civic_election_id = candidate.google_civic_election_id
                            one_position.save()
                            google_civic_id_added_to_friends_position += 1
                        except Exception as e:
                            google_civic_id_not_added_to_friends_position += 1
                    else:
                        google_civic_id_not_added_to_friends_position += 1
                else:
                    google_civic_id_not_added_to_friends_position += 1
            elif positive_value_exists(one_position.contest_measure_id):
                # Retrieve the measure and get the election it is for
                measure_results = measure_manager.retrieve_contest_measure_from_id(
                    one_position.contest_measure_id)
                if measure_results['contest_measure_found']:
                    measure = measure_results['contest_measure']
                    if positive_value_exists(measure.google_civic_election_id):
                        try:
                            one_position.google_civic_election_id = measure.google_civic_election_id
                            one_position.save()
                            google_civic_id_added_to_friends_position += 1
                        except Exception as e:
                            google_civic_id_not_added_to_friends_position += 1
                    else:
                        google_civic_id_not_added_to_friends_position += 1
                else:
                    google_civic_id_not_added_to_friends_position += 1
            else:
                google_civic_id_not_added_to_friends_position += 1
        # Now get the updated count
        positions_for_friends_without_election_id = PositionForFriends.objects.all()
        positions_for_friends_without_election_id = positions_for_friends_without_election_id.filter(
            Q(google_civic_election_id=None) | Q(google_civic_election_id=0))
        positions_for_friends_without_election_id_count = positions_for_friends_without_election_id.count()

    # *) voter_we_vote_id doesn't match organization_we_vote_id
    # *) In public position table, an organization_we_vote_id doesn't exist

    # These are Positions that should have an organization_we_vote_id but do not
    #  We know they should have a organization_we_vote_id because they are in the PositionEntered table
    public_positions_without_organization = PositionEntered.objects.all()
    if positive_value_exists(google_civic_election_id):
        public_positions_without_organization = public_positions_without_organization.filter(
            google_civic_election_id=google_civic_election_id)
    public_positions_without_organization = public_positions_without_organization.filter(
        Q(organization_we_vote_id=None) | Q(organization_we_vote_id=""))
    # Exclude positions without a connection to a voter
    public_positions_without_organization = public_positions_without_organization.exclude(
        Q(voter_we_vote_id=None) | Q(voter_we_vote_id=""))
    public_positions_without_organization_count = public_positions_without_organization.count()
    # We limit these to 20 since we are doing other lookup
    public_positions_without_organization = public_positions_without_organization[:200]
    if add_organization_to_position_owner:
        for one_position in public_positions_without_organization:
            add_organization_to_position_owner_local(one_position.voter_id, one_position)
        # Update this data for display
        public_positions_without_organization = PositionEntered.objects.all()
        if positive_value_exists(google_civic_election_id):
            public_positions_without_organization = public_positions_without_organization.filter(
                google_civic_election_id=google_civic_election_id)
        public_positions_without_organization = public_positions_without_organization.filter(
            Q(organization_we_vote_id=None) | Q(organization_we_vote_id=""))
        # Exclude positions without a connection to a voter
        public_positions_without_organization = public_positions_without_organization.exclude(
            Q(voter_we_vote_id=None) | Q(voter_we_vote_id=""))
        public_positions_without_organization_count = public_positions_without_organization.count()
        # We limit these to 20 since we are doing other lookup
        public_positions_without_organization = public_positions_without_organization[:200]

    # PositionsForFriends without organization_we_vote_id
    positions_for_friends_without_organization = PositionForFriends.objects.all()
    if positive_value_exists(google_civic_election_id):
        positions_for_friends_without_organization = positions_for_friends_without_organization.filter(
            google_civic_election_id=google_civic_election_id)
    positions_for_friends_without_organization = positions_for_friends_without_organization.filter(
        Q(organization_we_vote_id=None) | Q(organization_we_vote_id=""))
    positions_for_friends_without_organization_count = positions_for_friends_without_organization.count()
    # We limit these to 20 since we are doing other lookup
    positions_for_friends_without_organization = positions_for_friends_without_organization[:200]
    if add_organization_to_position_owner:
        for one_position in positions_for_friends_without_organization:
            add_organization_to_position_owner_local(one_position.voter_id, one_position)
        # Update this data for display
        positions_for_friends_without_organization = PositionForFriends.objects.all()
        if positive_value_exists(google_civic_election_id):
            positions_for_friends_without_organization = positions_for_friends_without_organization.filter(
                google_civic_election_id=google_civic_election_id)
        positions_for_friends_without_organization = positions_for_friends_without_organization.filter(
            Q(organization_we_vote_id=None) | Q(organization_we_vote_id=""))
        positions_for_friends_without_organization_count = positions_for_friends_without_organization.count()
        # We limit these to 20 since we are doing other lookup
        positions_for_friends_without_organization = positions_for_friends_without_organization[:200]

    position_list_analysis_message = ""
    position_list_analysis_message += "organization_we_vote_id_added: " + \
                                      str(organization_we_vote_id_added) + "<br />"
    position_list_analysis_message += "organization_we_vote_id_added_failed: " + \
                                      str(organization_we_vote_id_added_failed) + "<br />"
    position_list_analysis_message += "voter_we_vote_id_added: " + \
                                      str(voter_we_vote_id_added) + "<br />"
    position_list_analysis_message += "voter_we_vote_id_added_failed: " + \
                                      str(voter_we_vote_id_added_failed) + "<br />"
    position_list_analysis_message += "public_positions_without_organization_count: " + \
                                      str(public_positions_without_organization_count) + "<br />"
    position_list_analysis_message += "positions_for_friends_without_organization_count: " + \
                                      str(positions_for_friends_without_organization_count) + "<br />"
    position_list_analysis_message += "public_positions_without_election_id_count: " + \
                                      str(public_positions_without_election_id_count) + "<br />"
    position_list_analysis_message += "positions_for_friends_without_election_id_count: " + \
                                      str(positions_for_friends_without_election_id_count) + "<br />"

    position_list_success = False
    position_list_success_message = ""
    if google_civic_id_added_to_public_position:
        position_list_success = True
        position_list_success_message += "google_civic_id_added_to_public_position: " + \
                                         str(google_civic_id_added_to_public_position) + "<br />"
    if google_civic_id_added_to_friends_position:
        position_list_success = True
        position_list_success_message += "google_civic_id_added_to_friends_position: " + \
                                         str(google_civic_id_added_to_friends_position) + "<br />"

    position_list_error = False
    position_list_error_message = ""
    if google_civic_id_not_added_to_public_position:
        position_list_error = True
        position_list_error_message += "google_civic_id_not_added_to_public_position: " + \
                                       str(google_civic_id_not_added_to_public_position) + "<br />"
    if google_civic_id_not_added_to_friends_position:
        position_list_error = True
        position_list_error_message += "google_civic_id_not_added_to_friends_position: " + \
                                       str(google_civic_id_not_added_to_friends_position) + "<br />"

    messages.add_message(request, messages.INFO, position_list_analysis_message)
    if position_list_success:
        messages.add_message(request, messages.SUCCESS, position_list_success_message)
    if position_list_error:
        messages.add_message(request, messages.ERROR, position_list_error_message)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                            messages_on_stage,
        'election_list':                                election_list,
        'google_civic_election_id':                     google_civic_election_id,
        'public_positions_without_organization':        public_positions_without_organization,
        'positions_for_friends_without_organization':   positions_for_friends_without_organization,
        'public_positions_with_organization_id_only':   public_positions_with_organization_id_only,
        'public_positions_without_election_id_count':   public_positions_without_election_id_count,
        'positions_for_friends_without_election_id_count':  positions_for_friends_without_election_id_count,
    }
    response = render(request, 'admin_tools/data_cleanup_position_list_analysis.html', template_values)

    return response


def add_organization_to_position_owner_local(voter_id, one_position):
    """
    This is a local function used in the data_cleanup_position_list_analysis_view
    :param voter_id:
    :param one_position:
    :return:
    """
    organization_manager = OrganizationManager()
    voter_manager = VoterManager()
    if not positive_value_exists(voter_id):
        return
    # if one_position.voter_id in organization_already_created_for_voter:
    #     continue
    voter_results = voter_manager.retrieve_voter(voter_id)
    if not voter_results['voter_found']:
        return
    voter = voter_results['voter']
    # If here, we know that we have a voter
    # Is there a linked_organization_we_vote_id from the voter record?
    if positive_value_exists(voter.linked_organization_we_vote_id):
        # If we are here, then we know this voter already has an organization that needs to be linked
        organization_results = organization_manager.retrieve_organization_from_we_vote_id(
            voter.linked_organization_we_vote_id)
        if organization_results['organization_found']:
            organization = organization_results['organization']
            try:
                one_position.organization_id = organization.id
                one_position.organization_we_vote_id = organization.we_vote_id
                one_position.save()
                return
            except Exception as e:
                return

    # If there isn't a linked_organization_we_vote_id, check to see if this voter has a TwitterLinkedToVoter
    # entry that matches an OrganizationLinkedToVoter entry
    voter_twitter_id = voter_manager.fetch_twitter_id_from_voter_we_vote_id(voter.we_vote_id)
    organization_second_results = organization_manager.retrieve_organization_from_twitter_user_id(
        voter_twitter_id)
    if organization_second_results['organization_found']:
        organization = organization_second_results['organization']
        try:
            voter.linked_organization_we_vote_id = organization.we_vote_id
            voter.save()
            try:
                one_position.organization_id = organization.id
                one_position.organization_we_vote_id = organization.we_vote_id
                one_position.save()
                return
            except Exception as e:
                return
        except Exception as e:
            pass

    # If not, create a new organization
    organization_name = voter.get_full_name()
    organization_type = INDIVIDUAL
    organization_image = voter.voter_photo_url()
    create_results = organization_manager.create_organization(
        organization_name=organization_name,
        organization_image=organization_image,
        organization_type=organization_type,
        we_vote_hosted_profile_image_url_large=voter.we_vote_hosted_profile_image_url_large,
        we_vote_hosted_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
        we_vote_hosted_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny
    )
    if create_results['organization_created']:
        organization = create_results['organization']
        try:
            voter.linked_organization_we_vote_id = organization.we_vote_id
            voter.save()
        except Exception as e:
            pass
    else:
        pass
    return


@login_required
def data_cleanup_voter_hanging_data_process_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # Find any Voter entries where there is any email data, and then below check the EmailAddress table
    #  to see if there is an entry
    voter_hanging_email_ownership_is_verified_list = Voter.objects.all()
    voter_hanging_email_ownership_is_verified_list = voter_hanging_email_ownership_is_verified_list.filter(
        email_ownership_is_verified=True)
    voter_hanging_email_ownership_is_verified_list = voter_hanging_email_ownership_is_verified_list

    voter_email_print_list = ""
    email_ownership_is_verified_set_to_false_count = 0
    voter_emails_cleared_out = 0
    primary_email_not_found = 0
    primary_email_not_found_note = ""
    verified_email_addresses = 0
    voter_owner_of_email_not_found = 0
    voter_owner_new_primary_email_saved = 0
    voter_owner_new_primary_email_failed = 0
    voter_owner_new_primary_email_failed_note = ""
    for one_voter in voter_hanging_email_ownership_is_verified_list:
        # Clean if it is the simplest case of email_ownership_is_verified, but email and primary_email_we_vote_id None
        # voter_email_print_list += "voter.email: " + str(one_voter.email) + ", "
        # voter_email_print_list += "voter.primary_email_we_vote_id: " + str(one_voter.primary_email_we_vote_id) + ", "
        # voter_email_print_list += "voter.email_ownership_is_verified: " + str(one_voter.email_ownership_is_verified)
        # voter_email_print_list += " :: <br />"
        if positive_value_exists(one_voter.email_ownership_is_verified) and \
                one_voter.email is None and \
                one_voter.primary_email_we_vote_id is None:
            # If here, then the voter entry incorrectly thinks it has a verified email saved
            one_voter.email_ownership_is_verified = False
            one_voter.save()
            email_ownership_is_verified_set_to_false_count += 1
        elif positive_value_exists(one_voter.email_ownership_is_verified) and \
                one_voter.email is not None and \
                one_voter.primary_email_we_vote_id is None:
            # If here, an email value exists, but we don't have a primary_email_we_vote_id listed
            # Check to see if the email can be made the primary TODO DALE
            pass
        elif positive_value_exists(one_voter.primary_email_we_vote_id):
            # Is there an EmailAddress entry matching this primary_email_we_vote_id?
            try:
                verified_email_address = EmailAddress.objects.get(
                    we_vote_id=one_voter.primary_email_we_vote_id,
                    email_ownership_is_verified=True,
                    # email_permanent_bounce=False,
                    deleted=False
                )
                # Does this master EmailAddress entry agree that this voter owns this email
                if verified_email_address.voter_we_vote_id == one_voter.we_vote_id:
                    # Make sure the cached email address matches
                    if one_voter.email != verified_email_address.normalized_email_address:
                        try:
                            one_voter.email = verified_email_address.normalized_email_address
                            one_voter.save()
                        except Exception as e:
                            pass
                else:
                    # Clear out this email from the voter table
                    try:
                        one_voter.email = None
                        one_voter.primary_email_we_vote_id = None
                        one_voter.email_ownership_is_verified = False
                        one_voter.save()
                        voter_emails_cleared_out += 1
                    except Exception as e:
                        pass
            except EmailAddress.DoesNotExist:
                # primary_email_we_vote_id could not be found, so we may need to clear out this email from  voter table
                primary_email_not_found += 1
                # primary_email_not_found_note += one_voter.primary_email_we_vote_id + " "
                try:
                    one_voter.email = None
                    one_voter.primary_email_we_vote_id = None
                    one_voter.email_ownership_is_verified = False
                    one_voter.save()
                except Exception as e:
                    pass

    # Go through all of the verified email addresses in the EmailAddress table and make sure the
    # cached information is up-to-date in the voter table
    email_address_verified_list = EmailAddress.objects.all()
    email_address_verified_list = email_address_verified_list.filter(email_ownership_is_verified=True)
    for one_email in email_address_verified_list:
        if positive_value_exists(one_email.voter_we_vote_id):
            verified_email_addresses += 1
            try:
                voter_owner_of_email = Voter.objects.get(we_vote_id__iexact=one_email.voter_we_vote_id)
                # Does this voter already have a primary email address?
                if positive_value_exists(voter_owner_of_email.primary_email_we_vote_id):
                    # Leave it in place
                    pass
                else:
                    # Otherwise save the first email for this person as the primary
                    try:
                        voter_owner_of_email.email = one_email.normalized_email_address
                        voter_owner_of_email.primary_email_we_vote_id = one_email.we_vote_id
                        voter_owner_of_email.email_ownership_is_verified = True
                        voter_owner_of_email.save()
                        voter_owner_new_primary_email_saved += 1
                    except Exception as e:
                        voter_owner_new_primary_email_failed += 1
                        voter_owner_new_primary_email_failed_note += one_email.we_vote_id + " "
            except Exception as e:
                voter_owner_of_email_not_found += 1

    voter_email_print_list += "email_ownership_is_verified, reset to False: " + \
                              str(email_ownership_is_verified_set_to_false_count) + " <br />"
    voter_email_print_list += "voter_emails_cleared_out: " + \
                              str(voter_emails_cleared_out) + " <br />"
    voter_email_print_list += "primary_email_not_found: " + \
                              str(primary_email_not_found) + " " + primary_email_not_found_note + "<br />"
    voter_email_print_list += "verified_email_addresses: " + \
                              str(verified_email_addresses) + "<br />"
    voter_email_print_list += "voter_owner_of_email_not_found: " + \
                              str(voter_owner_of_email_not_found) + "<br />"
    voter_email_print_list += "voter_owner_new_primary_email_saved: " + \
                              str(voter_owner_new_primary_email_saved) + "<br />"
    voter_email_print_list += "voter_owner_new_primary_email_failed: " + \
                              str(voter_owner_new_primary_email_failed) + " " + \
                              voter_owner_new_primary_email_failed_note + "<br />"

    messages.add_message(request, messages.INFO, voter_email_print_list)

    return HttpResponseRedirect(reverse('admin_tools:data_cleanup', args=()))


@login_required
def data_cleanup_voter_list_analysis_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    create_facebook_link_to_voter = request.GET.get('create_facebook_link_to_voter', False)
    create_twitter_link_to_voter = request.GET.get('create_twitter_link_to_voter', False)
    updated_suggested_friends = request.GET.get('updated_suggested_friends', False)

    status_print_list = ""
    create_facebook_link_to_voter_possible = 0
    create_facebook_link_to_voter_added = 0
    create_facebook_link_to_voter_not_added = 0
    create_twitter_link_to_voter_possible = 0
    create_twitter_link_to_voter_added = 0
    create_twitter_link_to_voter_not_added = 0
    voter_address_manager = VoterAddressManager()
    facebook_manager = FacebookManager()
    twitter_user_manager = TwitterUserManager()
    friend_manager = FriendManager()
    position_metrics_manager = PositionMetricsManager()

    suggested_friend_created_count = 0
    if updated_suggested_friends:
        current_friends_results = CurrentFriend.objects.all()

        for one_current_friend in current_friends_results:
            # Start with one_current_friend.viewer_voter_we_vote_id, get a list of all of that voter's friends
            results = friend_manager.update_suggested_friends_starting_with_one_voter(
                one_current_friend.viewer_voter_we_vote_id)
            if results['suggested_friend_created_count']:
                suggested_friend_created_count += results['suggested_friend_created_count']

            # Then do the other side of the friendship - the viewee
            results = friend_manager.update_suggested_friends_starting_with_one_voter(
                one_current_friend.viewee_voter_we_vote_id)
            if results['suggested_friend_created_count']:
                suggested_friend_created_count += results['suggested_friend_created_count']

    voter_list_with_sign_in_data_query = Voter.objects.order_by('-id', '-date_last_changed')
    voter_list_with_sign_in_data_query = voter_list_with_sign_in_data_query.filter(
        ~Q(twitter_id=None) | ~Q(twitter_screen_name=None) | ~Q(email=None) | ~Q(facebook_id=None) |
        ~Q(fb_username=None) | ~Q(linked_organization_we_vote_id=None))
    voter_list_with_sign_in_data = voter_list_with_sign_in_data_query[:100]

    voter_list_with_sign_in_data_updated = []
    number_of_voters_found = 0
    for one_linked_voter in voter_list_with_sign_in_data:
        number_of_voters_found += 1

        one_linked_voter.text_for_map_search = \
            voter_address_manager.retrieve_text_for_map_search_from_voter_id(one_linked_voter.id)

        # Get FacebookLinkToVoter
        facebook_id_from_link_to_voter = 0
        try:
            facebook_link_to_voter = FacebookLinkToVoter.objects.get(
                voter_we_vote_id__iexact=one_linked_voter.we_vote_id)
            if positive_value_exists(facebook_link_to_voter.facebook_user_id):
                facebook_id_from_link_to_voter = facebook_link_to_voter.facebook_user_id
                one_linked_voter.facebook_id_from_link_to_voter = facebook_link_to_voter.facebook_user_id
        except FacebookLinkToVoter.DoesNotExist:
            pass

        # Get TwitterLinkToVoter
        twitter_id_from_link_to_voter = 0
        try:
            twitter_link_to_voter = TwitterLinkToVoter.objects.get(
                voter_we_vote_id__iexact=one_linked_voter.we_vote_id)
            if positive_value_exists(twitter_link_to_voter.twitter_id):
                twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                one_linked_voter.twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                # We reach out for the twitter_screen_name
                one_linked_voter.twitter_screen_name_from_link_to_voter = \
                    twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
        except TwitterLinkToVoter.DoesNotExist:
            pass

        # Get TwitterLinkToOrganization
        try:
            one_linked_voter.twitter_link_to_organization_status = ""
            if positive_value_exists(twitter_id_from_link_to_voter):
                twitter_id_to_search = twitter_id_from_link_to_voter
                twitter_link_to_organization_twitter_id_source_text = "FROM TW_LINK_TO_VOTER"
            else:
                twitter_id_to_search = one_linked_voter.twitter_id
                twitter_link_to_organization_twitter_id_source_text = "FROM VOTER RECORD"

            if positive_value_exists(twitter_id_to_search):
                twitter_link_to_organization = TwitterLinkToOrganization.objects.get(
                    twitter_id=twitter_id_to_search)
                if positive_value_exists(twitter_link_to_organization.twitter_id):
                    one_linked_voter.organization_we_vote_id_from_link_to_organization = \
                        twitter_link_to_organization.organization_we_vote_id
                    one_linked_voter.twitter_id_from_link_to_organization = twitter_link_to_organization.twitter_id
                    # We reach out for the twitter_screen_name
                    one_linked_voter.twitter_screen_name_from_link_to_organization = \
                        twitter_link_to_organization.fetch_twitter_handle_locally_or_remotely()
                    one_linked_voter.twitter_link_to_organization_twitter_id_source_text = \
                        twitter_link_to_organization_twitter_id_source_text
        except TwitterLinkToOrganization.DoesNotExist:
            pass

        # Do any other voters have this Facebook data? If not, we can create a FacebookLinkToVoter entry.
        duplicate_facebook_data_found = False
        voter_raw_filters = []
        if positive_value_exists(one_linked_voter.facebook_id):
            new_voter_filter = Q(facebook_id=one_linked_voter.facebook_id)
            voter_raw_filters.append(new_voter_filter)

        if len(voter_raw_filters):
            final_voter_filters = voter_raw_filters.pop()

            # ...and "OR" the remaining items in the list
            for item in voter_raw_filters:
                final_voter_filters |= item

            duplicate_facebook_data_voter_list = Voter.objects.all()
            duplicate_facebook_data_voter_list = duplicate_facebook_data_voter_list.filter(final_voter_filters)
            duplicate_facebook_data_voter_list = duplicate_facebook_data_voter_list.exclude(
                we_vote_id__iexact=one_linked_voter.we_vote_id)
            duplicate_facebook_data_found = positive_value_exists(len(duplicate_facebook_data_voter_list))
            one_linked_voter.duplicate_facebook_data_found = duplicate_facebook_data_found

        if facebook_id_from_link_to_voter or duplicate_facebook_data_found:
            # Do not offer the create_facebook_link
            pass
        else:
            if positive_value_exists(one_linked_voter.facebook_id):
                if create_facebook_link_to_voter:
                    # If here, we want to create a FacebookLinkToVoter
                    create_results = facebook_manager.create_facebook_link_to_voter(one_linked_voter.facebook_id,
                                                                                    one_linked_voter.we_vote_id)
                    if positive_value_exists(create_results['facebook_link_to_voter_saved']):
                        create_facebook_link_to_voter_added += 1
                        facebook_link_to_voter = create_results['facebook_link_to_voter']
                        if positive_value_exists(facebook_link_to_voter.facebook_user_id):
                            one_linked_voter.facebook_id_from_link_to_voter = facebook_link_to_voter.facebook_user_id
                    else:
                        create_facebook_link_to_voter_not_added += 1
                else:
                    create_facebook_link_to_voter_possible += 1

        # Do any other voters have this Twitter data? If not, we can create a TwitterLinkToVoter entry.
        duplicate_twitter_data_found = False
        voter_raw_filters = []
        if positive_value_exists(one_linked_voter.twitter_id):
            new_voter_filter = Q(twitter_id=one_linked_voter.twitter_id)
            voter_raw_filters.append(new_voter_filter)
        if positive_value_exists(one_linked_voter.twitter_screen_name):
            new_voter_filter = Q(twitter_screen_name__iexact=one_linked_voter.twitter_screen_name)
            voter_raw_filters.append(new_voter_filter)

        if len(voter_raw_filters):
            final_voter_filters = voter_raw_filters.pop()

            # ...and "OR" the remaining items in the list
            for item in voter_raw_filters:
                final_voter_filters |= item

            duplicate_twitter_data_voter_list = Voter.objects.all()
            duplicate_twitter_data_voter_list = duplicate_twitter_data_voter_list.filter(final_voter_filters)
            duplicate_twitter_data_voter_list = duplicate_twitter_data_voter_list.exclude(
                we_vote_id__iexact=one_linked_voter.we_vote_id)
            duplicate_twitter_data_found = positive_value_exists(len(duplicate_twitter_data_voter_list))
            one_linked_voter.duplicate_twitter_data_found = duplicate_twitter_data_found

        if twitter_id_from_link_to_voter or duplicate_twitter_data_found:
            # Do not offer the create_twitter_link
            pass
        else:
            if positive_value_exists(one_linked_voter.twitter_id) \
                    or positive_value_exists(one_linked_voter.twitter_screen_name):
                if create_twitter_link_to_voter:
                    # If here, we want to create a TwitterLinkToVoter
                    create_results = twitter_user_manager.create_twitter_link_to_voter(one_linked_voter.twitter_id,
                                                                                       one_linked_voter.we_vote_id)
                    if positive_value_exists(create_results['twitter_link_to_voter_saved']):
                        create_twitter_link_to_voter_added += 1
                        twitter_link_to_voter = create_results['twitter_link_to_voter']
                        if positive_value_exists(twitter_link_to_voter.twitter_id):
                            one_linked_voter.twitter_id_from_link_to_voter = twitter_link_to_voter.twitter_id
                            # We reach out for the twitter_screen_name
                            one_linked_voter.twitter_screen_name_from_link_to_voter = \
                                twitter_link_to_voter.fetch_twitter_handle_locally_or_remotely()
                            one_linked_voter.twitter_link_to_organization_twitter_id_source_text = " JUST ALTERED"
                    else:
                        create_twitter_link_to_voter_not_added += 1
                else:
                    create_twitter_link_to_voter_possible += 1

        one_linked_voter.links_to_other_organizations = \
            find_organizations_referenced_in_positions_for_this_voter(one_linked_voter)
        one_linked_voter.positions_count = \
            position_metrics_manager.fetch_positions_count_for_this_voter(one_linked_voter)

        email_address_list = EmailAddress.objects.all()
        email_address_list = email_address_list.filter(voter_we_vote_id__iexact=one_linked_voter.we_vote_id)
        one_linked_voter.linked_emails = email_address_list

        # Friend statistics
        one_linked_voter.current_friends_count = \
            friend_manager.fetch_current_friends_count(one_linked_voter.we_vote_id)
        one_linked_voter.friend_invitations_sent_by_me_count = \
            friend_manager.fetch_friend_invitations_sent_by_me_count(one_linked_voter.we_vote_id)
        one_linked_voter.friend_invitations_sent_to_me_count = \
            friend_manager.fetch_friend_invitations_sent_to_me_count(one_linked_voter.we_vote_id)
        one_linked_voter.suggested_friend_list_count = \
            friend_manager.fetch_suggested_friends_count(one_linked_voter.we_vote_id)
        follow_list_manager = FollowOrganizationList()
        one_linked_voter.organizations_followed_count = \
            follow_list_manager.fetch_follow_organization_by_voter_id_count(one_linked_voter.id)

        voter_list_with_sign_in_data_updated.append(one_linked_voter)

    status_print_list += "create_facebook_link_to_voter_possible: " + \
                         str(create_facebook_link_to_voter_possible) + ", "
    if positive_value_exists(create_facebook_link_to_voter_added):
        status_print_list += "create_facebook_link_to_voter_added: " + \
                             str(create_facebook_link_to_voter_added) + "<br />"
    if positive_value_exists(create_facebook_link_to_voter_not_added):
        status_print_list += "create_facebook_link_to_voter_not_added: " + \
                             str(create_facebook_link_to_voter_not_added) + "<br />"
    status_print_list += "create_twitter_link_to_voter_possible: " + \
                         str(create_twitter_link_to_voter_possible) + ", "
    if positive_value_exists(create_twitter_link_to_voter_added):
        status_print_list += "create_twitter_link_to_voter_added: " + \
                             str(create_twitter_link_to_voter_added) + "<br />"
    if positive_value_exists(create_twitter_link_to_voter_not_added):
        status_print_list += "create_twitter_link_to_voter_not_added: " + \
                             str(create_twitter_link_to_voter_not_added) + "<br />"
    status_print_list += "number_of_voters_found: " + \
                         str(number_of_voters_found) + "<br />"
    if positive_value_exists(suggested_friend_created_count):
        status_print_list += "suggested_friend_created_count: " + \
                             str(suggested_friend_created_count) + "<br />"

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                  messages_on_stage,
        'voter_list_with_sign_in_data':       voter_list_with_sign_in_data_updated,
    }
    response = render(request, 'admin_tools/data_cleanup_voter_list_analysis.html', template_values)

    return response


@login_required
def data_voter_statistics_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    status_print_list = ""
    create_facebook_link_to_voter_possible = 0
    create_facebook_link_to_voter_added = 0

    # ####################################
    # Information about Total Voters
    # ####################################
    current_friend_query = CurrentFriend.objects.all()
    current_friend_count = current_friend_query.count()

    voter_list_with_sign_in_data = Voter.objects.all()
    voter_list_with_sign_in_data = voter_list_with_sign_in_data.filter(
        ~Q(twitter_id=None) | ~Q(twitter_screen_name=None) | ~Q(email=None) | ~Q(facebook_id=None) |
        ~Q(fb_username=None) | ~Q(linked_organization_we_vote_id=None))
    voter_list_with_sign_in_data_count = voter_list_with_sign_in_data.count()

    suggested_friend_query = SuggestedFriend.objects.all()
    suggested_friend_count = suggested_friend_query.count()

    # ####################################
    # Statistics by Election
    # ####################################
    election_statistics = []
    election_query = Election.objects.order_by('-google_civic_election_id')
    number_of_voters_found = 0
    for one_election in election_query:
        if not positive_value_exists(one_election.google_civic_election_id):
            # Skip this entry if missing google_civic_election_id
            continue
        election_values_exist = False
        # ################################
        # For this election, how many addresses were saved?
        address_query = VoterAddress.objects.all()
        address_query = address_query.filter(google_civic_election_id=one_election.google_civic_election_id)
        one_election.voter_address_count = address_query.count()
        if positive_value_exists(one_election.voter_address_count):
            election_values_exist = True

        # ################################
        # For this election, how many BallotSaved entries were saved for voters?
        ballot_saved_query = VoterBallotSaved.objects.all()
        ballot_saved_query = ballot_saved_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        ballot_saved_query = ballot_saved_query.exclude(
            voter_id=0)
        one_election.voter_ballot_saved_count = ballot_saved_query.count()
        if positive_value_exists(one_election.voter_ballot_saved_count):
            election_values_exist = True

        # ################################
        # For this election, how many BallotReturned entries were saved for voters?
        ballot_returned_query = BallotReturned.objects.all()
        ballot_returned_query = ballot_returned_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        ballot_returned_query = ballot_returned_query.exclude(
            voter_id=0)
        ballot_returned_query = ballot_returned_query.exclude(
            voter_id=None)
        one_election.voter_ballot_returned_count = ballot_returned_query.count()
        if positive_value_exists(one_election.voter_ballot_returned_count):
            election_values_exist = True

        # ################################
        # For this election, how many individual voters saved at least one Public PositionEntered entry?
        voter_position_entered_query = PositionEntered.objects.all()
        voter_position_entered_query = voter_position_entered_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        voter_position_entered_query = voter_position_entered_query.exclude(
            voter_we_vote_id=None)
        voter_position_entered_query = voter_position_entered_query.values("voter_we_vote_id").distinct()
        one_election.voters_with_public_positions_count = voter_position_entered_query.count()
        if positive_value_exists(one_election.voters_with_public_positions_count):
            election_values_exist = True

        # ################################
        # For this election, how many Public PositionEntered entries were saved by voters?
        voter_position_entered_query = PositionEntered.objects.all()
        voter_position_entered_query = voter_position_entered_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        voter_position_entered_query = voter_position_entered_query.exclude(
            voter_we_vote_id=None)
        one_election.voter_position_entered_count = voter_position_entered_query.count()
        if positive_value_exists(one_election.voter_position_entered_count):
            election_values_exist = True

        # ################################
        # For this election, how many individual voters saved at least one PositionForFriends entry?
        voter_position_for_friends_query = PositionForFriends.objects.all()
        # As of Aug 2018 we are no longer using PERCENT_RATING
        voter_position_for_friends_query = voter_position_for_friends_query.exclude(stance__iexact='PERCENT_RATING')
        voter_position_for_friends_query = voter_position_for_friends_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        voter_position_for_friends_query = voter_position_for_friends_query.exclude(
            voter_we_vote_id=None)
        voter_position_for_friends_query = voter_position_for_friends_query.values("voter_we_vote_id").distinct()
        one_election.voters_with_positions_for_friends_count = voter_position_for_friends_query.count()
        if positive_value_exists(one_election.voters_with_positions_for_friends_count):
            election_values_exist = True

        # ################################
        # For this election, how many Public PositionForFriends entries were saved by voters?
        voter_position_for_friends_query = PositionForFriends.objects.all()
        # As of Aug 2018 we are no longer using PERCENT_RATING
        voter_position_for_friends_query = voter_position_for_friends_query.exclude(stance__iexact='PERCENT_RATING')
        voter_position_for_friends_query = voter_position_for_friends_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        one_election.voter_position_for_friends_count = voter_position_for_friends_query.count()
        if positive_value_exists(one_election.voter_position_for_friends_count):
            election_values_exist = True

        # NOT VOTER SPECIFIC

        # ################################
        # For this election, how many BallotReturned entries were saved for map points?
        ballot_returned_query = BallotReturned.objects.all()
        ballot_returned_query = ballot_returned_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        ballot_returned_query = ballot_returned_query.exclude(
            polling_location_we_vote_id=None)
        one_election.polling_location_ballot_returned_count = ballot_returned_query.count()
        # if positive_value_exists(one_election.polling_location_ballot_returned_count):
        #     election_values_exist = True

        # ################################
        # For this election, how many endorsers shared at least one Public PositionEntered entry?
        organization_position_entered_query = PositionEntered.objects.all()
        organization_position_entered_query = organization_position_entered_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        organization_position_entered_query = organization_position_entered_query.exclude(
            organization_we_vote_id=None)
        organization_position_entered_query = \
            organization_position_entered_query.values("organization_we_vote_id").distinct()
        one_election.organizations_with_public_positions_count = organization_position_entered_query.count()
        # if positive_value_exists(one_election.organizations_with_public_positions_count):
        #     election_values_exist = True

        # ################################
        # For this election, how many Public PositionEntered entries were for endorsers?
        organization_position_entered_query = PositionEntered.objects.all()
        organization_position_entered_query = organization_position_entered_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        organization_position_entered_query = organization_position_entered_query.exclude(
            organization_we_vote_id=None)
        one_election.organization_position_entered_count = organization_position_entered_query.count()
        # if positive_value_exists(one_election.organization_position_entered_count):
        #     election_values_exist = True

        # ################################
        # For this election, how many ContestOffices
        contest_office_query = ContestOffice.objects.all()
        contest_office_query = contest_office_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        one_election.number_of_offices = contest_office_query.count()
        # if positive_value_exists(one_election.number_of_offices):
        #     election_values_exist = True

        # ################################
        # For this election, how many CandidateCampaign
        candidate_query = CandidateCampaign.objects.all()
        candidate_query = candidate_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        one_election.number_of_candidates = candidate_query.count()
        # if positive_value_exists(one_election.number_of_candidates):
        #     election_values_exist = True

        # ################################
        # For this election, how many ContestMeasures
        contest_measure_query = ContestMeasure.objects.all()
        contest_measure_query = contest_measure_query.filter(
            google_civic_election_id=one_election.google_civic_election_id)
        one_election.number_of_measures = contest_measure_query.count()
        # if positive_value_exists(one_election.number_of_measures):
        #     election_values_exist = True

        if election_values_exist:
            election_statistics.append(one_election)

    # status_print_list += "create_facebook_link_to_voter_possible: " + \
    #                      str(create_facebook_link_to_voter_possible) + ", "
    # if positive_value_exists(create_facebook_link_to_voter_added):
    #     status_print_list += "create_facebook_link_to_voter_added: " + \
    #                          str(create_facebook_link_to_voter_added) + "<br />"
    # status_print_list += "number_of_voters_found: " + \
    #                      str(number_of_voters_found) + "<br />"

    messages.add_message(request, messages.INFO, status_print_list)

    messages_on_stage = get_messages(request)

    template_values = {
        'messages_on_stage':                    messages_on_stage,
        'current_friend_count':                 current_friend_count,
        'election_statistics':                  election_statistics,
        'suggested_friend_count':               suggested_friend_count,
        'voter_list_with_sign_in_data_count':   voter_list_with_sign_in_data_count,
    }
    response = render(request, 'admin_tools/data_voter_statistics.html', template_values)

    return response


@login_required
def delete_test_data_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # We leave in place the map points data and the election data from Google civic

    # Delete candidate data from exported file

    # Delete organization data from exported file

    # Delete positions data from exported file
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))


@login_required
def import_sample_data_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # This routine works without requiring a Google Civic API key

    # We want to make sure that all voters have been updated to have a we_vote_id
    voter_list = Voter.objects.all()
    for one_voter in voter_list:
        one_voter.save()

    polling_locations_results = import_and_save_all_polling_locations_data()

    # NOTE: The approach of having each developer pull directly from Google Civic won't work because if we are going
    # to import positions, we need to have stable we_vote_ids for all ballot items
    # =========================
    # # We redirect to the view that calls out to Google Civic and brings in ballot data
    # # This isn't ideal (I'd rather call a controller instead of redirecting to a view), but this is a unique case
    # # and we have a lot of error-display-to-screen code
    # election_local_id = 0
    # google_civic_election_id = 4162  # Virginia
    # return HttpResponseRedirect(reverse('election:election_all_ballots_retrieve',
    #                                     args=(election_local_id,)) +
    #                             "?google_civic_election_id=" + str(google_civic_election_id))

    # Import election data from We Vote export file
    elections_results = elections_import_from_sample_file()

    # Import ContestOffices
    load_from_uri = False
    offices_results = offices_import_from_sample_file(request, load_from_uri)

    # Import candidate data from We Vote export file
    load_from_uri = False
    candidates_results = candidates_import_from_sample_file(request, load_from_uri)

    # Import ContestMeasures

    # Import organization data from We Vote export file
    load_from_uri = False
    organizations_results = organizations_import_from_sample_file(request, load_from_uri)

    # Import positions data from We Vote export file
    # load_from_uri = False
    positions_results = positions_import_from_sample_file(request)  # , load_from_uri

    messages.add_message(request, messages.INFO,
                         'The following data has been imported: <br />'
                         'Polling locations saved: {polling_locations_saved}, updated: {polling_locations_updated},'
                         ' not_processed: {polling_locations_not_processed} <br />'
                         'Elections saved: {elections_saved}, updated: {elections_updated},'
                         ' not_processed: {elections_not_processed} <br />'
                         'Offices saved: {offices_saved}, updated: {offices_updated},'
                         ' not_processed: {offices_not_processed} <br />'
                         'Candidates saved: {candidates_saved}, updated: {candidates_updated},'
                         ' not_processed: {candidates_not_processed} <br />'
                         'Endorsers saved: {organizations_saved}, updated: {organizations_updated},'
                         ' not_processed: {organizations_not_processed} <br />'
                         'Positions saved: {positions_saved}, updated: {positions_updated},'
                         ' not_processed: {positions_not_processed} <br />'
                         ''.format(
                             polling_locations_saved=polling_locations_results['saved'],
                             polling_locations_updated=polling_locations_results['updated'],
                             polling_locations_not_processed=polling_locations_results['not_processed'],
                             elections_saved=elections_results['saved'],
                             elections_updated=elections_results['updated'],
                             elections_not_processed=elections_results['not_processed'],
                             offices_saved=offices_results['saved'],
                             offices_updated=offices_results['updated'],
                             offices_not_processed=offices_results['not_processed'],
                             candidates_saved=candidates_results['saved'],
                             candidates_updated=candidates_results['updated'],
                             candidates_not_processed=candidates_results['not_processed'],
                             organizations_saved=organizations_results['saved'],
                             organizations_updated=organizations_results['updated'],
                             organizations_not_processed=organizations_results['not_processed'],
                             positions_saved=positions_results['saved'],
                             positions_updated=positions_results['updated'],
                             positions_not_processed=positions_results['not_processed'],
                         ))
    return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))


def login_we_vote(request):
    """
    This method is called when you login from the /login/ form on the API server
    :param request:
    :return:
    """
    voter_api_device_id = get_voter_api_device_id(request)  # We look in the cookies for voter_api_device_id
    if hasattr(request, 'facebook'):
        facebook_object = request.facebook
        facebook_data = getattr(facebook_object, 'social_user', None)
    else:
        facebook_data = None
    store_new_voter_api_device_id_in_cookie = False
    voter_signed_in = False

    voter_manager = VoterManager()
    voter_device_link_manager = VoterDeviceLinkManager()
    results = voter_manager.retrieve_voter_from_voter_device_id(voter_api_device_id, read_only=True)
    if results['voter_found']:
        voter_on_stage = results['voter']
        voter_on_stage_id = voter_on_stage.id
        # Just because a We Vote voter is found doesn't mean they are authenticated for Django
    else:
        voter_on_stage_id = 0

    info_message = ''
    error_message = ''
    username = ''

    # Does Django think user is already signed in?
    if request.user.is_authenticated:
        # If so, make sure user and voter_on_stage are the same.
        if request.user.id != voter_on_stage_id:
            # Delete the prior voter_api_device_id from database
            voter_device_link_manager.delete_voter_device_link(voter_api_device_id)

            # Create a new voter_api_device_id and voter_device_link
            voter_api_device_id = generate_voter_device_id()
            results = voter_device_link_manager.save_new_voter_device_link(voter_api_device_id, request.user.id)
            store_new_voter_api_device_id_in_cookie = results['voter_device_link_created']
            voter_on_stage = request.user
            voter_on_stage_id = voter_on_stage.id
    elif request.POST:
        password = request.POST.get('password')
        input_username = request.POST.get('username').strip()
        # Retrieve user email address (as entered when account created) to avoid issue from WV-284
        # Login Admin login page email field being case-sensitive
        # Maybe in future can be dealt with by making emails in db all lowercase and lower-casing new user emails
        user_obj = Voter.objects.filter(email__iexact=input_username).first()
        if user_obj:
            username = user_obj.email
        else:
            # Find the voter based on authenticated emails
            queryset = EmailAddress.objects.filter(normalized_email_address__iexact=input_username)
            queryset = queryset.filter(email_ownership_is_verified=True)
            email_address_obj = queryset.first()
            if email_address_obj:
                voter_we_vote_id = email_address_obj.voter_we_vote_id
                user_obj = Voter.objects.filter(we_vote_id__iexact=voter_we_vote_id).get()
                username = user_obj.email
            else:
                username = None

        if positive_value_exists(username):
            user = authenticate(username=username, password=password)
        else:
            user = None
        if user is not None:
            if user.is_active:
                login(request, user)
                info_message = "You're successfully logged in!"

                # Delete the prior voter_api_device_id from database
                voter_device_link_manager.delete_voter_device_link(voter_api_device_id)

                # Create a new voter_api_device_id and voter_device_link
                voter_api_device_id = generate_voter_device_id()
                results = voter_device_link_manager.save_new_voter_device_link(voter_api_device_id, user.id)
                store_new_voter_api_device_id_in_cookie = results['voter_device_link_created']
            else:
                error_message = "Your account is not active, please contact the site admin."

            if user.id != voter_on_stage_id:
                # Eventually we want to merge voter_on_stage into user account
                pass
        else:
            error_message = "Your username and/or password were incorrect."
    elif not positive_value_exists(voter_on_stage_id):
        # If here, delete the prior voter_api_device_id from database
        voter_device_link_manager.delete_voter_device_link(voter_api_device_id)

        # We then need to set a voter_api_device_id cookie and create a new voter (even though not signed in)
        results = voter_setup(request)
        voter_api_device_id = results['voter_api_device_id']
        store_new_voter_api_device_id_in_cookie = results['store_new_voter_api_device_id_in_cookie']

    # Does Django think user is signed in?
    if request.user.is_authenticated:
        voter_signed_in = True
    else:
        info_message = "Please log in below..."

    if positive_value_exists(error_message):
        messages.add_message(request, messages.ERROR, error_message)
    if positive_value_exists(info_message):
        messages.add_message(request, messages.INFO, info_message)

    messages_on_stage = get_messages(request)
    template_values = {
        'request':              request,
        'username':             username,
        'next':                 '.',
        'voter_signed_in':      voter_signed_in,
        'messages_on_stage':    messages_on_stage,
    }
    response = render(request, 'registration/login_we_vote.html', template_values)

    # If login with facebook then save facebook details in facebookAuthResponse and facebookLinkToVoter
    if facebook_data:
        facebook_user_data = getattr(facebook_data, 'user', None)
        facebook_user_first_name = getattr(facebook_user_data, 'first_name', '')
        facebook_user_middle_name = getattr(facebook_user_data, 'middle_name', '')
        facebook_user_last_name = getattr(facebook_user_data, 'last_name', '')
        facebook_user_email = getattr(facebook_user_data, 'email', '')
        facebook_user_we_vote_id = getattr(facebook_user_data, 'we_vote_id', '')
        facebook_access_token = getattr(facebook_data, 'access_token', '')
        facebook_user_id = getattr(facebook_data, 'uid', 0)
        facebook_user_manager = FacebookManager()
        if positive_value_exists(facebook_access_token) and positive_value_exists(facebook_user_id):
            facebook_auth_response_results = facebook_user_manager.update_or_create_facebook_auth_response(
                voter_api_device_id, facebook_access_token, facebook_user_id, 0, '', facebook_user_email,
                facebook_user_first_name, facebook_user_middle_name, facebook_user_last_name, '', '', '', '')

        if positive_value_exists(facebook_user_id) and positive_value_exists(facebook_user_we_vote_id):
            facebook_link_results = facebook_user_manager.create_facebook_link_to_voter(facebook_user_id,
                                                                                        facebook_user_we_vote_id)

    # We want to store the voter_api_device_id cookie if it is new
    if positive_value_exists(voter_api_device_id) and positive_value_exists(store_new_voter_api_device_id_in_cookie):
        set_voter_api_device_id(request, response, voter_api_device_id)

    return response


def logout_we_vote(request):
    logout(request)

    info_message = "You are now signed out."
    messages.add_message(request, messages.INFO, info_message)

    messages_on_stage = get_messages(request)
    template_values = {
        'request':              request,
        'next':                 '/admin/',
        'messages_on_stage':    messages_on_stage,
    }
    response = render(request, 'registration/login_we_vote.html', template_values)

    # Find current voter_api_device_id
    voter_api_device_id = get_voter_api_device_id(request)

    delete_voter_api_device_id_cookie(response)

    # Now delete voter_api_device_id from database
    voter_device_link_manager = VoterDeviceLinkManager()
    voter_device_link_manager.delete_voter_device_link(voter_api_device_id)

    return response


def redirect_to_sign_in_page(request, authority_required={}):
    authority_required_text = ''
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    for each_authority in authority_required:
        if each_authority == 'admin':
            authority_required_text += ' or ' if len(authority_required_text) > 0 else ''
            authority_required_text += 'has Admin rights'
        if each_authority == 'analytics_admin':
            authority_required_text += ' or ' if len(authority_required_text) > 0 else ''
            authority_required_text += 'has Analytics Admin rights'
        if each_authority == 'partner_organization':
            authority_required_text += ' or ' if len(authority_required_text) > 0 else ''
            authority_required_text += 'has Partner Organization rights'
        if each_authority == 'political_data_manager':
            authority_required_text += ' or ' if len(authority_required_text) > 0 else ''
            authority_required_text += 'has Political Data Manager rights'
        if each_authority == 'political_data_viewer':
            authority_required_text += ' or ' if len(authority_required_text) > 0 else ''
            authority_required_text += 'has Political Data Viewer rights'
        if each_authority == 'verified_volunteer':
            authority_required_text += ' or ' if len(authority_required_text) > 0 else ''
            authority_required_text += 'has Verified Volunteer rights'
    error_message = "You must sign in with account that {authority_required_text} to see that page. " \
                    "-- NOTE: There is a known bug with this check, if you think this message is wrong, " \
                    "Sign Out and try again".format(authority_required_text=authority_required_text)

    messages.add_message(request, messages.ERROR, error_message)

    if positive_value_exists(request.path):
        next_url_variable = '?next=' + request.path
    else:
        next_url_variable = ''
    return HttpResponseRedirect(LOGIN_URL + next_url_variable)


@login_required
def statistics_summary_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'verified_volunteer'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    # ballotpedia_api_counter_manager = BallotpediaApiCounterManager()
    # ballotpedia_daily_summary_list = ballotpedia_api_counter_manager.retrieve_daily_summaries()
    ctcl_api_counter_manager = CTCLApiCounterManager()
    ctcl_daily_summary_list = ctcl_api_counter_manager.retrieve_daily_summaries(days_to_display=15)

    google_civic_api_counter_manager = GoogleCivicApiCounterManager()
    google_civic_daily_summary_list = google_civic_api_counter_manager.retrieve_daily_summaries(days_to_display=15)

    # Statistics are not being stored currently DALE 2024-01-22
    # sendgrid_api_counter_manager = SendGridApiCounterManager()
    # sendgrid_daily_summary_list = sendgrid_api_counter_manager.retrieve_daily_summaries(days_to_display=15)

    # vote_smart_api_counter_manager = VoteSmartApiCounterManager()
    # vote_smart_daily_summary_list = vote_smart_api_counter_manager.retrieve_daily_summaries()

    # targetsmart_api_counter_manager = TargetSmartApiCounterManager()
    # targetsmart_daily_summary_list = targetsmart_api_counter_manager.retrieve_daily_summaries()

    twitter_api_counter_manager = TwitterApiCounterManager()
    twitter_daily_summary_list = twitter_api_counter_manager.retrieve_daily_summaries(days_to_display=15)
    twitter_api_limits = retrieve_twitter_rate_limit_info()

    vote_usa_api_counter_manager = VoteUSAApiCounterManager()
    vote_usa_daily_summary_list = vote_usa_api_counter_manager.retrieve_daily_summaries(days_to_display=15)

    template_values = {
        'ctcl_daily_summary_list':          ctcl_daily_summary_list,
        'google_civic_daily_summary_list':  google_civic_daily_summary_list,
        'twitter_daily_summary_list':       twitter_daily_summary_list,
        'twitter_api_limits':               twitter_api_limits,
        'vote_usa_daily_summary_list':      vote_usa_daily_summary_list,
        # 'ballotpedia_daily_summary_list':   ballotpedia_daily_summary_list,
        # 'sendgrid_daily_summary_list':      sendgrid_daily_summary_list,
        # 'vote_smart_daily_summary_list':    vote_smart_daily_summary_list,
        # 'targetsmart_daily_summary_list':   targetsmart_daily_summary_list,
    }
    response = render(request, 'admin_tools/statistics_summary.html', template_values)

    return response


@login_required
def sync_data_with_master_servers_view(request):
    # admin, analytics_admin, partner_organization, political_data_manager, political_data_viewer, verified_volunteer
    authority_required = {'admin'}
    if not voter_has_authority(request, authority_required):
        return redirect_to_sign_in_page(request, authority_required)

    if WE_VOTE_SERVER_ROOT_URL in ELECTIONS_SYNC_URL:
        messages.add_message(request, messages.ERROR, "Cannot sync with Master We Vote Server -- "
                                                      "this is the Master We Vote Server.")
        return HttpResponseRedirect(reverse('admin_tools:admin_home', args=()))

    google_civic_election_id = request.GET.get('google_civic_election_id', '')
    state_code = request.GET.get('state_code', '')

    election_list = Election.objects.order_by('-election_day_text')

    state_list = STATE_CODE_MAP
    sorted_state_list = sorted(state_list.items())

    template_values = {
        'election_list':                election_list,
        'google_civic_election_id':     google_civic_election_id,
        'state_list':                   sorted_state_list,
        'state_code':                   state_code,

        'ballot_items_sync_url':        BALLOT_ITEMS_SYNC_URL,
        'ballot_returned_sync_url':     BALLOT_RETURNED_SYNC_URL,
        'candidates_sync_url':          CANDIDATES_SYNC_URL,
        'elections_sync_url':           ELECTIONS_SYNC_URL,
        'issues_sync_url':              ISSUES_SYNC_URL,
        'measures_sync_url':            MEASURES_SYNC_URL,
        'offices_sync_url':             OFFICES_SYNC_URL,
        'organizations_sync_url':       ORGANIZATIONS_SYNC_URL,
        'organization_link_to_issue_sync_url':  ORGANIZATION_LINK_TO_ISSUE_SYNC_URL,
        'politicians_sync_url':         POLITICIANS_SYNC_URL,
        'polling_locations_sync_url':   POLLING_LOCATIONS_SYNC_URL,
        'positions_sync_url':           POSITIONS_SYNC_URL,
        'voter_guides_sync_url':        VOTER_GUIDES_SYNC_URL,
    }
    response = render(request, 'admin_tools/sync_data_with_master_dashboard.html', template_values)

    return response
