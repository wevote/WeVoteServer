# apis_v1/views_docs.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-
from .documentation_source import ballot_item_options_retrieve_doc, ballot_item_retrieve_doc, \
    ballot_items_sync_out_doc, ballot_returned_sync_out_doc, \
    candidate_retrieve_doc, \
    candidates_retrieve_doc, candidates_sync_out_doc, device_id_generate_doc, \
    elections_sync_out_doc, facebook_disconnect_doc, friend_invitation_by_email_send_doc, \
    friend_invitation_by_email_verify_doc, friend_invitation_by_we_vote_id_send_doc, \
    friend_invite_response_doc, friend_list_doc, \
    measure_retrieve_doc, measures_sync_out_doc, \
    office_retrieve_doc, offices_sync_out_doc, \
    organization_count_doc, organizations_followed_retrieve_doc, \
    organization_follow_doc, organization_follow_ignore_doc, organization_stop_following_doc, \
    organization_retrieve_doc, organization_save_doc, organization_search_doc, organizations_sync_out_doc, \
    organization_suggestion_tasks_doc, \
    polling_locations_sync_out_doc, \
    position_like_count_doc, position_list_for_ballot_item_doc, position_list_for_opinion_maker_doc, \
    position_list_for_voter_doc, position_oppose_count_for_ballot_item_doc, \
    position_public_oppose_count_for_ballot_item_doc, position_retrieve_doc, position_save_doc, \
    positions_sync_out_doc, \
    position_public_support_count_for_ballot_item_doc, position_support_count_for_ballot_item_doc, \
    positions_count_for_all_ballot_items_doc, positions_count_for_one_ballot_item_doc, \
    quick_info_retrieve_doc, search_all_doc, twitter_identity_retrieve_doc, \
    twitter_sign_in_request_access_token_doc, twitter_sign_in_request_voter_info_doc, twitter_sign_in_retrieve_doc, \
    twitter_sign_in_start_doc, voter_address_retrieve_doc, voter_address_save_doc, \
    voter_all_positions_retrieve_doc, voter_all_stars_status_retrieve_doc, \
    voter_ballot_items_retrieve_doc, voter_ballot_items_retrieve_from_google_civic_doc, voter_count_doc, \
    voter_create_doc, \
    voter_email_address_retrieve_doc, voter_email_address_save_doc, \
    voter_email_address_sign_in_doc, voter_email_address_verify_doc, voter_facebook_save_to_current_account_doc, \
    voter_facebook_sign_in_retrieve_doc, voter_facebook_sign_in_save_doc, \
    voter_guide_possibility_retrieve_doc, voter_guide_possibility_save_doc, \
    voter_guides_followed_retrieve_doc, voter_guides_sync_out_doc, voter_guides_to_follow_retrieve_doc, \
    voter_location_retrieve_from_ip_doc, voter_merge_two_accounts_doc, voter_photo_save_doc, \
    voter_position_like_off_save_doc, voter_position_like_on_save_doc, voter_position_like_status_retrieve_doc, \
    voter_position_comment_save_doc, voter_position_retrieve_doc, voter_position_visibility_save_doc, \
    voter_opposing_save_doc, voter_retrieve_doc, voter_sign_out_doc, voter_star_off_save_doc, voter_star_on_save_doc, \
    voter_star_status_retrieve_doc, voter_stop_opposing_save_doc, \
    voter_stop_supporting_save_doc, voter_supporting_save_doc, voter_twitter_save_to_current_account_doc, \
    voter_update_doc
from config.base import get_environment_variable
from django.contrib.messages import get_messages
from django.shortcuts import render
from voter.models import voter_setup
from wevote_functions.functions import get_voter_api_device_id, set_voter_api_device_id, positive_value_exists

WE_VOTE_SERVER_ROOT_URL = get_environment_variable("WE_VOTE_SERVER_ROOT_URL")


def apis_index_doc_view(request):
    """
    Show a list of available APIs
    """
    # Create a voter_device_id and voter in the database if one doesn't exist yet
    results = voter_setup(request)
    voter_api_device_id = results['voter_api_device_id']
    store_new_voter_api_device_id_in_cookie = results['store_new_voter_api_device_id_in_cookie']

    messages_on_stage = get_messages(request)
    template_values = {
        'next': next,
        'messages_on_stage': messages_on_stage,
    }
    response = render(request, 'apis_v1/apis_index.html', template_values)

    # We want to store the voter_device_id cookie if it is new
    if positive_value_exists(voter_api_device_id) and positive_value_exists(store_new_voter_api_device_id_in_cookie):
        set_voter_api_device_id(request, response, voter_api_device_id)

    return response


