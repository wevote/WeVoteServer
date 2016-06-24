# twitter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/import_export_twitter/controllers.py for routines that manage incoming twitter data
from .models import TwitterUserManager
from candidate.models import CandidateCampaignListManager
from import_export_twitter.controllers import retrieve_twitter_user_info
from organization.models import OrganizationListManager
from wevote_functions.functions import positive_value_exists


def twitter_identity_retrieve_for_api(twitter_handle, voter_device_id=''):
    status = "TWITTER_HANDLE_DOES_NOT_EXIST"  # Default to this
    success = True
    kind_of_owner = "TWITTER_HANDLE_DOES_NOT_EXIST"
    owner_we_vote_id = ''
    owner_id = 0
    google_civic_election_id = 0
    twitter_description = ''
    twitter_followers_count = ''
    twitter_photo_url = ''
    twitter_user_website = ''
    twitter_name = ''

    owner_found = False

    # Check Politician table for Twitter Handle
    # NOTE: It would be better to retrieve from the Politician, and then bring "up" information we need from the
    #  CandidateCampaign table. 2016-05-11 We haven't implemented Politician's yet though.

    # Check Candidate table
    if not positive_value_exists(owner_found):
        candidate_list_manager = CandidateCampaignListManager()
        candidate_results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(twitter_handle)
        if candidate_results['candidate_list_found']:
            candidate_list = candidate_results['candidate_list']
            one_candidate = candidate_list[0]
            kind_of_owner = "CANDIDATE"
            owner_we_vote_id = one_candidate.we_vote_id
            owner_id = one_candidate.id
            google_civic_election_id = one_candidate.google_civic_election_id
            owner_found = True
            status = "OWNER_OF_THIS_TWITTER_HANDLE_FOUND-CANDIDATE"

    # Check Organization table
    if not positive_value_exists(owner_found):
        organization_list_manager = OrganizationListManager()
        organization_results = organization_list_manager.retrieve_organizations_from_non_unique_identifiers(
            twitter_handle)
        if organization_results['organization_list_found']:
            organization_list = organization_results['organization_list']
            one_organization = organization_list[0]
            kind_of_owner = "ORGANIZATION"
            owner_we_vote_id = one_organization.we_vote_id
            owner_id = one_organization.id
            google_civic_election_id = 0
            owner_found = True
            status = "OWNER_OF_THIS_TWITTER_HANDLE_FOUND-ORGANIZATION"

    # Reach out to Twitter (or our Twitter account cache) to retrieve some information we can display
    if not positive_value_exists(owner_found):
        twitter_user_manager = TwitterUserManager()
        twitter_results = twitter_user_manager.retrieve_twitter_user_locally_or_remotely(twitter_handle)

        if twitter_results['twitter_user_found']:
            twitter_user = twitter_results['twitter_user']
            twitter_description = twitter_user.twitter_description
            twitter_followers_count = twitter_user.twitter_followers_count
            twitter_photo_url = twitter_user.twitter_profile_image_url_https
            twitter_user_website = twitter_user.twitter_url
            twitter_name = twitter_user.twitter_name
            kind_of_owner = "TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE"
            status = "TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE"

    results = {
        'status':                   status,
        'success':                  success,
        'twitter_handle':           twitter_handle,
        'kind_of_owner':            kind_of_owner,
        'owner_found':              owner_found,
        'owner_we_vote_id':         owner_we_vote_id,
        'owner_id':                 owner_id,
        'google_civic_election_id': google_civic_election_id,
        # These values only returned if kind_of_owner == TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE
        'twitter_description':      twitter_description,
        'twitter_followers_count':  twitter_followers_count,
        'twitter_photo_url':        twitter_photo_url,
        'twitter_user_website':     twitter_user_website,
        'twitter_name':             twitter_name,
    }
    return results
