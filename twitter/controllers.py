# twitter/controllers.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

# See also WeVoteServer/import_export_twitter/controllers.py for routines that manage incoming twitter data
from .models import TwitterUserManager
from ballot.controllers import figure_out_google_civic_election_id_voter_is_watching
from candidate.models import CandidateCampaignManager, CandidateCampaignListManager
from import_export_twitter.functions import retrieve_twitter_user_info, retrieve_twitter_user_possibilities
from organization.models import OrganizationListManager
from wevote_functions.functions import convert_to_int, positive_value_exists


def retrieve_possible_twitter_handles(candidate_campaign):
    status = ""
    candidate_campaign_manager = CandidateCampaignManager()
    twitter_user_manager = TwitterUserManager()

    if not candidate_campaign:
        status = "RETRIEVE_POSSIBLE_TWITTER_HANDLES-CANDIDATE_MISSING "
        results = {
            'success':                  False,
            'status':                   status,
        }
        return results

    status += "RETRIEVE_POSSIBLE_TWITTER_HANDLES-REACHING_OUT_TO_TWITTER "
    results = retrieve_twitter_user_possibilities(candidate_campaign.candidate_name, candidate_campaign.state_code)

    if results['success']:
        status += "RETRIEVE_POSSIBLE_TWITTER_HANDLES-RETRIEVED_FROM_TWITTER"
        possible_twitter_handles_list = results['possible_twitter_handles_list']

        for possibility_result in possible_twitter_handles_list:
            save_twitter_user_results = twitter_user_manager.update_or_create_twitter_link_possibility(
                candidate_campaign.we_vote_id, possibility_result['twitter_json'],
                possibility_result['search_term'], possibility_result['likelihood_percentage'])

    results = {
        'success':                  True,
        'status':                   status,
        'num_of_possibilities':     str(len(results['possible_twitter_handles_list'])),
    }

    return results


def twitter_identity_retrieve_for_api(twitter_handle, voter_device_id=''):  # twitterIdentityRetrieve
    status = "TWITTER_HANDLE_DOES_NOT_EXIST"  # Default to this
    success = True
    kind_of_owner = "TWITTER_HANDLE_DOES_NOT_EXIST"
    owner_we_vote_id = ''
    owner_id = 0
    google_civic_election_id = 0
    google_civic_election_id_voter_is_watching = 0
    twitter_description = ''
    twitter_followers_count = ''
    twitter_photo_url = ''
    we_vote_hosted_profile_image_url_large = ''
    we_vote_hosted_profile_image_url_medium = ''
    we_vote_hosted_profile_image_url_tiny = ''
    twitter_profile_banner_url_https = ''
    twitter_user_website = ''
    twitter_name = ''

    owner_found = False

    # Check Politician table for Twitter Handle
    # NOTE: It would be better to retrieve from the Politician, and then bring "up" information we need from the
    #  CandidateCampaign table. 2016-05-11 We haven't implemented Politician's yet though.

    # Check Candidate table
    if not positive_value_exists(owner_found):
        # Find out the election the voter is looking at
        results = figure_out_google_civic_election_id_voter_is_watching(voter_device_id)
        if positive_value_exists(results['google_civic_election_id']):
            google_civic_election_id_voter_is_watching = results['google_civic_election_id']
        state_code = ""
        candidate_name = ""

        candidate_list_manager = CandidateCampaignListManager()
        candidate_results = candidate_list_manager.retrieve_candidates_from_non_unique_identifiers(
            google_civic_election_id_voter_is_watching, state_code, twitter_handle, candidate_name)
        if candidate_results['candidate_list_found']:
            candidate_list = candidate_results['candidate_list']

            # ...and then find the candidate entry for that election
            most_recent_candidate = candidate_list[0]
            for one_candidate in candidate_list:
                if google_civic_election_id_voter_is_watching == convert_to_int(one_candidate.google_civic_election_id):
                    kind_of_owner = "CANDIDATE"
                    owner_we_vote_id = one_candidate.we_vote_id
                    owner_id = one_candidate.id
                    google_civic_election_id = one_candidate.google_civic_election_id
                    owner_found = True
                    status = "OWNER_OF_THIS_TWITTER_HANDLE_FOUND-CANDIDATE"
                    # Now that we have candidate, break out of for-loop
                    break
            if not owner_found:
                kind_of_owner = "CANDIDATE"
                owner_we_vote_id = most_recent_candidate.we_vote_id
                owner_id = most_recent_candidate.id
                google_civic_election_id = most_recent_candidate.google_civic_election_id
                owner_found = True
                status = "OWNER_OF_THIS_TWITTER_HANDLE_FOUND-CANDIDATE"

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
            twitter_description = one_organization.twitter_description
            twitter_followers_count = one_organization.twitter_followers_count
            twitter_photo_url = one_organization.twitter_profile_image_url_https
            we_vote_hosted_profile_image_url_large = one_organization.we_vote_hosted_profile_image_url_large
            we_vote_hosted_profile_image_url_medium = one_organization.we_vote_hosted_profile_image_url_medium
            we_vote_hosted_profile_image_url_tiny = one_organization.we_vote_hosted_profile_image_url_tiny
            twitter_profile_banner_url_https = one_organization.twitter_profile_banner_url_https
            twitter_user_website = one_organization.organization_website
            twitter_name = one_organization.twitter_name

    # Reach out to Twitter (or our Twitter account cache) to retrieve some information we can display
    if not positive_value_exists(owner_found):
        twitter_user_manager = TwitterUserManager()
        twitter_user_id = 0
        twitter_results = \
            twitter_user_manager.retrieve_twitter_user_locally_or_remotely(twitter_user_id, twitter_handle)

        if twitter_results['twitter_user_found']:
            twitter_user = twitter_results['twitter_user']
            twitter_description = twitter_user.twitter_description
            twitter_followers_count = twitter_user.twitter_followers_count
            twitter_photo_url = twitter_user.twitter_profile_image_url_https
            we_vote_hosted_profile_image_url_large = twitter_user.we_vote_hosted_profile_image_url_large
            we_vote_hosted_profile_image_url_medium = twitter_user.we_vote_hosted_profile_image_url_medium
            we_vote_hosted_profile_image_url_tiny = twitter_user.we_vote_hosted_profile_image_url_tiny
            twitter_profile_banner_url_https = twitter_user.twitter_profile_banner_url_https
            twitter_user_website = twitter_user.twitter_url
            twitter_name = twitter_user.twitter_name
            kind_of_owner = "TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE"
            status = "TWITTER_HANDLE_NOT_FOUND_IN_WE_VOTE"

    results = {
        'status':                                   status,
        'success':                                  success,
        'twitter_handle':                           twitter_handle,
        'kind_of_owner':                            kind_of_owner,
        'owner_found':                              owner_found,
        'owner_we_vote_id':                         owner_we_vote_id,
        'owner_id':                                 owner_id,
        'google_civic_election_id':                 google_civic_election_id,
        'twitter_description':                      twitter_description,
        'twitter_followers_count':                  twitter_followers_count,
        'twitter_photo_url':                        twitter_photo_url,
        'we_vote_hosted_profile_image_url_large':   we_vote_hosted_profile_image_url_large,
        'we_vote_hosted_profile_image_url_medium':  we_vote_hosted_profile_image_url_medium,
        'we_vote_hosted_profile_image_url_tiny':    we_vote_hosted_profile_image_url_tiny,
        'twitter_profile_banner_url_https':         twitter_profile_banner_url_https,
        'twitter_user_website':                     twitter_user_website,
        'twitter_name':                             twitter_name,
    }
    return results