def ballot_item_options_retrieve_doc_view(request):
    """
    Show documentation about ballotItemOptionsRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = ballot_item_options_retrieve_doc.ballot_item_options_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def ballot_item_retrieve_doc_view(request):
    """
    Show documentation about ballotItemRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = ballot_item_retrieve_doc.ballot_item_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def ballot_items_sync_out_doc_view(request):
    """
    Show documentation about ballotItemsSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = ballot_items_sync_out_doc.ballot_items_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def ballot_returned_sync_out_doc_view(request):
    """
    Show documentation about ballotReturnedSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = ballot_returned_sync_out_doc.ballot_returned_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def candidate_retrieve_doc_view(request):
    """
    Show documentation about candidateRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = candidate_retrieve_doc.candidate_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def candidates_retrieve_doc_view(request):
    """
    Show documentation about candidatesRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = candidates_retrieve_doc.candidates_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def candidates_sync_out_doc_view(request):
    """
    Show documentation about candidatesSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = candidates_sync_out_doc.candidates_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def device_id_generate_doc_view(request):
    """
    Show documentation about deviceIdGenerate
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = device_id_generate_doc.device_id_generate_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def elections_sync_out_doc_view(request):
    """
    Show documentation about electionsSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = elections_sync_out_doc.elections_sync_out_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def facebook_disconnect_doc_view(request):
    """
    Show documentation about facebookDisconnect
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = facebook_disconnect_doc.facebook_disconnect_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_facebook_save_to_current_account_doc_view(request):
    """
    Show documentation about voterFacebookSaveToCurrentAccount
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = \
        voter_facebook_save_to_current_account_doc.voter_facebook_save_to_current_account_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def friend_invitation_by_email_send_doc_view(request):
    """
    Show documentation about friendInvitationByEmailSend
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = friend_invitation_by_email_send_doc.friend_invitation_by_email_send_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def friend_invitation_by_we_vote_id_send_doc_view(request):
    """
    Show documentation about friendInvitationByWeVoteIdSend
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = friend_invitation_by_we_vote_id_send_doc.friend_invitation_by_we_vote_id_send_doc_template_values(
        url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def friend_invitation_by_email_verify_doc_view(request):
    """
    Show documentation about friendInvitationByEmailVerify
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = friend_invitation_by_email_verify_doc.friend_invitation_by_email_verify_doc_template_values(
        url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def friend_invite_response_doc_view(request):
    """
    Show documentation about friendInviteResponse
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = friend_invite_response_doc.friend_invite_response_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def friend_list_doc_view(request):
    """
    Show documentation about friendList
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = friend_list_doc.friend_list_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def measure_retrieve_doc_view(request):
    """
    Show documentation about candidatesRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = measure_retrieve_doc.measure_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def measures_sync_out_doc_view(request):
    """
    Show documentation about measuresSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = measures_sync_out_doc.measures_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def office_retrieve_doc_view(request):
    """
    Show documentation about candidatesRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = office_retrieve_doc.office_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def offices_sync_out_doc_view(request):
    """
    Show documentation about officesSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = offices_sync_out_doc.offices_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_count_doc_view(request):
    """
    Show documentation about organizationCount
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organization_count_doc.organization_count_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_follow_doc_view(request):
    """
    Show documentation about organizationFollow
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organization_follow_doc.organization_follow_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organizations_followed_retrieve_doc_view(request):
    """
    Show documentation about organizationsFollowedRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organizations_followed_retrieve_doc.organizations_followed_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_follow_ignore_doc_view(request):
    """
    Show documentation about organizationFollowIgnore
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organization_follow_ignore_doc.organization_follow_ignore_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_stop_following_doc_view(request):
    """
    Show documentation about organizationStopFollowing
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organization_stop_following_doc.organization_stop_following_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_retrieve_doc_view(request):
    """
    Show documentation about organizationRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL

    template_values = organization_retrieve_doc.organization_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_save_doc_view(request):
    """
    Show documentation about organizationSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organization_save_doc.organization_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_search_doc_view(request):
    """
    Show documentation about organizationSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organization_search_doc.organization_search_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organizations_sync_out_doc_view(request):
    """
    Show documentation about organizationsSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organizations_sync_out_doc.organizations_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def organization_suggestion_tasks_doc_view(request):
    """
    Show documentation about organizationSuggestionTasks
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = organization_suggestion_tasks_doc.organization_suggestion_tasks_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_list_for_ballot_item_doc_view(request):
    """
    Show documentation about positionListForBallotItem
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_list_for_ballot_item_doc.position_list_for_ballot_item_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_list_for_opinion_maker_doc_view(request):
    """
    Show documentation about positionListForOpinionMaker
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_list_for_opinion_maker_doc.position_list_for_opinion_maker_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_list_for_voter_doc_view(request):
    """
    Show documentation about positionListForVoter
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_list_for_voter_doc.position_list_for_voter_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_retrieve_doc_view(request):
    """
    Show documentation about positionRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL

    template_values = position_retrieve_doc.position_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_save_doc_view(request):
    """
    Show documentation about positionSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_save_doc.position_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_oppose_count_for_ballot_item_doc_view(request):
    """
    Show documentation about positionOpposeCountForBallotItem
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_oppose_count_for_ballot_item_doc.\
        position_oppose_count_for_ballot_item_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_support_count_for_ballot_item_doc_view(request):
    """
    Show documentation about positionSupportCountForBallotItem
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_support_count_for_ballot_item_doc.\
        position_support_count_for_ballot_item_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_public_oppose_count_for_ballot_item_doc_view(request):
    """
    Show documentation about positionPublicOpposeCountForBallotItem
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_public_oppose_count_for_ballot_item_doc.\
        position_public_oppose_count_for_ballot_item_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_public_support_count_for_ballot_item_doc_view(request):
    """
    Show documentation about positionPublicSupportCountForBallotItem
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_public_support_count_for_ballot_item_doc.\
        position_public_support_count_for_ballot_item_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def positions_count_for_all_ballot_items_doc_view(request):
    """
    Show documentation about positionsCountForAllBallotItems
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = positions_count_for_all_ballot_items_doc.positions_count_for_all_ballot_items_doc_template_values(
        url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def positions_count_for_one_ballot_item_doc_view(request):
    """
    Show documentation about positionsCountForOneBallotItem
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = positions_count_for_one_ballot_item_doc.positions_count_for_one_ballot_item_doc_template_values(
        url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def positions_sync_out_doc_view(request):
    """
    Show documentation about positionsSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = positions_sync_out_doc.positions_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def quick_info_retrieve_doc_view(request):
    """
    Show documentation about quickInfoRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = quick_info_retrieve_doc.\
        quick_info_retrieve_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def search_all_doc_view(request):
    """
    Show documentation about searchAll
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = search_all_doc.\
        search_all_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def twitter_identity_retrieve_doc_view(request):
    """
    Show documentation about twitterIdentityRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = twitter_identity_retrieve_doc.twitter_identity_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def twitter_sign_in_start_doc_view(request):
    """
    Show documentation about twitterSignInStart
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = twitter_sign_in_start_doc.twitter_sign_in_start_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def twitter_sign_in_request_access_token_doc_view(request):
    """
    Show documentation about twitterSignInRequestAccessToken
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = \
        twitter_sign_in_request_access_token_doc.twitter_sign_in_request_access_token_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def twitter_sign_in_request_voter_info_doc_view(request):
    """
    Show documentation about twitterSignInRequestVoterInfo
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = \
        twitter_sign_in_request_voter_info_doc.twitter_sign_in_request_voter_info_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def twitter_sign_in_retrieve_doc_view(request):
    """
    Show documentation about twitterSignInRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = twitter_sign_in_retrieve_doc.twitter_sign_in_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_address_retrieve_doc_view(request):
    """
    Show documentation about voterAddressRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_address_retrieve_doc.voter_address_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_address_save_doc_view(request):
    """
    Show documentation about voterAddressSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_address_save_doc.voter_address_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_ballot_items_retrieve_doc_view(request):
    """
    Show documentation about voterBallotItemsRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_ballot_items_retrieve_doc.voter_ballot_items_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_ballot_items_retrieve_from_google_civic_doc_view(request):
    """
    Show documentation about voterBallotItemsRetrieveFromGoogleCivic
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_ballot_items_retrieve_from_google_civic_doc.\
        voter_ballot_items_retrieve_from_google_civic_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_count_doc_view(request):
    """
    Show documentation about voterCount
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_count_doc.voter_count_doc_template_values(url_root)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_create_doc_view(request):
    """
    Show documentation about voterCreate
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_create_doc.voter_create_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_email_address_retrieve_doc_view(request):
    """
    Show documentation about voterEmailAddressRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_email_address_retrieve_doc.voter_email_address_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_email_address_save_doc_view(request):
    """
    Show documentation about voterEmailAddressSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_email_address_save_doc.voter_email_address_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_email_address_sign_in_doc_view(request):
    """
    Show documentation about voterEmailAddressSignIn
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_email_address_sign_in_doc.voter_email_address_sign_in_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_email_address_verify_doc_view(request):
    """
    Show documentation about voterEmailAddressVerify
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_email_address_verify_doc.voter_email_address_verify_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_facebook_sign_in_retrieve_doc_view(request):
    """
    Show documentation about voterFacebookSignInRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_facebook_sign_in_retrieve_doc.voter_facebook_sign_in_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_facebook_sign_in_save_doc_view(request):
    """
    Show documentation about voterFacebookSignInSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_facebook_sign_in_save_doc.voter_facebook_sign_in_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_guide_possibility_retrieve_doc_view(request):
    """
    Show documentation about voterGuidePossibilityRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = \
        voter_guide_possibility_retrieve_doc.voter_guide_possibility_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_guide_possibility_save_doc_view(request):
    """
    Show documentation about voterGuidePossibilitySave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_guide_possibility_save_doc.voter_guide_possibility_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_guides_followed_retrieve_doc_view(request):
    """
    Show documentation about organizationsFollowedRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_guides_followed_retrieve_doc.voter_guides_followed_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_guides_sync_out_doc_view(request):
    """
    Show documentation about voterGuidesSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_guides_sync_out_doc.voter_guides_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_guides_to_follow_retrieve_doc_view(request):
    """
    Show documentation about voterGuidesToFollowRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_guides_to_follow_retrieve_doc.voter_guides_to_follow_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_location_retrieve_from_ip_doc_view(request):
    """
    Show documentation about voterLocationRetrieveFromIP
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_location_retrieve_from_ip_doc.voter_location_retrieve_from_ip_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_merge_two_accounts_doc_view(request):
    """
    Show documentation about voterMergeTwoAccounts
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_merge_two_accounts_doc.voter_merge_two_accounts_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_photo_save_doc_view(request):
    """
    Show documentation about voterPhotoRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_photo_save_doc.voter_photo_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_position_like_off_save_doc_view(request):
    """
    Show documentation about voterPositionLikeOffSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_position_like_off_save_doc.voter_position_like_off_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_position_like_on_save_doc_view(request):
    """
    Show documentation about voterPositionLikeOnSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_position_like_on_save_doc.voter_position_like_on_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_position_like_status_retrieve_doc_view(request):
    """
    Show documentation about voterPositionLikeStatusRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_position_like_status_retrieve_doc.voter_position_like_status_retrieve_doc_template_values(
        url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def polling_locations_sync_out_doc_view(request):
    """
    Show documentation about pollingLocationsSyncOut
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = polling_locations_sync_out_doc.polling_locations_sync_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def position_like_count_doc_view(request):
    """
    Show documentation about positionLikeCount
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = position_like_count_doc.position_like_count_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_all_positions_retrieve_doc_view(request):
    """
    Show documentation about voterAllPositionsRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL

    template_values = voter_all_positions_retrieve_doc.voter_all_positions_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_all_stars_status_retrieve_doc_view(request):
    """
    Show documentation about voterAllStarsStatusRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL

    template_values = voter_all_stars_status_retrieve_doc.voter_all_stars_status_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_position_retrieve_doc_view(request):
    """
    Show documentation about voterPositionRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL

    template_values = voter_position_retrieve_doc.voter_position_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_position_comment_save_doc_view(request):
    """
    Show documentation about voterPositionCommentSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_position_comment_save_doc.voter_position_comment_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_position_visibility_save_doc_view(request):
    """
    Show documentation about voterPositionVisibilitySave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_position_visibility_save_doc.voter_position_visibility_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_opposing_save_doc_view(request):
    """
    Show documentation about voterSupportingSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_opposing_save_doc.voter_opposing_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_stop_opposing_save_doc_view(request):
    """
    Show documentation about voterStopSupportingSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_stop_opposing_save_doc.voter_stop_opposing_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_retrieve_doc_view(request):
    """
    Show documentation about voterRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_retrieve_doc.voter_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_twitter_save_to_current_account_doc_view(request):
    """
    Show documentation about voterStopSupportingSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = \
        voter_twitter_save_to_current_account_doc.voter_twitter_save_to_current_account_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_stop_supporting_save_doc_view(request):
    """
    Show documentation about voterStopSupportingSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_stop_supporting_save_doc.voter_stop_supporting_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_supporting_save_doc_view(request):
    """
    Show documentation about voterSupportingSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_supporting_save_doc.voter_supporting_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_sign_out_doc_view(request):
    """
    Show documentation about voterStarOffSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_sign_out_doc.voter_sign_out_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_star_off_save_doc_view(request):
    """
    Show documentation about voterStarOffSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_star_off_save_doc.voter_star_off_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_star_on_save_doc_view(request):
    """
    Show documentation about voterStarOnSave
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_star_on_save_doc.voter_star_on_save_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_star_status_retrieve_doc_view(request):
    """
    Show documentation about voterStarStatusRetrieve
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_star_status_retrieve_doc.voter_star_status_retrieve_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)


def voter_update_doc_view(request):
    """
    Show documentation about voterUpdate
    """
    url_root = WE_VOTE_SERVER_ROOT_URL
    template_values = voter_update_doc.voter_update_doc_template_values(url_root)
    template_values['voter_api_device_id'] = get_voter_api_device_id(request)
    return render(request, 'apis_v1/api_doc_page.html', template_values)
