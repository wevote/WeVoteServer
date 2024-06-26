# voter_guide/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

import operator
from datetime import datetime, timedelta

import pytz
from django.db import models
from django.db.models import Q

import wevote_functions.admin
from election.models import ElectionManager, TIME_SPAN_LIST
from exception.models import handle_exception, handle_record_not_found_exception, \
    handle_record_found_more_than_one_exception
from organization.models import Organization, OrganizationManager, \
    CORPORATION, GROUP, INDIVIDUAL, NEWS_ORGANIZATION, NONPROFIT, NONPROFIT_501C3, NONPROFIT_501C4, \
    POLITICAL_ACTION_COMMITTEE, PUBLIC_FIGURE, TRADE_ASSOCIATION, UNKNOWN, ORGANIZATION_TYPE_CHOICES
from pledge_to_vote.models import PledgeToVoteManager
from voter.models import VoterManager
from wevote_functions.functions import convert_to_int, convert_to_str, positive_value_exists
from wevote_functions.functions_date import generate_localized_datetime_from_obj
from wevote_settings.models import fetch_site_unique_id_prefix, fetch_next_we_vote_id_voter_guide_integer

logger = wevote_functions.admin.get_logger(__name__)

ORGANIZATION = 'O'  # Deprecated
ORGANIZATION_WORD = 'ORGANIZATION'
VOTER = 'V'  # Deprecated

SUPPORT = 'SUPPORT'
NO_STANCE = 'NO_STANCE'
OPPOSE = 'OPPOSE'
POSITION_CHOICES = (
    (SUPPORT,           'Supports'),
    (NO_STANCE,         'No stance'),
    (OPPOSE,            'Opposes'),
)
ORGANIZATION_ENDORSING_CANDIDATES = 'ORG'
ENDORSEMENTS_FOR_CANDIDATE = 'CAND'
UNKNOWN_TYPE = 'UNKNOWN'
VOTER_GUIDE_POSSIBILITY_TYPES = (
    (ORGANIZATION_ENDORSING_CANDIDATES, 'Organization or News Website Endorsing Candidates'),
    (ENDORSEMENTS_FOR_CANDIDATE, 'List of Endorsements for One Candidate'),
    (UNKNOWN_TYPE, 'List of Endorsements for One Candidate'),
)
# Used in different places than WEBSITES_WE_DO_NOT_SCAN_FOR_ENDORSEMENTS - could possibly be combined?
# This constant is passed over to WebApp
WEBSITES_TO_NEVER_HIGHLIGHT_ENDORSEMENTS = [
    '*.atlassian.com',
    '*.atlassian.net',
    '*.google.com',
    '*.newrelic.com',
    '*.slack.com',
    '*.wevote.us',
    '*.zendesk.com',
    'api.wevoteusa.org',
    'app.jazz.co',
    'dashlane.com',
    'github.com'
    'localhost',
    'localhost:3000',
    'localhost:8000',
    'localhost:8001',
    'sketchviewer.com',
    '*.travis-ci.com',
    '*.travis-ci.org',
    'blank',
    'platform.twitter.com',
    's7.addthis.com',
    'vars.hotjar.com',
    'regex101.com',
]
# Used to prevent entering url to scan from being processed. Only used in WeVoteServer.
# DALE 2024/04/08 There are several websites we were blocking from being scanned for technical reasons.
#   I am reversing this blockage, so we can create a Voter Guide Possibility entry for use with the Chrome extension.
WEBSITES_WE_DO_NOT_SCAN_FOR_ENDORSEMENTS = [
    # 'adirondackdailyenterprise.com',
    'about:blank',
    # 'alternet.org', 'apple.com',
    'app.jazz.co'
    'atlassian.com', 'atlassian.net',
    # 'baltimoresun.com',
    # 'billboard.com', 'bloomberg.com', 'boston.com', 'bostonglobe.com',
    # 'broadwayworld.com', 'buffalonews.com', 'businessinsider.com', 'buzzfeed.com',
    # 'charlotteobserver.com', 'chicagotibune.com', 'cnbc.com', 'cnn.com',
    # 'dailydot.com', 'dailykos.com', 'dallasnews.com', 'democracynow.org', 'denverpost.com',
    'dco-assets.everestads.net',
    # 'desmoinesregister.com', 'dispatch.com',
    'docs.google.com', 'drive.google.com', 'mail.google.com', 'www.google.com',
    # 'essence.com',
    # 'facebook.com', 'foxbusiness.com', 'foxnews.com',
    # 'gayly.com',
    'github.com',
    # 'hollywoodreporter.com', 'houstonchronicle.com', 'huffpost.com',
    # 'indystar.com',
    # 'instagram.com',
    'jobs.com',
    # 'kansascity.com', 'kentucky.com', 'ksat.com',
    # 'latimes.com',
    'localhost:8000',
    # 'mercurynews.com', 'miaminewtimes.com', 'motherjones.com', 'msnbc.com',
    # 'nationalreview.com', 'nbcnews.com', 'newsweek.com', 'npr.org', 'nydailynews.com', 'nypost.com', 'nytimes.com',
    # 'ocregister.org', 'opensecrets.org', 'orlandosentinel.com',
    # 'palmbeachpost.com', 'people.com', 'politico.com',
    # 'reviewjournal.com', 'rollingstone.com',
    # 'sacbee.com', 'sfchronicle.com', 'snewsnet.com', 'spectator.us', 'sun-sentinel.com', 'suntimes.com',
    'http://t.co', 'https://t.co',
    # 'tampabay.com', 'techcrunch.com', 'texastribune.com', 'thehill.com',
    # 'thenation.com', 'thestate.com', 'twitter.com',
    # 'usatoday.com',
    # 'vox.com',
    'w3schools.com',
    # 'washingtonpost.com',
    # 'wapo.st', 'westword.com', 'wsj.com',
    # 'youtu.be', 'youtube.com',
]
POSSIBILITY_LIST_LIMIT = 1000  # Limit to 1000 to avoid very slow page loading, formerly 200, then 400
# We want a list of 1000 numbers converted to strings, so we use the last 4 digits
max_number_of_digits = len(str(POSSIBILITY_LIST_LIMIT))
leading_zeros = ""
for i in range(max_number_of_digits):
    leading_zeros += "0"
number_list_temp = []
for i in range(POSSIBILITY_LIST_LIMIT):
    digit = i + 1
    string_temp = leading_zeros + str(digit)
    number_list_temp.append(string_temp[-max_number_of_digits:])
POSSIBLE_ENDORSEMENT_NUMBER_LIST = number_list_temp

# Since there are some scenarios where we remove candidates where positions are already stored, we need to review more
#  positions than we are prepared to store
# POSSIBLE_ENDORSEMENT_NUMBER_LIST_FULL = []


class VoterGuideManager(models.Manager):
    """
    A class for working with the VoterGuide model
    """
    @staticmethod
    def update_or_create_organization_voter_guide_by_election_id(
            voter_guide_we_vote_id='',
            organization_we_vote_id='',
            google_civic_election_id=0,
            state_code='',
            pledge_goal=0,
            we_vote_hosted_profile_image_url_large='',
            we_vote_hosted_profile_image_url_medium='',
            we_vote_hosted_profile_image_url_tiny='',
            vote_smart_ratings_only=False,
            elections_dict={},
            organizations_dict={},
            voter_we_vote_id_dict={}):
        """
        This creates voter_guides, and also refreshes voter guides with updated organization data
        """
        google_civic_election_id = convert_to_int(google_civic_election_id)
        exception_multiple_object_returned = False
        voter_guide_on_stage = None
        organization = Organization()
        organization_found = False
        new_voter_guide_created = False
        voter_we_vote_id = None
        status = ''
        success = True
        if not google_civic_election_id or not organization_we_vote_id:
            status += 'ERROR_VARIABLES_MISSING_FOR_ORGANIZATION_VOTER_GUIDE '
            success = False
            new_voter_guide_created = False
        else:
            # Retrieve the organization object so we can bring over values
            # NOTE: If we don't have this organization in the local database, we won't create a voter guide
            organization_manager = OrganizationManager()
            voter_manager = VoterManager()

            if organization_we_vote_id in organizations_dict:
                organization = organizations_dict[organization_we_vote_id]
                organization_found = True
            else:
                results = organization_manager.retrieve_organization(0, organization_we_vote_id)
                if results['organization_found']:
                    organization = results['organization']
                    organizations_dict[organization_we_vote_id] = organization
                    organization_found = True

            if organization_found:
                if organization_we_vote_id in voter_we_vote_id_dict:
                    voter_we_vote_id = voter_we_vote_id_dict[organization_we_vote_id]
                else:
                    voter_results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization_we_vote_id)
                    if voter_results['voter_found']:
                        try:
                            voter_we_vote_id = voter_results['voter'].we_vote_id
                            voter_we_vote_id_dict[organization_we_vote_id] = voter_we_vote_id
                        except Exception as e:
                            status += 'COULD_NOT_RETRIEVE_VOTER_WE_VOTE_ID ' + str(e) + ' '

            # Retrieve the election so we can bring over the state_code if needed
            if positive_value_exists(state_code):
                election_state_code = state_code
            else:
                election_state_code = ''
                if google_civic_election_id in elections_dict:
                    election = elections_dict[google_civic_election_id]
                    if election:
                        election_state_code = election.state_code
                    else:
                        try:
                            del elections_dict[google_civic_election_id]
                        except Exception as e:
                            pass
                else:
                    election_manager = ElectionManager()
                    election_results = election_manager.retrieve_election(google_civic_election_id)
                    if election_results['election_found']:
                        election = election_results['election']
                        election_state_code = election.state_code
                        if not positive_value_exists(election_state_code):
                            election_state_code = ''
                        elections_dict[google_civic_election_id] = election

            # Now update voter_guide
            if organization_found:
                pledge_to_vote_manager = PledgeToVoteManager()
                pledge_results = pledge_to_vote_manager.retrieve_pledge_count_from_organization_we_vote_id(
                        organization_we_vote_id)
                if pledge_results['pledge_count_found']:
                    pledge_count = pledge_results['pledge_count']
                else:
                    pledge_count = 0

                if positive_value_exists(election_state_code):
                    election_state_code = election_state_code.lower()
                updated_values = {
                    'google_civic_election_id': google_civic_election_id,
                    'organization_we_vote_id':  organization_we_vote_id,
                    'image_url':                organization.organization_photo_url(),
                    'twitter_handle':           organization.organization_twitter_handle,
                    'twitter_description':      organization.twitter_description,
                    'twitter_followers_count':  organization.twitter_followers_count,
                    'display_name':             organization.organization_name,
                    'voter_guide_owner_type':   organization.organization_type,
                    'vote_smart_ratings_only':  vote_smart_ratings_only,
                    'state_code':               election_state_code,
                    'we_vote_hosted_profile_image_url_large':  organization.we_vote_hosted_profile_image_url_large,
                    'we_vote_hosted_profile_image_url_medium': organization.we_vote_hosted_profile_image_url_medium,
                    'we_vote_hosted_profile_image_url_tiny':   organization.we_vote_hosted_profile_image_url_tiny,
                    'pledge_count':             pledge_count,
                }
                if positive_value_exists(voter_guide_we_vote_id):
                    updated_values['we_vote_id'] = voter_guide_we_vote_id
                if positive_value_exists(voter_we_vote_id):
                    updated_values['voter_we_vote_id'] = voter_we_vote_id
                if positive_value_exists(pledge_goal):
                    updated_values['pledge_goal'] = pledge_goal
                if positive_value_exists(we_vote_hosted_profile_image_url_large):
                    updated_values['we_vote_hosted_profile_image_url_large'] = \
                        we_vote_hosted_profile_image_url_large
                if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                    updated_values['we_vote_hosted_profile_image_url_medium'] = \
                        we_vote_hosted_profile_image_url_medium
                if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                    updated_values['we_vote_hosted_profile_image_url_tiny'] = we_vote_hosted_profile_image_url_tiny
                if positive_value_exists(google_civic_election_id):
                    if google_civic_election_id in elections_dict:
                        election = elections_dict[google_civic_election_id]
                        if election:
                            updated_values['election_day_text'] = election.election_day_text
                        else:
                            try:
                                del elections_dict[google_civic_election_id]
                            except Exception as e:
                                pass
                    else:
                        election_manager = ElectionManager()
                        election_results = election_manager.retrieve_election(google_civic_election_id)
                        if election_results['election_found']:
                            election = election_results['election']
                            updated_values['election_day_text'] = election.election_day_text
                            elections_dict[google_civic_election_id] = election
                try:
                    voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                        google_civic_election_id__exact=google_civic_election_id,
                        organization_we_vote_id__iexact=organization_we_vote_id,
                        defaults=updated_values)
                except VoterGuide.MultipleObjectsReturned as e:
                    handle_record_found_more_than_one_exception(e, logger=logger)
                    status += 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_ORGANIZATION '
                    exception_multiple_object_returned = True
                    new_voter_guide_created = False
                except Exception as e:
                    handle_exception(e, logger=logger)
                    success = False
                    status += 'UPDATE_OR_CREATE_ORGANIZATION_VOTER_GUIDE_BY_ELECTION_ID: ' + str(e) + ' '
                    new_voter_guide_created = False
                if new_voter_guide_created:
                    if not positive_value_exists(voter_guide_on_stage.id):
                        # Advance the we_vote_id_last_voter_guide_integer
                        next_integer = fetch_next_we_vote_id_voter_guide_integer()
                        status += 'UPDATE_OR_CREATE_ORGANIZATION_VOTER_GUIDE_BY_ELECTION_ID, NEXT_INTEGER: ' \
                                  '' + str(next_integer) + ' '
                        try:
                            voter_guide_on_stage.we_vote_id = None
                            voter_guide_on_stage.save()
                        except Exception as e:
                            handle_exception(e, logger=logger)
                            status += 'UPDATE_OR_CREATE_ORGANIZATION_VOTER_GUIDE_AFTER_NEXT_INTEGER: ' + str(e) + ' '
                            new_voter_guide_created = False
                    if positive_value_exists(voter_guide_on_stage.id):
                        status += 'VOTER_GUIDE_CREATED_FOR_ORGANIZATION '
                        success = True
                    else:
                        status += 'COULD_NOT_CREATE_VOTER_GUIDE '
                        success = False
                else:
                    status += 'VOTER_GUIDE_UPDATED_FOR_ORGANIZATION '
                    success = True
            else:
                success = False
                status += 'VOTER_GUIDE_NOT_CREATED_BECAUSE_ORGANIZATION_NOT_FOUND_LOCALLY '

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'voter_guide':              voter_guide_on_stage,
            'new_voter_guide_created':  new_voter_guide_created,
            'elections_dict':           elections_dict,
            'organizations_dict':       organizations_dict,
            'voter_we_vote_id_dict':    voter_we_vote_id_dict,
        }
        return results

    @staticmethod
    def update_or_create_organization_voter_guide_by_time_span(
            voter_guide_we_vote_id,
            organization_we_vote_id,
            vote_smart_time_span,
            pledge_goal='',
            we_vote_hosted_profile_image_url_large='',
            we_vote_hosted_profile_image_url_medium='',
            we_vote_hosted_profile_image_url_tiny=''):
        organization_found = False
        voter_guide_owner_type = ORGANIZATION
        exception_multiple_object_returned = False
        new_voter_guide_created = False
        status = ''
        if not vote_smart_time_span or not organization_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_ORGANIZATION_VOTER_GUIDE_BY_TIME_SPAN'
            success = False
            new_voter_guide_created = False
        else:
            # Retrieve the organization object so we can bring over values
            organization_manager = OrganizationManager()
            results = organization_manager.retrieve_organization(0, organization_we_vote_id)
            if results['organization_found']:
                organization_found = True
                organization = results['organization']

            # Now update voter_guide  # TODO DALE Get from TwitterLinkToOrganization, not organization_twitter_handle
            try:
                if organization_found:
                    if organization.twitter_followers_count is None:
                        twitter_followers_count = 0
                    else:
                        twitter_followers_count = convert_to_int(organization.twitter_followers_count)
                    pledge_to_vote_manager = PledgeToVoteManager()
                    pledge_results = pledge_to_vote_manager.retrieve_pledge_count_from_organization_we_vote_id(
                            organization_we_vote_id)
                    if pledge_results['pledge_count_found']:
                        pledge_count = pledge_results['pledge_count']
                    else:
                        pledge_count = 0
                    updated_values = {
                        # Values we search against below
                        'vote_smart_time_span':     vote_smart_time_span,
                        'organization_we_vote_id':  organization_we_vote_id,
                        # The rest of the values
                        'voter_guide_owner_type':   voter_guide_owner_type,
                        'twitter_handle':           organization.organization_twitter_handle,
                        'display_name':             organization.organization_name,
                        'image_url':                organization.organization_photo_url(),
                        'twitter_description':      organization.twitter_description,
                        'twitter_followers_count':  twitter_followers_count,
                        'pledge_count':             pledge_count,
                    }
                    if positive_value_exists(voter_guide_we_vote_id):
                        updated_values['we_vote_id'] = voter_guide_we_vote_id
                    if positive_value_exists(pledge_goal):
                        updated_values['pledge_goal'] = pledge_goal
                    if positive_value_exists(we_vote_hosted_profile_image_url_large):
                        updated_values['we_vote_hosted_profile_image_url_large'] = \
                            we_vote_hosted_profile_image_url_large
                    if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                        updated_values['we_vote_hosted_profile_image_url_medium'] = \
                            we_vote_hosted_profile_image_url_medium
                    if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                        updated_values['we_vote_hosted_profile_image_url_tiny'] = we_vote_hosted_profile_image_url_tiny
                    voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                        vote_smart_time_span__exact=vote_smart_time_span,
                        organization_we_vote_id__iexact=organization_we_vote_id,
                        defaults=updated_values)
                    success = True
                    if new_voter_guide_created:
                        status += 'VOTER_GUIDE_CREATED_FOR_ORGANIZATION_BY_TIME_SPAN '
                    else:
                        status += 'VOTER_GUIDE_UPDATED_FOR_ORGANIZATION_BY_TIME_SPAN '
                else:
                    success = False
                    status += 'VOTER_GUIDE_NOT_CREATED_BECAUSE_ORGANIZATION_NOT_FOUND_LOCALLY '
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status += 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_ORGANIZATION_BY_TIME_SPAN '
                exception_multiple_object_returned = True
                new_voter_guide_created = False
            except Exception as e:
                handle_exception(e, logger=logger)
                success = False
                status += 'UPDATE_OR_CREATE_ORGANIZATION_VOTER_GUIDE_BY_ELECTION_ID: ' + str(e) + ' '
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    @staticmethod
    def update_or_create_voter_guides_generated(google_civic_election_id=0, number_of_voter_guides=0):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        status = ""

        try:
            updated_values = {
                # Values we search against below
                'google_civic_election_id': google_civic_election_id,
                'number_of_voter_guides':   number_of_voter_guides,
            }
            voter_guide, new_voter_guide_created = VoterGuidesGenerated.objects.update_or_create(
                google_civic_election_id=google_civic_election_id,
                defaults=updated_values)
            success = True
            if new_voter_guide_created:
                status += 'VOTER_GUIDES_GENERATED_CREATED '
            else:
                status += 'VOTER_GUIDES_GENERATED_UPDATED '
        except VoterGuidesGenerated.MultipleObjectsReturned as e:
            success = False
            status += 'MULTIPLE_MATCHING_VOTER_GUIDES_GENERATED '
        except Exception as e:
            handle_exception(e, logger=logger)
            success = False
            status += 'UPDATE_OR_CREATE_VOTER_GUIDES_GENERATED: ' + str(e) + ' '

        results = {
            'success':  success,
            'status':   status,
        }
        return results

    @staticmethod
    def update_or_create_voter_voter_guide(google_civic_election_id, voter):
        """

        :param google_civic_election_id:
        :param voter:
        :param organization:
        :return:
        """
        google_civic_election_id = convert_to_int(google_civic_election_id)
        success = False
        status = ""
        exception_multiple_object_returned = False
        new_voter_guide_created = False
        linked_organization_we_vote_id = ""
        organization_manager = OrganizationManager()
        voter_guide = VoterGuide()

        try:
            voter
        except NameError:
            voter_exists = False
        else:
            voter_exists = True

        if voter_exists and positive_value_exists(voter.linked_organization_we_vote_id):
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(voter.linked_organization_we_vote_id)
            if organization_results['organization_found']:
                organization = organization_results['organization']
                linked_organization_we_vote_id = organization.we_vote_id

        try:
            organization
        except NameError:
            organization_exists = False
        else:
            organization_exists = True

        if positive_value_exists(linked_organization_we_vote_id) and voter_exists and organization_exists \
                and positive_value_exists(google_civic_election_id):
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'organization_we_vote_id': linked_organization_we_vote_id,
                    # The rest of the values
                    'voter_guide_owner_type': organization.organization_type,
                    'owner_voter_id': voter.id,
                    'owner_we_vote_id': voter.we_vote_id,
                    'voter_we_vote_id': voter.we_vote_id,
                }
                voter_guide, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    organization_we_vote_id__iexact=linked_organization_we_vote_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status += 'VOTER_GUIDE_CREATED_FOR_VOTER '
                else:
                    status += 'VOTER_GUIDE_UPDATED_FOR_VOTER '
            except VoterGuide.MultipleObjectsReturned as e:
                success = False
                status += 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_VOTER '
                exception_multiple_object_returned = True
                new_voter_guide_created = False
            except Exception as e:
                handle_exception(e, logger=logger)
                success = False
                status += 'UPDATE_OR_CREATE_VOTER_VOTER_GUIDE: ' + str(e) + ' '
                new_voter_guide_created = False

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide':              voter_guide,
            'voter_guide_saved':        success,
            'voter_guide_created':      new_voter_guide_created,
        }
        return results

    @staticmethod
    def voter_guide_exists(organization_we_vote_id, google_civic_election_id):
        voter_guide_found = False
        google_civic_election_id = int(google_civic_election_id)

        if not positive_value_exists(organization_we_vote_id) or not positive_value_exists(google_civic_election_id):
            return False

        try:
            if positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                voter_guide_query = VoterGuide.objects.filter(google_civic_election_id=google_civic_election_id,
                                                              organization_we_vote_id__iexact=organization_we_vote_id)
                voter_guide_found = True if voter_guide_query.count() > 0 else False
        except VoterGuide.MultipleObjectsReturned as e:
            handle_exception(e, logger=logger)
            voter_guide_found = True
        except VoterGuide.DoesNotExist as e:
            handle_exception(e, logger=logger)
            voter_guide_found = False
        except Exception as e:
            handle_exception(e, logger=logger)
        return voter_guide_found

    @staticmethod
    def retrieve_voter_guide(
            voter_guide_id=0,
            voter_guide_we_vote_id="",
            google_civic_election_id=0,
            vote_smart_time_span=None,
            organization_we_vote_id=None,
            public_figure_we_vote_id=None,
            owner_we_vote_id=None,
            read_only=False):
        voter_guide_id = convert_to_int(voter_guide_id)
        google_civic_election_id = convert_to_int(google_civic_election_id)
        organization_we_vote_id = convert_to_str(organization_we_vote_id)
        public_figure_we_vote_id = convert_to_str(public_figure_we_vote_id)
        owner_we_vote_id = convert_to_str(owner_we_vote_id)

        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        status = ""
        success = True
        voter_guide_on_stage = VoterGuide()
        voter_guide_on_stage_id = 0
        voter_guide_on_stage_we_vote_id = ''
        try:
            if positive_value_exists(voter_guide_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ID "  # Set this in case the get fails
                if read_only:
                    voter_guide_on_stage = VoterGuide.objects.using('readonly').get(id=voter_guide_id)
                else:
                    voter_guide_on_stage = VoterGuide.objects.get(id=voter_guide_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                voter_guide_on_stage_we_vote_id = voter_guide_on_stage.we_vote_id
                status = "VOTER_GUIDE_FOUND_WITH_ID "
            elif positive_value_exists(voter_guide_we_vote_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_WE_VOTE_ID "  # Set this in case the get fails
                if read_only:
                    voter_guide_on_stage = VoterGuide.objects.using('readonly').get(we_vote_id=voter_guide_we_vote_id)
                else:
                    voter_guide_on_stage = VoterGuide.objects.get(we_vote_id=voter_guide_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                voter_guide_on_stage_we_vote_id = voter_guide_on_stage.we_vote_id
                status = "VOTER_GUIDE_FOUND_WITH_WE_VOTE_ID "
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ORGANIZATION_WE_VOTE_ID "  # Set this in case the get fails
                if read_only:
                    voter_guide_on_stage = VoterGuide.objects.using('readonly').get(
                        google_civic_election_id=google_civic_election_id,
                        organization_we_vote_id__iexact=organization_we_vote_id)
                else:
                    voter_guide_on_stage = VoterGuide.objects.get(
                        google_civic_election_id=google_civic_election_id,
                        organization_we_vote_id__iexact=organization_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                voter_guide_on_stage_we_vote_id = voter_guide_on_stage.we_vote_id
                status = "VOTER_GUIDE_FOUND_WITH_ORGANIZATION_WE_VOTE_ID "
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(vote_smart_time_span):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ORGANIZATION_WE_VOTE_ID_AND_TIME_SPAN "
                if read_only:
                    voter_guide_on_stage = VoterGuide.objects.using('readonly').get(
                        vote_smart_time_span=vote_smart_time_span,
                        organization_we_vote_id__iexact=organization_we_vote_id)
                else:
                    voter_guide_on_stage = VoterGuide.objects.get(
                        vote_smart_time_span=vote_smart_time_span,
                        organization_we_vote_id__iexact=organization_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                voter_guide_on_stage_we_vote_id = voter_guide_on_stage.we_vote_id
                status = "VOTER_GUIDE_FOUND_WITH_ORGANIZATION_WE_VOTE_ID_AND_TIME_SPAN "
            elif positive_value_exists(public_figure_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_PUBLIC_FIGURE_WE_VOTE_ID "  # Set this in case the get fails
                if read_only:
                    voter_guide_on_stage = VoterGuide.objects.using('readonly').get(
                        google_civic_election_id=google_civic_election_id,
                        public_figure_we_vote_id__iexact=public_figure_we_vote_id)
                else:
                    voter_guide_on_stage = VoterGuide.objects.get(
                        google_civic_election_id=google_civic_election_id,
                        public_figure_we_vote_id__iexact=public_figure_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                voter_guide_on_stage_we_vote_id = voter_guide_on_stage.we_vote_id
                status = "VOTER_GUIDE_FOUND_WITH_PUBLIC_FIGURE_WE_VOTE_ID "
            elif positive_value_exists(owner_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_VOTER_WE_VOTE_ID "  # Set this in case the get fails
                if read_only:
                    voter_guide_on_stage = VoterGuide.objects.using('readonly').get(
                        google_civic_election_id=google_civic_election_id,
                        owner_we_vote_id__iexact=owner_we_vote_id)
                else:
                    voter_guide_on_stage = VoterGuide.objects.get(
                        google_civic_election_id=google_civic_election_id,
                        owner_we_vote_id__iexact=owner_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                voter_guide_on_stage_we_vote_id = voter_guide_on_stage.we_vote_id
                status = "VOTER_GUIDE_FOUND_WITH_VOTER_WE_VOTE_ID "
            else:
                status = "Insufficient variables included to retrieve one voter guide."
        except VoterGuide.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status += ", ERROR_MORE_THAN_ONE_VOTER_GUIDE_FOUND "
            success = False
        except VoterGuide.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status += ", VOTER_GUIDE_DOES_NOT_EXIST "
            success = False

        voter_guide_on_stage_found = True if positive_value_exists(voter_guide_on_stage_we_vote_id) else False
        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_found':            voter_guide_on_stage_found,
            'voter_guide_id':               voter_guide_on_stage_id,
            'voter_guide_we_vote_id':       voter_guide_on_stage_we_vote_id,
            'organization_we_vote_id':      voter_guide_on_stage.organization_we_vote_id,
            'public_figure_we_vote_id':     voter_guide_on_stage.public_figure_we_vote_id,
            'owner_we_vote_id':             voter_guide_on_stage.owner_we_vote_id,
            'voter_guide':                  voter_guide_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    @staticmethod
    def retrieve_most_recent_voter_guide_for_org(organization_we_vote_id, read_only=False):
        status = 'ENTERING_RETRIEVE_MOST_RECENT_VOTER_GUIDE_FOR_ORG'
        voter_guide_found = False
        voter_guide = VoterGuide()
        voter_guide_manager = VoterGuideManager()
        for time_span in TIME_SPAN_LIST:
            voter_guide_by_time_span_results = voter_guide_manager.retrieve_voter_guide(
                vote_smart_time_span=time_span,
                organization_we_vote_id=organization_we_vote_id,
                read_only=read_only)
            if voter_guide_by_time_span_results['voter_guide_found']:
                voter_guide_found = True
                voter_guide = voter_guide_by_time_span_results['voter_guide']
                status = 'MOST_RECENT_VOTER_GUIDE_FOUND_FOR_ORG_BY_TIME_SPAN'
                results = {
                    'success':              voter_guide_found,
                    'status':               status,
                    'voter_guide_found':    voter_guide_found,
                    'voter_guide':          voter_guide,
                }
                return results

        election_manager = ElectionManager()
        results = election_manager.retrieve_elections_by_date()
        if results['success']:
            election_list = results['election_list']
            for one_election in election_list:
                voter_guide_results = voter_guide_manager.retrieve_voter_guide(
                    google_civic_election_id=one_election.google_civic_election_id,
                    organization_we_vote_id=organization_we_vote_id,
                    read_only=read_only)
                if voter_guide_results['voter_guide_found']:
                    voter_guide_found = True
                    voter_guide = voter_guide_results['voter_guide']
                    status = 'MOST_RECENT_VOTER_GUIDE_FOUND_FOR_ORG_BY_ELECTION_ID'
                    results = {
                        'success':              voter_guide_found,
                        'status':               status,
                        'voter_guide_found':    voter_guide_found,
                        'voter_guide':          voter_guide,
                    }
                    return results

        results = {
            'success':              False,
            'status':               status,
            'voter_guide_found':    voter_guide_found,
            'voter_guide':          voter_guide,
        }
        return results

    @staticmethod
    def reset_voter_guide_image_details(
            organization,
            twitter_profile_image_url_https=None,
            facebook_profile_image_url_https=None):
        """
        Reset Voter guide entry with original we vote image details
        :param organization:
        :param twitter_profile_image_url_https:
        :param facebook_profile_image_url_https:
        :return:
        """
        image_url = None
        success = False
        status = ""
        voter_guide = VoterGuide()

        if positive_value_exists(twitter_profile_image_url_https):
            image_url = twitter_profile_image_url_https
        elif positive_value_exists(facebook_profile_image_url_https):
            image_url = facebook_profile_image_url_https
        if organization:
            voter_guide_list_manager = VoterGuideListManager()
            results = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(
                organization.we_vote_id, read_only=False)
            voter_guide_list = results['voter_guide_list']
            if positive_value_exists(results['voter_guide_list_found']):
                for voter_guide in voter_guide_list:
                    voter_guide.image_url = image_url
                    voter_guide.we_vote_hosted_profile_image_url_large = ''
                    voter_guide.we_vote_hosted_profile_image_url_medium = ''
                    voter_guide.we_vote_hosted_profile_image_url_tiny = ''

                    voter_guide.save()
                    success = True
                    status += " RESET_ORG_IMAGE_DETAILS-EARLIER VERSION"
            else:
                success = True
                status += "NO_VOTER_GUIDES_FOUND_FOR_RESET_IMAGE_DETAILS"

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
            'voter_guide':              voter_guide,
        }
        return results

    def update_organization_voter_guides_with_organization_data(self, organization):
        """
        Update voter_guide entry with the latest information from an organization
        """
        success = True
        status = ""
        voter_guides_updated = 0

        if organization:
            voter_guide_list_manager = VoterGuideListManager()
            voter_manager = VoterManager()
            results = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(
                organization.we_vote_id, read_only=False)
            if positive_value_exists(results['voter_guide_list_found']):
                voter_guide_list = results['voter_guide_list']
                for voter_guide in voter_guide_list:
                    # Note that "refresh_one_voter_guide_from_organization" doesn't save changes
                    refresh_results = self.refresh_one_voter_guide_from_organization(voter_guide, organization)
                    if positive_value_exists(refresh_results['values_changed']) \
                            or not positive_value_exists(voter_guide.voter_we_vote_id):
                        voter_guide = refresh_results['voter_guide']
                        if not positive_value_exists(voter_guide.voter_we_vote_id):
                            voter_results = voter_manager.retrieve_voter_by_organization_we_vote_id(
                                organization.we_vote_id)
                            if voter_results['voter_found']:
                                try:
                                    voter_we_vote_id = voter_results['voter'].we_vote_id
                                    voter_guide.voter_we_vote_id = voter_we_vote_id
                                except Exception as e:
                                    status += 'COULD_NOT_RETRIEVE_VOTER_WE_VOTE_ID ' + str(e) + ' '
                                    success = False
                            elif not voter_results['success']:
                                status += "RETRIEVE_VOTER_FAILED: " + voter_results['status'] + " "
                        try:
                            voter_guide.save()
                            voter_guides_updated += 1
                        except Exception as e:
                            status += "SAVE_VOTER_GUIDE_FAILED: " + str(e) + " "
                            success = False
                    elif not refresh_results['success']:
                        status += "REFRESH_VOTER_GUIDE_FAILED: " + refresh_results['status'] + " "
                status += "UPDATED_VOTER_GUIDES_WITH_ORG_DATA: " + str(voter_guides_updated) + " "
            elif not results['success']:
                status += "RETRIEVE_VOTER_GUIDES_FAILED: " + results['status'] + " "
        else:
            status += "UPDATED_VOTER_GUIDES_ORGANIZATION_MISSING "
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
        }
        return results

    def update_voter_guide_social_media_statistics(self, organization):
        """
        Update voter_guide entry with details retrieved from Twitter, Facebook, or ???
        DALE 2017-11-06 This function needs to be refactored
        """
        success = False
        status = ""
        voter_guide = VoterGuide()

        if organization:
            if positive_value_exists(organization.twitter_followers_count):
                results = self.retrieve_most_recent_voter_guide_for_org(organization_we_vote_id=organization.we_vote_id)

                if results['voter_guide_found']:
                    voter_guide = results['voter_guide']
                    if positive_value_exists(voter_guide.id):
                        refresh_results = self.refresh_one_voter_guide_from_organization(voter_guide, organization)
                        if positive_value_exists(refresh_results['values_changed']):
                            voter_guide = refresh_results['voter_guide']
                            voter_guide.save()
                            success = True
                            status += " SAVED_ORG_TWITTER_DETAILS"
                        else:
                            success = True
                            status = " NO_CHANGES_SAVED_TO_ORG_TWITTER_DETAILS"

                voter_guide_list_manager = VoterGuideListManager()
                results = voter_guide_list_manager.retrieve_all_voter_guides_by_organization_we_vote_id(
                    organization.we_vote_id, read_only=False)
                if positive_value_exists(results['voter_guide_list_found']):
                    voter_guide_list = results['voter_guide_list']
                    for voter_guide in voter_guide_list:
                        if not positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_large) or \
                                not positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_medium) or \
                                not positive_value_exists(voter_guide.we_vote_hosted_profile_image_url_tiny):
                            refresh_results = self.refresh_one_voter_guide_from_organization(voter_guide, organization)
                            if positive_value_exists(refresh_results['values_changed']):
                                voter_guide = refresh_results['voter_guide']
                                voter_guide.save()
                                success = True
                                status += " SAVED_ORG_TWITTER_DETAILS-EARLIER VERSION"

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
            'voter_guide':              voter_guide,
        }
        return results

    @staticmethod
    def refresh_one_voter_guide_from_organization(voter_guide, organization):
        """
        This function does not save voter_guide
        :param voter_guide:
        :param organization:
        :return:
        """
        success = True
        status = ""
        values_changed = False
        if voter_guide.display_name != organization.organization_name:
            voter_guide.display_name = organization.organization_name
            values_changed = True
        if voter_guide.voter_guide_owner_type != organization.organization_type:
            voter_guide.voter_guide_owner_type = organization.organization_type
            values_changed = True
        if voter_guide.twitter_followers_count != organization.twitter_followers_count:
            voter_guide.twitter_followers_count = organization.twitter_followers_count
            values_changed = True
        if voter_guide.twitter_description != organization.twitter_description:
            voter_guide.twitter_description = organization.twitter_description
            values_changed = True
        if voter_guide.twitter_handle != organization.organization_twitter_handle:
            voter_guide.twitter_handle = organization.organization_twitter_handle
            values_changed = True
        if voter_guide.image_url != organization.organization_photo_url():
            voter_guide.image_url = organization.organization_photo_url()
            values_changed = True
        if voter_guide.we_vote_hosted_profile_image_url_large != \
                organization.we_vote_hosted_profile_image_url_large:
            voter_guide.we_vote_hosted_profile_image_url_large = \
                organization.we_vote_hosted_profile_image_url_large
            values_changed = True
        if voter_guide.we_vote_hosted_profile_image_url_medium != \
                organization.we_vote_hosted_profile_image_url_medium:
            voter_guide.we_vote_hosted_profile_image_url_medium = \
                organization.we_vote_hosted_profile_image_url_medium
            values_changed = True
        if voter_guide.we_vote_hosted_profile_image_url_tiny != \
                organization.we_vote_hosted_profile_image_url_tiny:
            voter_guide.we_vote_hosted_profile_image_url_tiny = \
                organization.we_vote_hosted_profile_image_url_tiny
            values_changed = True
        if positive_value_exists(voter_guide.google_civic_election_id) \
                and not positive_value_exists(voter_guide.election_day_text):
            election_manager = ElectionManager()
            election_results = election_manager.retrieve_election(voter_guide.google_civic_election_id)
            if election_results['election_found']:
                election = election_results['election']
                voter_guide.election_day_text = election.election_day_text
                values_changed = True

        results = {
            'values_changed':   values_changed,
            'voter_guide':      voter_guide,
            'status':           status,
            'success':          success,
        }
        return results

    def delete_voter_guide(self, voter_guide_id):
        voter_guide_id = convert_to_int(voter_guide_id)
        voter_guide_deleted = False

        try:
            if voter_guide_id:
                results = self.retrieve_voter_guide(voter_guide_id)
                if results['voter_guide_found']:
                    voter_guide = results['voter_guide']
                    voter_guide_id = voter_guide.id
                    voter_guide.delete()
                    voter_guide_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)

        results = {
            'success':              voter_guide_deleted,
            'voter_guide_deleted': voter_guide_deleted,
            'voter_guide_id':      voter_guide_id,
        }
        return results

    @staticmethod
    def merge_duplicate_voter_guides_for_organization_and_election(organization_we_vote_id, google_civic_election_id):
        success = True
        status = ''
        number_of_voter_guides_found = 0
        number_of_voter_guides_deleted = 0
        voter_guide_found = False
        voter_guide = None
        voter_guide_list = []
        # Make sure there are both variables
        if not organization_we_vote_id or not google_civic_election_id:
            success = False
            status += 'MERGE_DUPLICATE_VOTER_GUIDES_MISSING_REQUIRED_VARIABLE '
            results = {
                'success':                          success,
                'status':                           status,
                'number_of_voter_guides_found':     number_of_voter_guides_found,
                'number_of_voter_guides_deleted':   number_of_voter_guides_deleted,
                'voter_guide_found':                voter_guide_found,
                'voter_guide':                      voter_guide,
            }
            return results

        # Find full list of voter guides
        try:
            voter_guide_query = VoterGuide.objects.order_by('pk')
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.filter(organization_we_vote_id=organization_we_vote_id)
            voter_guide_list = voter_guide_query.filter(google_civic_election_id=google_civic_election_id)

            number_of_voter_guides_found = len(voter_guide_list)
            if positive_value_exists(number_of_voter_guides_found):
                status += 'MERGE_DUPLICATE_VOTER_GUIDES_VOTER_GUIDES_FOUND: ' + str(number_of_voter_guides_found) + ' '
            else:
                status += 'MERGE_DUPLICATE_VOTER_GUIDES_NO_VOTER_GUIDES_FOUND '
            success = True
        except Exception as e:
            status += 'merge_duplicate_voter_guides_for_organization_and_election: ' \
                      'Unable to retrieve voter guides from db. ' \
                      '{error} [type: {error_type}] '.format(error=e, error_type=type(e))
            success = False

        # If there are more than one voter_guides found, delete extras after merging in data
        new_master_voter_guide = None
        if success:
            is_first_voter_guide = True
            if number_of_voter_guides_found > 1:
                for one_voter_guide in voter_guide_list:
                    if is_first_voter_guide:
                        new_master_voter_guide = one_voter_guide
                        is_first_voter_guide = False
                        continue
                    else:
                        new_master_voter_guide_changed = False
                        # Take oldest one, and add any new information from the later entries
                        # Merge in duplicate voter guide before deleting
                        try:
                            if not new_master_voter_guide.display_name:
                                new_master_voter_guide_changed = True
                                new_master_voter_guide.display_name = one_voter_guide.display_name
                            if not new_master_voter_guide.election_day_text:
                                new_master_voter_guide_changed = True
                                new_master_voter_guide.election_day_text = one_voter_guide.election_day_text
                            if not new_master_voter_guide.state_code:
                                new_master_voter_guide_changed = True
                                new_master_voter_guide.state_code = one_voter_guide.state_code
                            if new_master_voter_guide.vote_smart_ratings_only:
                                new_master_voter_guide_changed = True
                                new_master_voter_guide.vote_smart_ratings_only = False
                            if new_master_voter_guide_changed:
                                new_master_voter_guide.save()
                            one_voter_guide.delete()
                            number_of_voter_guides_deleted += 1
                        except Exception as e:
                            status += 'MERGE_DUPLICATE_VOTER_GUIDES-MERGE_FAILED {error} [type: {error_type}] ' \
                                      ''.format(error=e, error_type=type(e))
                            success = False

        if success:
            if number_of_voter_guides_found == 1:
                status += 'ONE_FOUND '
                voter_guide_found = True
                voter_guide = voter_guide_list[0]
            else:
                status += 'VOTER_GUIDES_MERGED '
                voter_guide_found = True
                voter_guide = new_master_voter_guide

        results = {
            'success':                          success,
            'status':                           status,
            'number_of_voter_guides_found':     number_of_voter_guides_found,
            'number_of_voter_guides_deleted':   number_of_voter_guides_deleted,
            'voter_guide_found':                voter_guide_found,
            'voter_guide':                      voter_guide,
        }
        return results

    @staticmethod
    def save_voter_guide_object(voter_guide):
        """
        """
        try:
            voter_guide.save()
        except Exception as e:
            handle_exception(e, logger=logger)

        return voter_guide


class VoterGuide(models.Model):
    # We are relying on built-in Python id field

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our voter_guide
    # info with other organizations running their own We Vote servers
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "vg" (for voter guide), and then a sequential integer like "123".
    # We generate this id on initial save keep the last value in WeVoteSetting.we_vote_id_last_voter_guide_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=True, db_index=True)

    # NOTE: We are using we_vote_id's instead of internal ids
    # The unique id of the organization. May be null if voter_guide owned by a public figure or voter instead of org.
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote id", max_length=255, null=True, blank=True, unique=False, db_index=True)
    voter_we_vote_id = models.CharField(
        verbose_name="voter who owns the organization", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the public figure. May be null if voter_guide owned by org or voter instead of public figure.
    public_figure_we_vote_id = models.CharField(
        verbose_name="public figure we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the public figure. May be null if voter_guide owned by org or public figure instead of voter.
    owner_we_vote_id = models.CharField(
        verbose_name="individual voter's we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the voter that owns this guide. May be null if voter_guide owned by an org
    # or public figure instead of by a voter.
    # DEPRECATE THIS - 2015-11-11 We should use
    owner_voter_id = models.PositiveIntegerField(
        verbose_name="the unique voter id of the voter who this guide is about", default=0, null=True, blank=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, db_index=True)
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    state_code = models.CharField(verbose_name="state the voter_guide is related to", max_length=2, null=True)

    # Usually in one of these two formats 2015, 2014-2015
    vote_smart_time_span = models.CharField(
        verbose_name="the period in which the organization stated this position", max_length=255, null=True,
        blank=True, unique=False, db_index=True)

    # This might be the organization name, or the individual's name
    display_name = models.CharField(
        verbose_name="display title for this voter guide", max_length=255, null=True, blank=True, unique=False)

    image_url = models.TextField(
        verbose_name='image url of logo/photo associated with voter guide', blank=True, null=True)
    we_vote_hosted_profile_image_url_large = models.TextField(
        verbose_name='large version image url of logo/photo associated with voter guide', blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(
        verbose_name='medium version image url of logo/photo associated with voter guide', blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(
        verbose_name='tiny version image url of logo/photo associated with voter guide', blank=True, null=True)

    # Mapped directly from organization.organization_type
    voter_guide_owner_type = models.CharField(
        verbose_name="is owner org, public figure, or voter?", max_length=2, choices=ORGANIZATION_TYPE_CHOICES,
        default=UNKNOWN)

    twitter_handle = models.CharField(verbose_name='twitter username', max_length=255, null=True, unique=False)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)
    twitter_followers_count = models.PositiveIntegerField(
        verbose_name="number of twitter followers", null=True, blank=True, default=0)

    pledge_goal = models.PositiveIntegerField(
        verbose_name="target number of voters for pledge drive", null=True, blank=True, default=0)
    pledge_count = models.PositiveIntegerField(
        verbose_name="number of voters who have pledged", null=True, blank=True, default=0)

    vote_smart_ratings_only = models.BooleanField(default=False)

    # We usually cache the voter guide name, but in case we haven't, we force the lookup
    def voter_guide_display_name(self):
        if self.display_name:
            return self.display_name
        elif self.voter_guide_owner_type == ORGANIZATION:
            return self.retrieve_organization_display_name()
        return ''

    def retrieve_organization_display_name(self):
        organization_manager = OrganizationManager()
        organization_id = 0
        organization_we_vote_id = self.organization_we_vote_id
        results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)
        if results['organization_found']:
            organization = results['organization']
            organization_name = organization.organization_name
            return organization_name

    # We try to cache the image_url, but in case we haven't, we force the lookup
    def voter_guide_image_url(self):
        if self.image_url:
            return self.image_url
        elif self.voter_guide_owner_type == ORGANIZATION:
            organization_manager = OrganizationManager()
            organization_id = 0
            organization_we_vote_id = self.organization_we_vote_id
            results = organization_manager.retrieve_organization(organization_id, organization_we_vote_id)
            if results['organization_found']:
                organization = results['organization']
                organization_photo_url = organization.organization_photo_url()
                return organization_photo_url
        return ''

    # The date of the last change to this voter_guide
    # TODO convert to date_last_changed
    last_updated = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # We want to map these here so they are available in the templates
    CORPORATION = CORPORATION
    GROUP = GROUP  # Group of people (not an individual), but org status unknown
    INDIVIDUAL = INDIVIDUAL
    NEWS_ORGANIZATION = NEWS_ORGANIZATION
    NONPROFIT = NONPROFIT
    NONPROFIT_501C3 = NONPROFIT_501C3
    NONPROFIT_501C4 = NONPROFIT_501C4
    POLITICAL_ACTION_COMMITTEE = POLITICAL_ACTION_COMMITTEE
    ORGANIZATION = ORGANIZATION  # Deprecate in favor of GROUP
    PUBLIC_FIGURE = PUBLIC_FIGURE
    TRADE_ASSOCIATION = TRADE_ASSOCIATION
    VOTER = VOTER  # Deprecate in favor of Individual
    UNKNOWN = UNKNOWN

    def __unicode__(self):
        return self.last_updated

    class Meta:
        ordering = ('last_updated',)

    objects = VoterGuideManager()

    def organization(self):
        try:
            organization = Organization.objects.using('readonly').get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("voter_guide.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("voter_guide.organization did not find")
            return
        return organization

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this voter_guide came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            self.generate_new_we_vote_id()
        try:
            # Attempt 1
            super(VoterGuide, self).save(*args, **kwargs)
        except Exception as e:
            logger.error("VoterGuide Unable to Save Attempt 1: " + str(self.we_vote_id) + " " + str(e))

    def generate_new_we_vote_id(self):
        # ...generate a new id
        site_unique_id_prefix = fetch_site_unique_id_prefix()
        next_local_integer = fetch_next_we_vote_id_voter_guide_integer()
        # "wv" = We Vote
        # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
        # "vg" = tells us this is a unique id for a voter guide
        # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
        self.we_vote_id = "wv{site_unique_id_prefix}vg{next_integer}".format(
            site_unique_id_prefix=site_unique_id_prefix,
            next_integer=next_local_integer,
        )
        return


# This is the class that we use to rapidly show lists of voter guides, regardless of whether they are from an
# organization, public figure, or voter
class VoterGuideListManager(models.Manager):
    """
    A set of methods to retrieve a list of voter_guides
    """

    # NOTE: This is extremely simple way to retrieve voter guides, used by admin tools. Being replaced by:
    #  retrieve_voter_guides_by_ballot_item(ballot_item_we_vote_id) AND
    #  retrieve_voter_guides_by_election(google_civic_election_id)
    @staticmethod
    def retrieve_voter_guides_for_election(google_civic_election_id_list, exclude_voter_guide_owner_type_list=[]):
        voter_guide_list = []
        voter_guide_list_found = False

        try:
            # voter_guide_query = VoterGuide.objects.order_by('-twitter_followers_count')
            voter_guide_query = VoterGuide.objects.order_by('display_name')
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.filter(
                google_civic_election_id__in=google_civic_election_id_list)
            if len(exclude_voter_guide_owner_type_list):
                voter_guide_query = \
                    voter_guide_query.exclude(voter_guide_owner_type__in=exclude_voter_guide_owner_type_list)
            voter_guide_list = list(voter_guide_query)
            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_voter_guides_for_election: Unable to retrieve voter guides from db. ' + str(e) + ' '
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    @staticmethod
    def retrieve_google_civic_election_id_list_for_elections_with_voter_guides():
        google_civic_election_id_list = []
        voter_guide_list = []
        google_civic_election_id_list_found = False

        try:
            # order_by is required for the distinct to work correctly
            voter_guide_query = VoterGuide.objects.using('readonly').\
                order_by().values('google_civic_election_id').distinct()
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.exclude(google_civic_election_id=2000)
            voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                google_civic_election_id_list_found = True
                status = 'VOTER_GUIDES_FOUND-RETRIEVE_GOOGLE_CIVIC_ELECTION_ID_LIST '
            else:
                status = 'NO_VOTER_GUIDES_FOUND-RETRIEVE_GOOGLE_CIVIC_ELECTION_ID_LIST '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_google_civic_election_id_list_for_elections_with_voter_guides: ' \
                     'Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if google_civic_election_id_list_found:
            for voter_guide in voter_guide_list:
                if positive_value_exists(voter_guide['google_civic_election_id']) \
                        and voter_guide['google_civic_election_id'] not in google_civic_election_id_list:
                    google_civic_election_id_list.append(voter_guide['google_civic_election_id'])

        results = {
            'success':                              success,
            'status':                               status,
            'google_civic_election_id_list_found':  google_civic_election_id_list_found,
            'google_civic_election_id_list':        google_civic_election_id_list,
        }
        return results

    def retrieve_voter_guides_by_organization_list(self, organization_we_vote_ids_followed_by_voter,
                                                   filter_by_this_google_civic_election_id=False):
        voter_guide_list = []
        voter_guide_list_found = False
        status = ''

        if not type(organization_we_vote_ids_followed_by_voter) is list:
            status += 'NO_VOTER_GUIDES_FOUND_MISSING_ORGANIZATION_LIST '
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'voter_guide_list_found':       voter_guide_list_found,
                'voter_guide_list':             voter_guide_list,
            }
            return results

        if not len(organization_we_vote_ids_followed_by_voter):
            status += 'NO_VOTER_GUIDES_FOUND_NO_ORGANIZATIONS_IN_LIST '
            success = True
            results = {
                'success':                      success,
                'status':                       status,
                'voter_guide_list_found':       voter_guide_list_found,
                'voter_guide_list':             voter_guide_list,
            }
            return results

        try:
            voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.filter(
                organization_we_vote_id__in=organization_we_vote_ids_followed_by_voter)
            test_election = 2000
            voter_guide_query = voter_guide_query.exclude(google_civic_election_id=test_election)
            if filter_by_this_google_civic_election_id:
                voter_guide_query = voter_guide_query.filter(
                    google_civic_election_id=filter_by_this_google_civic_election_id)
            voter_guide_query = voter_guide_query.order_by('-twitter_followers_count')
            voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status += 'VOTER_GUIDES_FOUND_BY_ORGANIZATION_LIST '
            else:
                status += 'NO_VOTER_GUIDES_FOUND_BY_ORGANIZATION_LIST '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status += 'RETRIEVE_VOTER_GUIDES_BY_ORGANIZATION_LIST: Unable to retrieve voter guides from db. ' \
                      '{error} [type: {error_type}] '.format(error=e.message, error_type=type(e))
            success = False

        # If we have multiple voter guides for one org, we only want to show the most recent
        if voter_guide_list_found:
            voter_guide_list_filtered = self.remove_older_voter_guides_for_each_org(voter_guide_list)
        else:
            voter_guide_list_filtered = []

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list_filtered,
        }
        return results

    def retrieve_all_voter_guides_by_organization_we_vote_id(self, organization_we_vote_id, read_only=True):
        return self.retrieve_all_voter_guides(organization_we_vote_id, read_only=read_only)

    def retrieve_all_voter_guides_by_voter_id(self, owner_voter_id, read_only=True):
        organization_we_vote_id = ""
        return self.retrieve_all_voter_guides(organization_we_vote_id, owner_voter_id, read_only=read_only)

    def retrieve_all_voter_guides_by_voter_we_vote_id(self, owner_voter_we_vote_id, read_only=True):
        organization_we_vote_id = ""
        owner_voter_id = 0
        return self.retrieve_all_voter_guides(organization_we_vote_id, owner_voter_id, owner_voter_we_vote_id,
                                              read_only=read_only)

    @staticmethod
    def retrieve_all_voter_guides(
            organization_we_vote_id,
            owner_voter_id=0,
            owner_voter_we_vote_id="",
            maximum_number_to_retrieve=0,
            read_only=True):
        status = ''
        voter_guide_list = []
        voter_guide_list_found = False

        if not positive_value_exists(organization_we_vote_id) and not positive_value_exists(owner_voter_id) and \
                not positive_value_exists(owner_voter_we_vote_id):
            status += 'NO_VOTER_GUIDES_FOUND-MISSING_REQUIRED_VARIABLE '
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'voter_guide_list_found':       voter_guide_list_found,
                'voter_guide_list':             voter_guide_list,
            }
            return results

        try:
            if positive_value_exists(read_only):
                voter_guide_query = VoterGuide.objects.using('readonly').all()
            else:
                voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.order_by('-election_day_text')
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            if positive_value_exists(organization_we_vote_id):
                voter_guide_query = voter_guide_query.filter(
                    organization_we_vote_id__iexact=organization_we_vote_id)
            elif positive_value_exists(owner_voter_id):
                voter_guide_query = voter_guide_query.filter(
                    owner_voter_id=owner_voter_id)
            elif positive_value_exists(owner_voter_we_vote_id):
                voter_guide_query = voter_guide_query.filter(
                    owner_we_vote_id__iexact=owner_voter_we_vote_id)
            if positive_value_exists(maximum_number_to_retrieve):
                voter_guide_list = voter_guide_query[:maximum_number_to_retrieve]
            else:
                voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status += 'VOTER_GUIDES_FOUND_BY_RETRIEVE_ALL_VOTER_GUIDES '
            else:
                status += 'NO_VOTER_GUIDES_FOUND_BY_RETRIEVE_ALL_VOTER_GUIDES '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status += 'retrieve_all_voter_guides: Unable to retrieve voter guides from db. ' + str(e) + ' '
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    @staticmethod
    def retrieve_voter_guides_to_follow_by_election(
            google_civic_election_id,
            organization_we_vote_id_list,
            search_string,
            start_retrieve_at_this_number=0,
            maximum_number_to_retrieve=0,
            sort_by='',
            sort_order='',
            read_only=False):
        voter_guide_list = []
        voter_guide_list_found = False
        if not positive_value_exists(maximum_number_to_retrieve):
            maximum_number_to_retrieve = 30

        try:
            if read_only:
                voter_guide_query = VoterGuide.objects.using('readonly').all()
            else:
                voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            if search_string:
                voter_guide_query = voter_guide_query.filter(Q(display_name__icontains=search_string) |
                                                             Q(twitter_handle__icontains=search_string))
            else:
                # If not searching, make sure we do not include individuals
                voter_guide_query = voter_guide_query.exclude(voter_guide_owner_type__iexact=INDIVIDUAL)

            if positive_value_exists(len(organization_we_vote_id_list)):
                voter_guide_query = voter_guide_query.filter(
                    Q(google_civic_election_id=google_civic_election_id) &
                    Q(organization_we_vote_id__in=organization_we_vote_id_list)
                )
            else:
                voter_guide_query = voter_guide_query.filter(google_civic_election_id=google_civic_election_id)

            if positive_value_exists(start_retrieve_at_this_number):
                query_start_number = start_retrieve_at_this_number
                query_end_number = start_retrieve_at_this_number + maximum_number_to_retrieve
            else:
                query_start_number = 0
                query_end_number = maximum_number_to_retrieve

            if sort_order == 'desc':
                voter_guide_query = voter_guide_query.order_by('-' + sort_by)[query_start_number:query_end_number]
            else:
                voter_guide_query = voter_guide_query.order_by(sort_by)[query_start_number:query_end_number]

            voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDES_FOUND_BY_ELECTION '
            else:
                status = 'NO_VOTER_GUIDES_FOUND_BY_ELECTION '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_voter_guides_to_follow_by_election: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        # status += " len(organization_we_vote_id_list): " + str(len(organization_we_vote_id_list)) + " :: "
        # for one_we_vote_id in organization_we_vote_id_list:
        #     status += one_we_vote_id + " "

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    @staticmethod
    def retrieve_voter_guides_to_follow_by_time_span(
            orgs_we_need_found_by_position_and_time_span_list_of_dicts,
            search_string,
            maximum_number_to_retrieve=0,
            sort_by='',
            sort_order=''):
        """
        Get the voter guides for orgs that we found by looking at the positions for an org found based on time span
        """
        voter_guide_list = []
        voter_guide_list_found = False
        if not positive_value_exists(maximum_number_to_retrieve):
            maximum_number_to_retrieve = 30

        if not len(orgs_we_need_found_by_position_and_time_span_list_of_dicts):
            status = "NO_VOTER_GUIDES_FOUND_BY_TIME_SPAN"
            results = {
                'success': True,
                'status': status,
                'voter_guide_list_found': voter_guide_list_found,
                'voter_guide_list': voter_guide_list,
            }
            return results

        try:
            voter_guide_query = VoterGuide.objects.all()

            # Retrieve all pairs that match vote_smart_time_span / organization_we_vote_id
            filter_list = Q()
            for item in orgs_we_need_found_by_position_and_time_span_list_of_dicts:
                filter_list |= Q(vote_smart_time_span=item['vote_smart_time_span'],
                                 organization_we_vote_id__iexact=item['organization_we_vote_id'])
            voter_guide_query = voter_guide_query.filter(filter_list)

            if search_string:
                voter_guide_query = voter_guide_query.filter(
                    Q(display_name__icontains=search_string) | Q(twitter_handle__icontains=search_string)
                )

            if sort_order == 'desc':
                voter_guide_query = voter_guide_query.order_by('-' + sort_by)[:maximum_number_to_retrieve]
            else:
                voter_guide_query = voter_guide_query.order_by(sort_by)[:maximum_number_to_retrieve]

            voter_guide_list = voter_guide_query
            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_voter_guides_to_follow_by_time_span: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def retrieve_voter_guides_to_follow_generic(self, organization_we_vote_ids_followed_or_ignored_by_voter=[],
                                                search_string='',
                                                maximum_number_to_retrieve=0, sort_by='', sort_order='',
                                                google_civic_election_id_list=[],
                                                read_only=False):
        """
        Get the voter guides for orgs that we found by looking at the positions for an org found based on time span
        """
        status = ""
        voter_guide_list = []
        voter_guide_list_found = False
        if not positive_value_exists(maximum_number_to_retrieve):
            maximum_number_to_retrieve = 30

        try:
            if read_only:
                voter_guide_query = VoterGuide.objects.using('readonly').all()
            else:
                voter_guide_query = VoterGuide.objects.all()
            # As of August 2018, we no longer want to support Vote Smart ratings voter guides
            voter_guide_query = voter_guide_query.exclude(vote_smart_time_span__isnull=False)
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)

            if positive_value_exists(len(organization_we_vote_ids_followed_or_ignored_by_voter)):
                voter_guide_query = voter_guide_query.exclude(
                    organization_we_vote_id__in=organization_we_vote_ids_followed_or_ignored_by_voter)

            if positive_value_exists(len(google_civic_election_id_list)):
                status += "CONVERTING_GOOGLE_CIVIC_ELECTION_ID_LIST_TO_INTEGER "
                google_civic_election_id_integer_list = []
                for google_civic_election_id in google_civic_election_id_list:
                    google_civic_election_id_integer_list.append(convert_to_int(google_civic_election_id))
                voter_guide_query = voter_guide_query.filter(
                    google_civic_election_id__in=google_civic_election_id_integer_list)

            if search_string:
                # Each word in the search string can be anywhere in any field we search
                try:
                    data = search_string.split()
                except Exception as e:
                    status += "SEARCH_STRING_COULD_NOT_BE_SPLIT "
                    data = []

                for search_string_part in data:
                    voter_guide_query = voter_guide_query.filter(Q(display_name__icontains=search_string_part) |
                                                                 Q(twitter_handle__icontains=search_string_part))
            else:
                # If not searching, make sure we do not include individuals. We *do* retrieve PUBLIC_FIGURES
                status += "NOT_SEARCHING-EXCLUDING_INDIVIDUALS "
                voter_guide_query = voter_guide_query.exclude(voter_guide_owner_type__iexact=INDIVIDUAL)

                if not positive_value_exists(len(google_civic_election_id_list)):
                    # We also want to exclude voter guides with election_day_text smaller than today's date
                    status += "EXCLUDE_PAST_ELECTION_DAYS "
                    # timezone = pytz.timezone("America/Los_Angeles")
                    # datetime_now = timezone.localize(datetime.now())
                    datetime_now = generate_localized_datetime_from_obj()[1]
                    two_days = timedelta(days=2)
                    datetime_two_days_ago = datetime_now - two_days
                    earliest_date_to_show = datetime_two_days_ago.strftime("%Y-%m-%d")
                    voter_guide_query = voter_guide_query.exclude(election_day_text__lt=earliest_date_to_show)
                    voter_guide_query = voter_guide_query.exclude(election_day_text__isnull=True)

            if sort_order == 'desc':
                voter_guide_query = voter_guide_query.order_by('-' + sort_by)[:maximum_number_to_retrieve]
            elif positive_value_exists(sort_by):
                voter_guide_query = voter_guide_query.order_by(sort_by)[:maximum_number_to_retrieve]
            else:
                voter_guide_query = voter_guide_query[:maximum_number_to_retrieve]

            voter_guide_list = list(voter_guide_query)
            if len(voter_guide_list):
                voter_guide_list_found = True
                status += 'VOTER_GUIDE_FOUND_GENERIC_VOTER_GUIDES_TO_FOLLOW '
            else:
                status += 'NO_VOTER_GUIDES_FOUND_GENERIC_VOTER_GUIDES_TO_FOLLOW '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status += 'retrieve_voter_guides_to_follow_generic: Unable to retrieve voter guides from db. ' \
                      '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        # If we have multiple voter guides for one org, we only want to show the most recent
        voter_guide_list_filtered = []
        if voter_guide_list_found:
            if not positive_value_exists(len(google_civic_election_id_list)):
                # If we haven't specified multiple elections, then remove old voter guides
                voter_guide_list_filtered = self.remove_older_voter_guides_for_each_org(voter_guide_list)
            else:
                voter_guide_list_filtered = voter_guide_list
        else:
            voter_guide_list_filtered = []

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list_filtered,
        }
        return results

    @staticmethod
    def remove_older_voter_guides_for_each_org(voter_guide_list):
        # If we have multiple voter guides for one org, we only want to show the most recent
        organization_already_reviewed = []
        organization_with_multiple_voter_guides = []
        newest_voter_guide_for_org = {}  # Figure out the newest voter guide per org that we should show
        for one_voter_guide in voter_guide_list:
            if one_voter_guide.organization_we_vote_id:
                if one_voter_guide.organization_we_vote_id not in organization_already_reviewed:
                    organization_already_reviewed.append(one_voter_guide.organization_we_vote_id)
                # Are we dealing with a time span (instead of google_civic_election_id)?
                if positive_value_exists(one_voter_guide.vote_smart_time_span):
                    # Take the first four digits of one_voter_guide.vote_smart_time_span
                    first_four_digits = convert_to_int(one_voter_guide.vote_smart_time_span[:4])
                    # And figure out the newest voter guide for each org
                    if one_voter_guide.organization_we_vote_id in newest_voter_guide_for_org:
                        # If we are here, it means we have seen this organization once already
                        if one_voter_guide.organization_we_vote_id not in organization_with_multiple_voter_guides:
                            organization_with_multiple_voter_guides.append(one_voter_guide.organization_we_vote_id)
                        # If this voter guide is newer than the one already looked at, update newest_voter_guide_for_org
                        if first_four_digits > newest_voter_guide_for_org[one_voter_guide.organization_we_vote_id]:
                            newest_voter_guide_for_org[one_voter_guide.organization_we_vote_id] = first_four_digits
                    else:
                        newest_voter_guide_for_org[one_voter_guide.organization_we_vote_id] = first_four_digits

        voter_guide_list_filtered = []
        for one_voter_guide in voter_guide_list:
            if one_voter_guide.organization_we_vote_id in organization_with_multiple_voter_guides:
                if positive_value_exists(one_voter_guide.vote_smart_time_span):
                    first_four_digits = convert_to_int(one_voter_guide.vote_smart_time_span[:4])
                    if newest_voter_guide_for_org[one_voter_guide.organization_we_vote_id] == first_four_digits:
                        # If this voter guide is the newest from among the org's voter guides, include in results
                        voter_guide_list_filtered.append(one_voter_guide)
            else:
                voter_guide_list_filtered.append(one_voter_guide)

        return voter_guide_list_filtered

    @staticmethod
    def retrieve_all_voter_guides_order_by(
            order_by='',
            limit_number=0,
            search_string='',
            google_civic_election_id=0,
            show_individuals=False):
        voter_guide_list = []
        voter_guide_list_found = False
        try:
            voter_guide_query = VoterGuide.objects.all()
            voter_guide_query = voter_guide_query.exclude(vote_smart_ratings_only=True)
            voter_guide_query = voter_guide_query.exclude(vote_smart_time_span__isnull=False)
            if not positive_value_exists(show_individuals):
                voter_guide_query = voter_guide_query.exclude(voter_guide_owner_type__iexact=INDIVIDUAL)
            if positive_value_exists(google_civic_election_id):
                voter_guide_query = voter_guide_query.filter(google_civic_election_id=google_civic_election_id)
            if order_by == 'google_civic_election_id':
                voter_guide_query = voter_guide_query.order_by(
                    '-vote_smart_time_span', '-google_civic_election_id')
            else:
                voter_guide_query = voter_guide_query.order_by('-twitter_followers_count')

            if positive_value_exists(search_string):
                try:
                    search_words = search_string.split()
                except Exception as e:
                    search_words = []
                for one_word in search_words:
                    filters = []

                    new_filter = Q(we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(display_name__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(google_civic_election_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(organization_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(owner_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(public_figure_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(state_code__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(twitter_handle__icontains=one_word)
                    filters.append(new_filter)

                    # Add the first query
                    if len(filters):
                        final_filters = filters.pop()

                        # ...and "OR" the remaining items in the list
                        for item in filters:
                            final_filters |= item

                        voter_guide_query = voter_guide_query.filter(final_filters)

            if positive_value_exists(limit_number):
                voter_guide_list = voter_guide_query[:limit_number]
            else:
                voter_guide_list = list(voter_guide_query)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_all_voter_guides_order_by: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    @staticmethod
    def reorder_voter_guide_list(voter_guide_list, field_to_order_by, asc_or_desc='desc'):
        def get_key_to_sort_by():
            if field_to_order_by == 'twitter_followers_count':
                return 'twitter_followers_count'
            else:
                return 'twitter_followers_count'

        if not len(voter_guide_list):
            return []

        # If we set this to 'desc', then Reverse the sort below. Otherwise sort 'asc' (ascending)
        is_desc = True if asc_or_desc == 'desc' else False

        voter_guide_list_sorted = sorted(voter_guide_list, key=operator.attrgetter(get_key_to_sort_by()),
                                         reverse=is_desc)

        return voter_guide_list_sorted

    @staticmethod
    def retrieve_possible_duplicate_voter_guides(
            google_civic_election_id,
            vote_smart_time_span,
            organization_we_vote_id,
            public_figure_we_vote_id,
            twitter_handle,
            we_vote_id_from_master=''):
        voter_guide_list_objects = []
        filters = []
        voter_guide_list_found = False

        try:
            voter_guide_query = VoterGuide.objects.all()
            if positive_value_exists(google_civic_election_id):
                voter_guide_query = voter_guide_query.filter(google_civic_election_id=google_civic_election_id)
            elif positive_value_exists(vote_smart_time_span):
                voter_guide_query = voter_guide_query.filter(vote_smart_time_span__iexact=vote_smart_time_span)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                voter_guide_query = voter_guide_query.exclude(we_vote_id__iexact=we_vote_id_from_master)

            # We want to find candidates with *any* of these values
            if positive_value_exists(organization_we_vote_id):
                new_filter = Q(organization_we_vote_id__iexact=organization_we_vote_id)
                filters.append(new_filter)

            if positive_value_exists(public_figure_we_vote_id):
                new_filter = Q(public_figure_we_vote_id__iexact=public_figure_we_vote_id)
                filters.append(new_filter)

            if positive_value_exists(twitter_handle):
                new_filter = Q(twitter_handle__iexact=twitter_handle)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                voter_guide_query = voter_guide_query.filter(final_filters)

            voter_guide_list_objects = voter_guide_query

            if len(voter_guide_list_objects):
                voter_guide_list_found = True
                status = 'DUPLICATE_VOTER_GUIDES_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_VOTER_GUIDES_RETRIEVED'
                success = True
        except VoterGuide.DoesNotExist:
            # No voter guides found. Not a problem.
            status = 'NO_DUPLICATE_VOTER_GUIDES_FOUND_DoesNotExist'
            voter_guide_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_possible_duplicate_voter_guides ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'google_civic_election_id': google_civic_election_id,
            'voter_guide_list_found':   voter_guide_list_found,
            'voter_guide_list':         voter_guide_list_objects,
        }
        return results


class VoterGuidePossibilityManager(models.Manager):
    """
    A class for working with the VoterGuidePossibility and VoterGuidePossibilityPosition model
    """

    @staticmethod
    def update_or_create_voter_guide_possibility(
            voter_guide_possibility_url='',
            voter_who_submitted_we_vote_id='',
            voter_guide_possibility_id=0,
            target_google_civic_election_id=0,
            updated_values={}):
        exception_multiple_object_returned = False
        success = True
        voter_guide_possibility_created = False
        voter_guide_possibility = None
        voter_guide_possibility_found = False
        status = ""

        if positive_value_exists(voter_guide_possibility_id):
            # Check before we try to create a new entry
            try:
                voter_guide_possibility = VoterGuidePossibility.objects.get(
                    id=voter_guide_possibility_id,
                )
                voter_guide_possibility_found = True
                success = True
                status += 'VOTER_GUIDE_POSSIBILITY_FOUND_BY_ID '
            except VoterGuidePossibility.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_VOTER_GUIDE_POSSIBILITY_NOT_FOUND_BY_WE_VOTE_ID "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_BY_WE_VOTE_ID ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        if not voter_guide_possibility_found:
            try:
                now = datetime.now()
                voter_guide_possibility_query = VoterGuidePossibility.objects.filter(
                    voter_guide_possibility_url__iexact=voter_guide_possibility_url,
                    hide_from_active_review=False,
                    date_last_changed__year=now.year,
                )
                # Dale: As of Jun 2024, we only want to save one voter_guide_possibility instance per year
                voter_guide_possibility = voter_guide_possibility_query.first()
                if voter_guide_possibility and hasattr(voter_guide_possibility, 'voter_guide_possibility_url'):
                    voter_guide_possibility_found = True
                    status += 'VOTER_GUIDE_POSSIBILITY_FOUND_BY_URL '
                else:
                    status += 'VOTER_GUIDE_POSSIBILITY_NOT_FOUND_BY_URL '
            except VoterGuidePossibility.DoesNotExist:
                status += "RETRIEVE_VOTER_GUIDE_POSSIBILITY_NOT_FOUND_BY_URL "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_BY_URL ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        if voter_guide_possibility_found:
            # Update record
            try:
                voter_guide_possibility_created = False
                voter_guide_possibility_updated = False
                voter_guide_possibility_has_changes = False
                done_verified_previous = voter_guide_possibility.done_verified
                done_verified_flipped_from_false_to_true = False
                if 'done_verified' in updated_values and positive_value_exists(updated_values['done_verified']):
                    done_verified_new = updated_values['done_verified']
                    done_verified_flipped_from_false_to_true = done_verified_new and not done_verified_previous
                if done_verified_flipped_from_false_to_true:
                    if 'voter_who_submitted_name' in updated_values and \
                            positive_value_exists(updated_values['voter_who_submitted_name']):
                        updated_values['verified_by_name'] = updated_values['voter_who_submitted_name']
                    if 'voter_who_submitted_we_vote_id' in updated_values and \
                            positive_value_exists(updated_values['voter_who_submitted_we_vote_id']):
                        updated_values['verified_by_we_vote_id'] = updated_values['voter_who_submitted_we_vote_id']
                for key, value in updated_values.items():
                    if hasattr(voter_guide_possibility, key):
                        voter_guide_possibility_has_changes = True
                        setattr(voter_guide_possibility, key, value)
                if voter_guide_possibility_has_changes and positive_value_exists(voter_guide_possibility.id):
                    voter_guide_possibility.save()
                    voter_guide_possibility_id = voter_guide_possibility.id
                    voter_guide_possibility_updated = True
                if voter_guide_possibility_updated:
                    success = True
                    status += "VOTER_GUIDE_POSSIBILITY_UPDATED "
                else:
                    success = False
                    status += "VOTER_GUIDE_POSSIBILITY_NOT_UPDATED "
            except Exception as e:
                status += 'FAILED_TO_UPDATE_VOTER_GUIDE_POSSIBILITY ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        elif success:
            # Create record
            try:
                voter_guide_possibility_created = False
                voter_guide_possibility = VoterGuidePossibility.objects.create(
                    voter_guide_possibility_url=voter_guide_possibility_url,
                    target_google_civic_election_id=target_google_civic_election_id,
                )
                if positive_value_exists(voter_guide_possibility.id):
                    for key, value in updated_values.items():
                        if hasattr(voter_guide_possibility, key):
                            setattr(voter_guide_possibility, key, value)
                    voter_guide_possibility.save()
                    voter_guide_possibility_id = voter_guide_possibility.id
                    voter_guide_possibility_created = True
                if voter_guide_possibility_created:
                    success = True
                    status += "VOTER_GUIDE_POSSIBILITY_CREATED "
                else:
                    success = False
                    status += "VOTER_GUIDE_POSSIBILITY_NOT_CREATED "
            except Exception as e:
                status += 'FAILED_TO_CREATE_VOTER_GUIDE_POSSIBILITY ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success':                              success,
            'status':                               status,
            'MultipleObjectsReturned':              exception_multiple_object_returned,
            'voter_guide_possibility_created':      voter_guide_possibility_created,
            'voter_guide_possibility_saved':        success,
            'voter_guide_possibility':              voter_guide_possibility,
            'voter_guide_possibility_id':           voter_guide_possibility_id,
        }
        return results

    @staticmethod
    def update_or_create_voter_guide_possibility_position(
            voter_guide_possibility_position_id=0,
            voter_guide_possibility_id=0,
            updated_values={}):
        exception_multiple_object_returned = False

        success = False
        new_voter_guide_possibility_position_created = False
        voter_guide_possibility_position = VoterGuidePossibilityPosition()
        voter_guide_possibility_position_found = False
        status = ""

        if positive_value_exists(voter_guide_possibility_position_id):
            # Check before we try to create a new entry
            try:
                voter_guide_possibility_position = VoterGuidePossibilityPosition.objects.get(
                    id=voter_guide_possibility_position_id,
                )
                voter_guide_possibility_position_found = True
                success = True
                status += 'VOTER_GUIDE_POSSIBILITY_POSITION_FOUND_BY_ID '
            except VoterGuidePossibilityPosition.DoesNotExist:
                exception_does_not_exist = True
                status += "RETRIEVE_VOTER_GUIDE_POSSIBILITY_POSITION_NOT_FOUND_BY_WE_VOTE_ID "
            except Exception as e:
                status += 'FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_POSITION_BY_WE_VOTE_ID ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        # 2019-05 We no longer want to think of possibility_position_number as unique
        # if not voter_guide_possibility_position_found:
        #     try:
        #         voter_guide_possibility_position = VoterGuidePossibilityPosition.objects.get(
        #             voter_guide_possibility_parent_id=voter_guide_possibility_id,
        #             possibility_position_number=updated_values['possibility_position_number'],
        #         )
        #         voter_guide_possibility_position_id = voter_guide_possibility_position.id
        #         voter_guide_possibility_position_found = True
        #         success = True
        #         status += 'VOTER_GUIDE_POSSIBILITY_POSITION_FOUND_BY_URL '
        #     except VoterGuidePossibilityPosition.MultipleObjectsReturned as e:
        #         status += 'MULTIPLE_MATCHING_VOTER_GUIDE_POSSIBILITIES_FOUND_BY_URL-CREATE_NEW '
        #     except VoterGuidePossibilityPosition.DoesNotExist:
        #         status += "RETRIEVE_VOTER_GUIDE_POSSIBILITY_POSITION_NOT_FOUND_BY_URL "
        #     except Exception as e:
        #         status += 'FAILED_TO_RETRIEVE_VOTER_GUIDE_POSSIBILITY_POSITION_BY_URL ' \
        #                   '{error} [type: {error_type}]'.format(error=e, error_type=type(e))

        if voter_guide_possibility_position_found:
            # Update record
            try:
                new_voter_guide_possibility_position_created = False
                voter_guide_possibility_position_updated = False
                voter_guide_possibility_position_has_changes = False
                for key, value in updated_values.items():
                    if hasattr(voter_guide_possibility_position, key):
                        voter_guide_possibility_position_has_changes = True
                        setattr(voter_guide_possibility_position, key, value)
                if voter_guide_possibility_position_has_changes and \
                        positive_value_exists(voter_guide_possibility_position.id):
                    timezone = pytz.timezone("America/Los_Angeles")
                    voter_guide_possibility_position.date_updated = timezone.localize(datetime.now())
                    voter_guide_possibility_position.save()
                    voter_guide_possibility_position_id = voter_guide_possibility_position.id
                    voter_guide_possibility_position_updated = True
                if voter_guide_possibility_position_updated:
                    success = True
                    status += "VOTER_GUIDE_POSSIBILITY_POSITION_UPDATED "
                else:
                    success = False
                    status += "VOTER_GUIDE_POSSIBILITY_POSITION_NOT_UPDATED "
            except Exception as e:
                status += 'FAILED_TO_UPDATE_VOTER_GUIDE_POSSIBILITY ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
        else:
            # Create record
            if not positive_value_exists(voter_guide_possibility_id):
                status += "CANNOT_CREATE-MISSING_PARENT_ID "
                results = {
                    'success': False,
                    'status': status,
                    'MultipleObjectsReturned': exception_multiple_object_returned,
                    'voter_guide_possibility_position_saved': False,
                    'new_voter_guide_possibility_position_created': new_voter_guide_possibility_position_created,
                    'voter_guide_possibility_position': voter_guide_possibility_position,
                    'voter_guide_possibility_position_id': voter_guide_possibility_position_id,
                }
                return results

            try:
                new_voter_guide_possibility_position_created = False
                voter_guide_possibility_position = VoterGuidePossibilityPosition.objects.create(
                    voter_guide_possibility_parent_id=voter_guide_possibility_id,
                    possibility_position_number=updated_values['possibility_position_number'],
                )
                if positive_value_exists(voter_guide_possibility_position.id):
                    for key, value in updated_values.items():
                        if hasattr(voter_guide_possibility_position, key):
                            setattr(voter_guide_possibility_position, key, value)
                    timezone = pytz.timezone("America/Los_Angeles")
                    voter_guide_possibility_position.date_updated = timezone.localize(datetime.now())
                    voter_guide_possibility_position.save()
                    voter_guide_possibility_position_id = voter_guide_possibility_position.id
                    new_voter_guide_possibility_position_created = True
                if new_voter_guide_possibility_position_created:
                    success = True
                    status += "VOTER_GUIDE_POSSIBILITY_POSITION_CREATED "
                else:
                    success = False
                    status += "VOTER_GUIDE_POSSIBILITY_POSITION_NOT_CREATED "
            except Exception as e:
                status += 'FAILED_TO_CREATE_VOTER_GUIDE_POSSIBILITY ' \
                          '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False

        results = {
            'success': success,
            'status': status,
            'MultipleObjectsReturned': exception_multiple_object_returned,
            'voter_guide_possibility_position_saved': success,
            'new_voter_guide_possibility_position_created': new_voter_guide_possibility_position_created,
            'voter_guide_possibility_position': voter_guide_possibility_position,
            'voter_guide_possibility_position_id': voter_guide_possibility_position_id,
        }
        return results

    def retrieve_voter_guide_possibility_from_url(
            self,
            voter_guide_possibility_url="",
            pdf_url="",
            voter_who_submitted_we_vote_id="",
            google_civic_election_id=0,
            limit_to_this_year=True):
        voter_guide_possibility_id = 0
        return self.retrieve_voter_guide_possibility(
            voter_guide_possibility_id=voter_guide_possibility_id,
            google_civic_election_id=google_civic_election_id,
            voter_guide_possibility_url=voter_guide_possibility_url,
            pdf_url=pdf_url,
            # voter_who_submitted_we_vote_id=voter_who_submitted_we_vote_id,
            limit_to_this_year=limit_to_this_year)

    @staticmethod
    def retrieve_voter_guide_possibility(
            voter_guide_possibility_id=0,
            google_civic_election_id=0,
            voter_guide_possibility_url='',
            pdf_url='',
            organization_we_vote_id=None,
            voter_who_submitted_we_vote_id=None,
            limit_to_this_year=True):
        status = ""
        voter_guide_possibility_id = convert_to_int(voter_guide_possibility_id)
        google_civic_election_id = convert_to_int(google_civic_election_id)
        organization_we_vote_id = convert_to_str(organization_we_vote_id)
        voter_who_submitted_we_vote_id = convert_to_str(voter_who_submitted_we_vote_id)

        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_guide_possibility_on_stage = None
        voter_guide_possibility_on_stage_id = 0
        try:
            if positive_value_exists(voter_guide_possibility_id):
                status += "RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_ID "  # Set this in case the get fails
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(id=voter_guide_possibility_id)
                if voter_guide_possibility_on_stage is not None:
                    voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                    status += "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_ID "
                    success = True
                else:
                    status += "VOTER_GUIDE_POSSIBILITY_NOT_FOUND_WITH_ID "
                    success = True
            elif positive_value_exists(voter_guide_possibility_url):
                status += "RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_URL "  # Set this in case the get fails
                # Search both http and https
                voter_guide_possibility_url_alternate = \
                    voter_guide_possibility_url.lower().replace("https://", "http://")
                # If a replacement didn't happen...
                if len(voter_guide_possibility_url_alternate) == len(voter_guide_possibility_url):
                    voter_guide_possibility_url_alternate = \
                        voter_guide_possibility_url.lower().replace("http://", "https://")
                voter_guide_possibility_query = VoterGuidePossibility.objects.filter(
                    Q(voter_guide_possibility_url__iexact=voter_guide_possibility_url) |
                    Q(voter_guide_possibility_url__iexact=voter_guide_possibility_url_alternate))
                # DALE 2020-06-08 After working with this, it is better to include entries hidden from active review
                # voter_guide_possibility_query = voter_guide_possibility_query.exclude(hide_from_active_review=True)

                if positive_value_exists(limit_to_this_year):
                    # Only retrieve by URL if it was created this year
                    now = datetime.now()
                    status += "LIMITING_TO_THIS_YEAR: " + str(now.year) + " "
                    voter_guide_possibility_query = \
                        voter_guide_possibility_query.filter(date_last_changed__year=now.year)

                # Dale: As of Jun 2024, we only want to save one voter_guide_possibility instance per year
                # voter_guide_possibility_on_stage = voter_guide_possibility_query.last()
                voter_guide_possibility_on_stage = voter_guide_possibility_query.first()
                if voter_guide_possibility_on_stage is not None:
                    voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                    status += "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_URL "
                    success = True
                else:
                    status += "VOTER_GUIDE_POSSIBILITY_NOT_FOUND_WITH_URL "
                    success = True
            elif positive_value_exists(pdf_url):
                status += "RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_PDF_URL "  # Set this in case the get fails
                # Search both http and https
                voter_guide_possibility_query = VoterGuidePossibility.objects.filter(
                    Q(voter_guide_possibility_pdf_url__iexact=pdf_url))
                # DALE 2020-06-08 After working with this, it is better to include entries hidden from active review
                # voter_guide_possibility_query = voter_guide_possibility_query.exclude(hide_from_active_review=True)

                if positive_value_exists(limit_to_this_year):
                    # Only retrieve by URL if it was created this year
                    now = datetime.now()
                    status += "LIMITING_TO_THIS_YEAR: " + str(now.year) + " "
                    voter_guide_possibility_query = (
                        voter_guide_possibility_query.filter(date_last_changed__year=now.year)
                    )

                # Dale: As of Jun 2024, we only want to save one voter_guide_possibility instance per year
                # voter_guide_possibility_on_stage = voter_guide_possibility_query.last()
                voter_guide_possibility_on_stage = voter_guide_possibility_query.first()
                if voter_guide_possibility_on_stage is not None:
                    voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                    status += "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_PDF_URL "
                    success = True
                else:
                    status += "VOTER_GUIDE_POSSIBILITY_NOT_FOUND_WITH_PDF_URL "
                    success = True
            elif positive_value_exists(organization_we_vote_id) and positive_value_exists(google_civic_election_id):
                # Set this status in case the 'get' fails
                status += "RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_ORGANIZATION_WE_VOTE_ID "
                # TODO: Update this to deal with the google_civic_election_id being spread across 50 fields
                # Only retrieve by URL if it was created this year
                now = datetime.now()
                voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
                    google_civic_election_id=google_civic_election_id,
                    organization_we_vote_id__iexact=organization_we_vote_id,
                    hide_from_active_review=False,
                    date_last_changed__year=now.year)
                if voter_guide_possibility_on_stage is not None:
                    voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
                    status += "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_ORGANIZATION_WE_VOTE_ID "
                    success = True
                else:
                    status += "VOTER_GUIDE_POSSIBILITY_NOT_FOUND_WITH_ORGANIZATION_WE_VOTE_ID "
                    success = True
            # Dale: 2024-06 Deprecated
            # elif positive_value_exists(voter_who_submitted_we_vote_id) and \
            #         positive_value_exists(google_civic_election_id):
            #     # Set this status in case the 'get' fails
            #     status += "RETRIEVING_VOTER_GUIDE_POSSIBILITY_WITH_VOTER_WE_VOTE_ID "
            #     # TODO: Update this to deal with the google_civic_election_id being spread across 50 fields
            #     voter_guide_possibility_on_stage = VoterGuidePossibility.objects.get(
            #         google_civic_election_id=google_civic_election_id,
            #         voter_who_submitted_we_vote_id__iexact=voter_who_submitted_we_vote_id,
            #         hide_from_active_review=False)
            #     if voter_guide_possibility_on_stage is not None:
            #         voter_guide_possibility_on_stage_id = voter_guide_possibility_on_stage.id
            #         status += "VOTER_GUIDE_POSSIBILITY_FOUND_WITH_VOTER_WE_VOTE_ID "
            #         success = True
            #     else:
            #         status += "VOTER_GUIDE_POSSIBILITY_NOT_FOUND_WITH_VOTER_WE_VOTE_ID "
            #         success = True
            else:
                status += "VOTER_GUIDE_POSSIBILITY_NOT_FOUND_INSUFFICIENT_VARIABLES "
                success = False
        except VoterGuidePossibility.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status += "VOTER_GUIDE_POSSIBILITY_NOT_FOUND "
            success = True
        except Exception as e:
            error_result = True
            status += ", ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY: " + str(e)
            success = False

        voter_guide_possibility_on_stage_found = True if voter_guide_possibility_on_stage_id > 0 else False
        organization_we_vote_id_from_possibility = voter_guide_possibility_on_stage.organization_we_vote_id if \
            voter_guide_possibility_on_stage else None
        voter_guide_possibility_url_from_possibility = voter_guide_possibility_on_stage.voter_guide_possibility_url if \
            voter_guide_possibility_on_stage else None
        results = {
            'success':                          success,
            'status':                           status,
            'organization_we_vote_id':          organization_we_vote_id_from_possibility,
            'voter_guide_possibility':          voter_guide_possibility_on_stage,
            'voter_guide_possibility_found':    voter_guide_possibility_on_stage_found,
            'voter_guide_possibility_id':       voter_guide_possibility_on_stage_id,
            'voter_guide_possibility_url':      voter_guide_possibility_url_from_possibility,
            'error_result':                     error_result,
            'DoesNotExist':                     exception_does_not_exist,
            'MultipleObjectsReturned':          exception_multiple_object_returned,
        }
        return results

    @staticmethod
    def retrieve_voter_guide_possibility_list(
            order_by='',
            start_number=0,
            end_number=25,
            search_string='',
            google_civic_election_id=0,
            hide_from_active_review=False,
            cannot_find_endorsements=False,
            candidates_missing_from_we_vote=False,
            capture_detailed_comments=False,
            done_needs_verification=False,
            done_verified=False,
            from_prior_election=False,
            ignore_this_source=False,
            show_prior_years=False,
            assigned_to_no_one=False,
            assigned_to_voter_we_vote_id=False,
            read_only=True,
            return_count_only=False):
        start_number = convert_to_int(start_number)
        end_number = convert_to_int(end_number)
        hide_from_active_review = positive_value_exists(hide_from_active_review)
        candidates_missing_from_we_vote = positive_value_exists(candidates_missing_from_we_vote)
        cannot_find_endorsements = positive_value_exists(cannot_find_endorsements)
        capture_detailed_comments = positive_value_exists(capture_detailed_comments)
        done_needs_verification = positive_value_exists(done_needs_verification)
        done_verified = positive_value_exists(done_verified)
        from_prior_election = positive_value_exists(from_prior_election)
        ignore_this_source = positive_value_exists(ignore_this_source)
        return_count_only = positive_value_exists(return_count_only)

        status = ""
        voter_guide_possibility_list = []
        voter_guide_possibility_list_found = False
        voter_guide_possibility_list_count = 0
        try:
            if positive_value_exists(read_only):
                voter_guide_query = VoterGuidePossibility.objects.using('readonly').all()
            else:
                voter_guide_query = VoterGuidePossibility.objects.all()
            if positive_value_exists(order_by):
                voter_guide_query = voter_guide_query.order_by(order_by)
            if not positive_value_exists(show_prior_years):
                # Default to only showing this year
                now = datetime.now()
                voter_guide_query = voter_guide_query.filter(date_last_changed__year=now.year)
            if positive_value_exists(assigned_to_no_one):
                voter_guide_query = voter_guide_query.filter(
                    Q(assigned_to_voter_we_vote_id__isnull=True) |
                    Q(assigned_to_voter_we_vote_id=""))
            elif positive_value_exists(assigned_to_voter_we_vote_id):
                voter_guide_query = voter_guide_query.filter(
                    assigned_to_voter_we_vote_id__iexact=assigned_to_voter_we_vote_id)

            if positive_value_exists(search_string):
                try:
                    search_words = search_string.split()
                except Exception as e:
                    status += "SEARCH_STRING_COULD_NOT_BE_SPLIT "
                    search_words = []
                # possibility_number_list = POSSIBLE_ENDORSEMENT_NUMBER_LIST
                for one_word in search_words:
                    filters = []

                    new_filter = Q(ballot_items_raw__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(organization_name__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(organization_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(organization_twitter_handle__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(voter_guide_possibility_url__icontains=one_word)
                    filters.append(new_filter)

                    new_filter = Q(voter_who_submitted_we_vote_id__iexact=one_word)
                    filters.append(new_filter)

                    new_filter = Q(voter_who_submitted_name__icontains=one_word)
                    filters.append(new_filter)

                    try:
                        candidate_we_vote_id_query = VoterGuidePossibilityPosition.objects.all()
                        candidate_we_vote_id_query = candidate_we_vote_id_query.filter(
                            candidate_we_vote_id__iexact=one_word)
                        candidate_we_vote_id_query = candidate_we_vote_id_query.values(
                            'voter_guide_possibility_parent_id').distinct()
                        candidate_voter_guide_possibility_parent_id_dict = list(candidate_we_vote_id_query)
                        candidate_voter_guide_possibility_parent_id_list = []
                        for one_entry in candidate_voter_guide_possibility_parent_id_dict:
                            candidate_voter_guide_possibility_parent_id_list.append(
                                one_entry['voter_guide_possibility_parent_id'])

                        measure_we_vote_id_query = VoterGuidePossibilityPosition.objects.all()
                        measure_we_vote_id_query = measure_we_vote_id_query.filter(
                            measure_we_vote_id__iexact=one_word)
                        measure_we_vote_id_query = measure_we_vote_id_query.values(
                            'voter_guide_possibility_parent_id').distinct()
                        measure_voter_guide_possibility_parent_id_dict = list(measure_we_vote_id_query)
                        measure_voter_guide_possibility_parent_id_list = []
                        for one_entry in measure_voter_guide_possibility_parent_id_dict:
                            measure_voter_guide_possibility_parent_id_list.append(
                                one_entry['voter_guide_possibility_parent_id'])

                        ballot_item_name_query = VoterGuidePossibilityPosition.objects.all()
                        ballot_item_name_query = ballot_item_name_query.filter(ballot_item_name__icontains=one_word)
                        ballot_item_name_query = ballot_item_name_query.values(
                            'voter_guide_possibility_parent_id').distinct()
                        ballot_item_name_dict = list(ballot_item_name_query)
                        ballot_item_name_list = []
                        for one_entry in ballot_item_name_dict:
                            ballot_item_name_list.append(one_entry['voter_guide_possibility_parent_id'])

                        voter_guide_possibility_parent_id_list = []
                        voter_guide_possibility_parent_id_list_raw = \
                            candidate_voter_guide_possibility_parent_id_list + \
                            measure_voter_guide_possibility_parent_id_list + ballot_item_name_list
                        for one_entry in voter_guide_possibility_parent_id_list_raw:
                            if one_entry not in voter_guide_possibility_parent_id_list:
                                voter_guide_possibility_parent_id_list.append(one_entry)

                        if len(voter_guide_possibility_parent_id_list):
                            new_filter = Q(id__in=voter_guide_possibility_parent_id_list)
                            filters.append(new_filter)
                    except Exception as e:
                        status += "SET_OF_QUERIES_FAILURE: " + str(e) + ' '

                    # Add the first query
                    if len(filters):
                        final_filters = filters.pop()

                        # ...and "OR" the remaining items in the list
                        for item in filters:
                            final_filters |= item

                        voter_guide_query = voter_guide_query.filter(final_filters)
                # These are similar to the non-search query below
                if positive_value_exists(return_count_only):
                    if positive_value_exists(from_prior_election):
                        # This URL is specific to elections in prior election/year - filter_selected_from_prior_election
                        voter_guide_query = voter_guide_query.filter(from_prior_election=True)
                    elif positive_value_exists(cannot_find_endorsements):
                        # Cannot find endorsements - filter_selected_not_available_yet
                        voter_guide_query = voter_guide_query.filter(cannot_find_endorsements=True)
                    elif positive_value_exists(candidates_missing_from_we_vote):
                        # Candidates/Measures Missing - filter_selected_candidates_missing
                        voter_guide_query = voter_guide_query.filter(candidates_missing_from_we_vote=True)
                    elif positive_value_exists(capture_detailed_comments):
                        # Capture Comments - filter_selected_capture_detailed_comments
                        voter_guide_query = voter_guide_query.filter(capture_detailed_comments=True)
                    elif positive_value_exists(done_needs_verification):
                        # Capture Comments - filter_selected_done_needs_verification
                        voter_guide_query = voter_guide_query.filter(done_needs_verification=True)
                    elif positive_value_exists(done_verified):
                        # Capture Comments - filter_selected_done_verified
                        voter_guide_query = voter_guide_query.filter(done_verified=True)
                    elif positive_value_exists(ignore_this_source):
                        # Ignore - filter_selected_ignore
                        voter_guide_query = voter_guide_query.filter(ignore_this_source=True)
                    elif positive_value_exists(hide_from_active_review):
                        # Archive - filter_selected_archive
                        voter_guide_query = voter_guide_query.filter(hide_from_active_review=True)
                    else:
                        # To Review - filter_selected_to_review Only count items NOT categorized as one of the above
                        voter_guide_query = voter_guide_query.filter(candidates_missing_from_we_vote=False)
                        voter_guide_query = voter_guide_query.filter(cannot_find_endorsements=False)
                        voter_guide_query = voter_guide_query.filter(capture_detailed_comments=False)
                        voter_guide_query = voter_guide_query.filter(done_needs_verification=False)
                        voter_guide_query = voter_guide_query.filter(done_verified=False)
                        voter_guide_query = voter_guide_query.filter(hide_from_active_review=False)
                        voter_guide_query = voter_guide_query.filter(ignore_this_source=False)
                        voter_guide_query = voter_guide_query.filter(from_prior_election=False)

                voter_guide_possibility_list_count = voter_guide_query.count()
            else:
                voter_guide_query = voter_guide_query.filter(hide_from_active_review=hide_from_active_review)
                if not positive_value_exists(ignore_this_source):
                    # generally only look for entries we aren't ignoring
                    voter_guide_query = voter_guide_query.filter(ignore_this_source=False)
                if positive_value_exists(from_prior_election):
                    # Was a link from a prior election
                    voter_guide_query = voter_guide_query.filter(from_prior_election=True)
                elif positive_value_exists(cannot_find_endorsements):
                    # Cannot find endorsements, but they may be added to the website
                    voter_guide_query = voter_guide_query.filter(cannot_find_endorsements=True)
                elif positive_value_exists(candidates_missing_from_we_vote):
                    # Candidates/Measures Missing
                    voter_guide_query = voter_guide_query.filter(candidates_missing_from_we_vote=True)
                elif positive_value_exists(capture_detailed_comments):
                    # Capture Comments
                    voter_guide_query = voter_guide_query.filter(capture_detailed_comments=True)
                elif positive_value_exists(done_needs_verification):
                    # Done. Now needs to be verified - filter_selected_done_needs_verification
                    voter_guide_query = voter_guide_query.filter(done_needs_verification=True)
                elif positive_value_exists(done_verified):
                    # Done, and verified - filter_selected_done_verified
                    voter_guide_query = voter_guide_query.filter(done_verified=True)
                elif positive_value_exists(ignore_this_source):
                    # Ignore
                    voter_guide_query = voter_guide_query.filter(ignore_this_source=True)
                elif not positive_value_exists(hide_from_active_review):
                    # Remove items that need further work (and that are shown in other views) from main "Review" list
                    voter_guide_query = voter_guide_query.filter(candidates_missing_from_we_vote=False)
                    voter_guide_query = voter_guide_query.filter(cannot_find_endorsements=False)
                    voter_guide_query = voter_guide_query.filter(capture_detailed_comments=False)
                    voter_guide_query = voter_guide_query.filter(done_needs_verification=False)
                    voter_guide_query = voter_guide_query.filter(done_verified=False)
                    voter_guide_query = voter_guide_query.filter(from_prior_election=False)
                voter_guide_possibility_list_count = voter_guide_query.count()

            if positive_value_exists(return_count_only):
                pass
            else:
                if positive_value_exists(end_number):
                    voter_guide_possibility_list = voter_guide_query[start_number:end_number]
                else:
                    voter_guide_possibility_list = list(voter_guide_query)

                if len(voter_guide_possibility_list):
                    voter_guide_possibility_list_found = True
                    status += 'VOTER_GUIDE_FOUND '
                else:
                    status += 'NO_VOTER_GUIDES_FOUND '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_all_voter_guides_order_by: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                              success,
            'status':                               status,
            'assigned_to_voter_we_vote_id':         assigned_to_voter_we_vote_id,
            'voter_guide_possibility_list_found':   voter_guide_possibility_list_found,
            'voter_guide_possibility_list':         voter_guide_possibility_list,
            'voter_guide_possibility_list_count':   voter_guide_possibility_list_count,
        }
        return results

    @staticmethod
    def retrieve_voter_guide_possibility_position(voter_guide_possibility_position_id):
        status = ""
        voter_guide_possibility_position_id = convert_to_int(voter_guide_possibility_position_id)

        if not positive_value_exists(voter_guide_possibility_position_id):
            success = False
            status = "CANNOT_RETRIEVE_VOTER_GUIDE_POSSIBILITY_POSITION-MISSING_POSITION_ID "
            results = {
                'success': success,
                'status': status,
                'voter_guide_possibility_position': None,
                'voter_guide_possibility_position_found': False,
            }
            return results

        voter_guide_possibility_position = None
        voter_guide_possibility_position_found = False
        try:
            voter_guide_possibility_position = \
                VoterGuidePossibilityPosition.objects.get(id=voter_guide_possibility_position_id)
            voter_guide_possibility_position_found = True
            status += "VOTER_GUIDE_POSSIBILITY_POSITION_FOUND_WITH_ID "
            success = True
        except VoterGuidePossibilityPosition.DoesNotExist:
            status += "VOTER_GUIDE_POSSIBILITY_POSITION_NOT_FOUND_IN_DB "
            success = True
        except Exception as e:
            status += ", ERROR_RETRIEVING_VOTER_GUIDE_POSSIBILITY_POSITION: " + str(e)
            success = False

        results = {
            'success':                                  success,
            'status':                                   status,
            'voter_guide_possibility_position':         voter_guide_possibility_position,
            'voter_guide_possibility_position_found':   voter_guide_possibility_position_found,
        }
        return results

    @staticmethod
    def retrieve_voter_guide_possibility_position_list(voter_guide_possibility_id):
        voter_guide_possibility_list = []
        voter_guide_possibility_list_found = False
        try:
            voter_guide_query = VoterGuidePossibilityPosition.objects.all()
            voter_guide_query = voter_guide_query.order_by('possibility_position_number')
            voter_guide_query = voter_guide_query.filter(voter_guide_possibility_parent_id=voter_guide_possibility_id)
            voter_guide_possibility_list = list(voter_guide_query)

            if len(voter_guide_possibility_list):
                voter_guide_possibility_list_found = True
                status = 'VOTER_GUIDE_POSSIBILITY_POSITIONS_FOUND'
            else:
                status = 'NO_VOTER_GUIDE_POSSIBILITY_POSITIONS_FOUND'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'retrieve_voter_guide_possibility_position_list: Unable to retrieve from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                              success,
            'status':                               status,
            'voter_guide_possibility_position_list_found':   voter_guide_possibility_list_found,
            'voter_guide_possibility_position_list':         voter_guide_possibility_list,
        }
        return results

    @staticmethod
    def migrate_vote_guide_possibility(voter_guide_possibility):
        status = ""
        success = True
        entry_migrated = False

        voter_guide_possibility_manager = VoterGuidePossibilityManager()

        # Has this entry been migrated yet?
        if positive_value_exists(voter_guide_possibility.google_civic_election_id_200):
            if voter_guide_possibility.google_civic_election_id_200 == 555:
                # Already migrated
                results = {
                    'success': success,
                    'status': status,
                    'entry_migrated': entry_migrated,
                    'voter_guide_possibility': voter_guide_possibility,
                }
                return results

        # Get positions that might have been migrated
        voter_guide_possibility_position_list = []
        try:
            voter_guide_query = VoterGuidePossibilityPosition.objects.all()
            voter_guide_query = voter_guide_query.order_by('possibility_position_number')
            voter_guide_query = voter_guide_query.filter(voter_guide_possibility_parent_id=voter_guide_possibility.id)
            voter_guide_possibility_position_list = list(voter_guide_query)

            if len(voter_guide_possibility_position_list):
                status += 'VOTER_GUIDE_POSSIBILITY_POSITIONS_FOUND '
            else:
                status += 'NO_VOTER_GUIDE_POSSIBILITY_POSITIONS_FOUND '
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'migrate_vote_guide_possibility: Unable to retrieve from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if not success:
            results = {
                'success': success,
                'status': status,
                'entry_migrated': entry_migrated,
                'voter_guide_possibility': voter_guide_possibility,
            }
            return results

        position_json_list = []
        candidate_number_list = POSSIBLE_ENDORSEMENT_NUMBER_LIST

        number_index = 0
        for candidate_number in candidate_number_list:
            if number_index >= len(candidate_number_list):
                break
            if positive_value_exists(getattr(voter_guide_possibility,
                                             'candidate_name_' + candidate_number)) \
                    or positive_value_exists(getattr(voter_guide_possibility,
                                                     'candidate_we_vote_id_' + candidate_number)) \
                    or positive_value_exists(getattr(voter_guide_possibility,
                                                     'comment_about_candidate_' + candidate_number)):
                candidate_name = getattr(voter_guide_possibility, 'candidate_name_' + candidate_number)
                candidate_we_vote_id = getattr(voter_guide_possibility, 'candidate_we_vote_id_' + candidate_number)
                google_civic_election_id = getattr(voter_guide_possibility,
                                                   'google_civic_election_id_' + candidate_number)
                stance = getattr(voter_guide_possibility, 'stance_about_candidate_' + candidate_number)
                statement_text = getattr(voter_guide_possibility, 'comment_about_candidate_' + candidate_number)
                possibility_position_number = number_index + 1
                position_json = {
                    'ballot_item_name': candidate_name,
                    'candidate_we_vote_id': candidate_we_vote_id,
                    'google_civic_election_id': google_civic_election_id,
                    'position_stance': stance,
                    'possibility_position_number': possibility_position_number,
                    'statement_text': statement_text,
                }
                position_json_list.append(position_json)
            number_index += 1

        class LocalBreak(Exception):  # Also called BreakException elsewhere
            pass

        local_break = LocalBreak()

        modified_position_json_list = []
        if len(position_json_list):
            # Remove positions from position_json_list that have already been stored in VoterGuidePossibilityPosition
            for position_json in position_json_list:
                # Is there a VoterGuidePossibilityPosition entry that matches this position_json?
                position_json_found_in_voter_guide_possibility_position_list = False
                try:
                    for voter_guide_possibility_position in voter_guide_possibility_position_list:
                        if positive_value_exists(voter_guide_possibility_position.ballot_item_name):
                            if voter_guide_possibility_position.ballot_item_name == position_json['ballot_item_name']:
                                position_json_found_in_voter_guide_possibility_position_list = True
                                raise local_break  # Jump out of inner loop
                        if positive_value_exists(voter_guide_possibility_position.candidate_we_vote_id):
                            if voter_guide_possibility_position.candidate_we_vote_id \
                                    == position_json['candidate_we_vote_id']:
                                position_json_found_in_voter_guide_possibility_position_list = True
                                raise local_break  # Jump out of inner loop
                except LocalBreak:
                    continue

                if not position_json_found_in_voter_guide_possibility_position_list:
                    modified_position_json_list.append(position_json)

        # Reorder position index numbers
        reset_possibility_position_number = 0
        must_reset_position_json_position_numbers = False
        for voter_guide_possibility_position in voter_guide_possibility_position_list:
            reset_possibility_position_number += 1
            voter_guide_possibility_position.possibility_position_number = reset_possibility_position_number
            timezone = pytz.timezone("America/Los_Angeles")
            voter_guide_possibility_position.date_updated = timezone.localize(datetime.now())
            voter_guide_possibility_position.save()
            must_reset_position_json_position_numbers = True

        # Store
        for position_json in modified_position_json_list:
            if positive_value_exists(must_reset_position_json_position_numbers):
                # We need to reset the possibility_position_number values in modified_position_json_list
                reset_possibility_position_number += 1
                position_json['possibility_position_number'] = reset_possibility_position_number
            position_results = voter_guide_possibility_manager.update_or_create_voter_guide_possibility_position(
                voter_guide_possibility_id=voter_guide_possibility.id, updated_values=position_json)

        if success:
            voter_guide_possibility.google_civic_election_id_200 = 555
            voter_guide_possibility.save()
            entry_migrated = True

        results = {
            'success':                              success,
            'status':                               status,
            'entry_migrated':                       entry_migrated,
            'voter_guide_possibility':              voter_guide_possibility,
        }
        return results

    @staticmethod
    def number_of_ballot_items(voter_guide_possibility_id):
        """
        How many VoterGuidePossibilityPosition entries for this VoterGuidePossibility?
        :param voter_guide_possibility_id:
        :return:
        """
        if not positive_value_exists(voter_guide_possibility_id):
            return 0

        number_query = VoterGuidePossibilityPosition.objects.all()
        number_query = number_query.filter(voter_guide_possibility_parent_id=voter_guide_possibility_id)
        number_of_ballot_items_found_count = number_query.count()

        return number_of_ballot_items_found_count

    @staticmethod
    def number_of_candidates_in_database(voter_guide_possibility_id):
        """
        Out of all the VoterGuidePossibilityPosition entries, how many have been tied to candidates?
        :param voter_guide_possibility_id:
        :return:
        """
        if not positive_value_exists(voter_guide_possibility_id):
            return 0

        number_query = VoterGuidePossibilityPosition.objects.all()
        number_query = number_query.filter(voter_guide_possibility_parent_id=voter_guide_possibility_id)
        # Remove rows without candidate_we_vote_id
        number_query = number_query.exclude(Q(candidate_we_vote_id__isnull=True) | Q(candidate_we_vote_id=""))
        number_of_candidates_in_database_count = number_query.count()

        return number_of_candidates_in_database_count

    @staticmethod
    def number_of_measures_in_database(voter_guide_possibility_id):
        """
        Out of all the VoterGuidePossibilityPosition entries, how many have been tied to measures?
        :param voter_guide_possibility_id:
        :return:
        """
        if not positive_value_exists(voter_guide_possibility_id):
            return 0

        number_query = VoterGuidePossibilityPosition.objects.all()
        number_query = number_query.filter(voter_guide_possibility_parent_id=voter_guide_possibility_id)
        # Remove rows without measure_we_vote_id
        number_query = number_query.exclude(Q(measure_we_vote_id__isnull=True) | Q(measure_we_vote_id=""))
        number_of_measures_in_database_count = number_query.count()

        return number_of_measures_in_database_count

    @staticmethod
    def number_of_possible_organizations_in_database(voter_guide_possibility_id):
        """
        Out of all the VoterGuidePossibilityPosition entries, how many have been tied to candidates?
        :param voter_guide_possibility_id:
        :return:
        """
        if not positive_value_exists(voter_guide_possibility_id):
            return 0

        number_query = VoterGuidePossibilityPosition.objects.all()
        number_query = number_query.filter(voter_guide_possibility_parent_id=voter_guide_possibility_id)
        # Remove rows without candidate_we_vote_id
        number_query = number_query.exclude(Q(organization_we_vote_id__isnull=True) | Q(organization_we_vote_id=""))
        number_of_possible_organizations_in_database_count = number_query.count()

        return number_of_possible_organizations_in_database_count

    @staticmethod
    def number_of_ballot_items_not_matched(voter_guide_possibility_id):
        """
        Out of all the VoterGuidePossibilityPosition entries, how many have not been matched to ballot items?
        :param voter_guide_possibility_id:
        :return:
        """
        if not positive_value_exists(voter_guide_possibility_id):
            return 0

        number_query = VoterGuidePossibilityPosition.objects.all()
        number_query = number_query.filter(voter_guide_possibility_parent_id=voter_guide_possibility_id)
        # Remove rows without candidate_we_vote_id
        number_query = number_query.exclude(Q(candidate_we_vote_id__isnull=True) | Q(candidate_we_vote_id=""))
        # Remove rows without measure_we_vote_id
        number_query = number_query.exclude(Q(measure_we_vote_id__isnull=True) | Q(measure_we_vote_id=""))
        number_of_ballot_items_not_matched_count = number_query.count()

        return number_of_ballot_items_not_matched_count

    def positions_ready_to_save_as_batch(self, voter_guide_possibility):
        ballot_item_in_batch_exists_in_database = False
        organization_found = False
        candidate_found = False
        if positive_value_exists(voter_guide_possibility.organization_we_vote_id):
            organization_found = True

            if positive_value_exists(self.number_of_candidates_in_database(voter_guide_possibility.id)):
                ballot_item_in_batch_exists_in_database = True
            elif positive_value_exists(self.number_of_measures_in_database(voter_guide_possibility.id)):
                ballot_item_in_batch_exists_in_database = True
        elif positive_value_exists(voter_guide_possibility.candidate_we_vote_id):
            candidate_found = True

            if positive_value_exists(self.number_of_possible_organizations_in_database(voter_guide_possibility.id)):
                ballot_item_in_batch_exists_in_database = True

        if positive_value_exists(voter_guide_possibility.voter_guide_possibility_url) \
                and ballot_item_in_batch_exists_in_database and organization_found or candidate_found:
            return True

        return False

    def delete_voter_guide_possibility(self, voter_guide_possibility_id):
        status = ""
        success = True

        voter_guide_possibility_id = convert_to_int(voter_guide_possibility_id)
        voter_guide_possibility_deleted = False

        try:
            if positive_value_exists(voter_guide_possibility_id):
                queryset = VoterGuidePossibilityPosition.objects.all()
                queryset = queryset.filter(voter_guide_possibility_parent_id=voter_guide_possibility_id)
                number_deleted = queryset.delete()
                status += str(number_deleted) + "VoterGuidePossibilityPosition_DELETED "

        except Exception as e:
            handle_exception(e, logger=logger)
            success = False

        try:
            if success and positive_value_exists(voter_guide_possibility_id):
                results = self.retrieve_voter_guide_possibility(voter_guide_possibility_id)
                if results['voter_guide_possibility_found']:
                    voter_guide_possibility = results['voter_guide_possibility']
                    voter_guide_possibility_id = voter_guide_possibility.id
                    voter_guide_possibility.delete()
                    status += "VOTER_GUIDE_POSSIBILITY_DELETED "
                    voter_guide_possibility_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger)
            success = False

        results = {
            'success':                          success,
            'status':                           status,
            'voter_guide_possibility_deleted':  voter_guide_possibility_deleted,
            'voter_guide_possibility_id':       voter_guide_possibility_id,
        }
        return results


class VoterGuidePossibility(models.Model):
    """
    We ask volunteers to enter a list of urls that might have voter guides. This table stores the URLs and partial
    information, prior to a full-fledged voter guide being saved in the VoterGuide table.
    """
    # We are relying on built-in Python id field

    # Where a volunteer thinks there is a voter guide
    voter_guide_possibility_url = models.TextField(
        verbose_name='url of possible voter guide', blank=True, null=True)

    voter_guide_possibility_pdf_url = models.TextField(
        verbose_name='url of possible voter guide which is a PDF', blank=True, null=True)

    # The unique id of the organization making the endorsements, if/when we know it
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote id", max_length=255, null=True, blank=True, unique=False)

    candidate_name = models.CharField(
        verbose_name="candidate name", max_length=255, null=True, blank=True, unique=False)
    candidate_twitter_handle = models.CharField(
        verbose_name="candidate twitter handle", max_length=255, null=True, blank=True, unique=False)
    # The unique id of the candidate these endorsements are about, if/when we know it
    candidate_we_vote_id = models.CharField(
        verbose_name="candidate we vote id", max_length=255, null=True, blank=True, unique=False)

    voter_who_submitted_name = models.CharField(
        verbose_name="voter name who submitted this", max_length=255, null=True, blank=True, unique=False)
    voter_who_submitted_we_vote_id = models.CharField(
        verbose_name="voter we vote id who submitted this", max_length=255, null=True, blank=True, unique=False)

    verified_by_name = models.CharField(max_length=255, null=True, blank=True, unique=False)
    verified_by_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)

    # Political data manager responsible for processing this voter guide possibility
    assigned_to_name = models.CharField(max_length=255, null=True, blank=True, unique=False)
    assigned_to_voter_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)

    state_code = models.CharField(verbose_name="state the voter guide is related to", max_length=2, null=True)

    # Mapped directly from organization.organization_type
    voter_guide_owner_type = models.CharField(
        verbose_name="is owner org, public figure, or voter?", max_length=2, choices=ORGANIZATION_TYPE_CHOICES,
        default=UNKNOWN)
    voter_guide_possibility_type = models.CharField(
        max_length=7, choices=VOTER_GUIDE_POSSIBILITY_TYPES, default=UNKNOWN_TYPE)

    organization_name = models.CharField(
        verbose_name="organization name", max_length=255, null=True, blank=True, unique=False)
    organization_twitter_handle = models.CharField(
        verbose_name="organization twitter handle", max_length=255, null=True, blank=True, unique=False)
    organization_twitter_followers_count = models.PositiveIntegerField(null=False, blank=True, default=0)
    # These are the candidates or measures on the voter guide (comma separated, or on own lines)
    ballot_items_raw = models.TextField(null=True, blank=True,)

    # Notes coming from the person submitting this voter guide
    contributor_comments = models.TextField(null=True, blank=True, default=None)
    contributor_email = models.TextField(null=True, blank=True, default=None)

    # What election was used as the target for finding endorsements?
    target_google_civic_election_id = models.PositiveIntegerField(null=True)

    # Data manager sees candidates or measures on voter guide that are not in the We Vote database
    candidates_missing_from_we_vote = models.BooleanField(default=False)

    # Data manager cannot find upcoming endorsements (may not be posted yet)
    cannot_find_endorsements = models.BooleanField(default=False)

    # Data manager will need to put more work into this in order to capture all the details
    capture_detailed_comments = models.BooleanField(default=False)

    # We have extracted all the data that we can from this Endorsement Website,
    # and it is ready for review by another teammate.
    done_needs_verification = models.BooleanField(default=False)

    # Another teammate reviewed the captured data for accuracy, and approved all the stored data as valid.
    done_verified = models.BooleanField(default=False)

    # Data manager will need to put more work into this in order to capture all the details
    from_prior_election = models.BooleanField(default=False)

    # While processing and reviewing this organization's endorsements, leave out positions already stored
    ignore_stored_positions = models.BooleanField(default=False)

    # This website is not a good source for future endorsements
    ignore_this_source = models.BooleanField(default=False)

    # Has this VoterGuidePossibility been used to create a batch in the import_export_batch system?
    hide_from_active_review = models.BooleanField(default=False)
    batch_header_id = models.PositiveIntegerField(null=True)

    # For internal notes regarding gathering data
    internal_notes = models.TextField(null=True, blank=True, default=None)

    date_created = models.DateTimeField(null=True, auto_now_add=True)
    # The date of the last change to this voter_guide_possibility
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)  # last_updated

    def __unicode__(self):
        return self.date_last_changed

    class Meta:
        ordering = ('date_last_changed',)

    objects = VoterGuideManager()

    def organization(self):
        if not positive_value_exists(self.organization_we_vote_id):
            return

        try:
            organization = Organization.objects.using('readonly').get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("voter_guide_possibility.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("voter_guide_possibility.organization did not find")
            return
        return organization


class VoterGuidePossibilityPosition(models.Model):
    """
    This table stores the support/oppose/info only positions from organizations, prior to a
    full-fledged voter guide being saved in the VoterGuide table.
    """
    # We are relying on built-in Python id field

    # What is the parent VoterGuidePossibility?
    objects = None
    voter_guide_possibility_parent_id = models.PositiveIntegerField(null=True, db_index=True)

    # 001 - 999
    possibility_position_number = models.PositiveIntegerField(null=True, db_index=True)
    ballot_item_name = models.CharField(max_length=255, null=True, unique=False)
    ballot_item_state_code = models.CharField(max_length=2, null=True, unique=False)
    candidate_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    candidate_twitter_handle = models.CharField(max_length=255, null=True, unique=False)
    organization_name = models.CharField(max_length=255, null=True, unique=False)
    organization_twitter_handle = models.CharField(max_length=255, null=True, unique=False)
    organization_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    position_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    measure_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    statement_text = models.TextField(null=True, blank=True)
    google_civic_election_id = models.PositiveIntegerField(null=True)
    position_stance = models.CharField(max_length=15, choices=POSITION_CHOICES, default=SUPPORT)
    # A link to any location with more information about this position
    more_info_url = models.TextField(verbose_name='url with more info about this position', null=True)
    # We don't want to work with this possibility anymore
    possibility_should_be_ignored = models.BooleanField(default=False,
                                                        verbose_name='Soft delete. Stop analyzing this entry.')
    # Delete existing PositionEntered from database
    position_should_be_removed = models.BooleanField(default=False,
                                                     verbose_name='Delete saved position from PositionEntered.')
    date_created = models.DateTimeField(verbose_name='date created', null=True, auto_now_add=True)
    date_updated = models.DateTimeField(null=True)


class VoterGuidesGenerated(models.Model):
    google_civic_election_id = models.PositiveIntegerField(null=True, db_index=True)
    date_last_changed = models.DateTimeField(null=True, auto_now=True)
    number_of_voter_guides = models.PositiveIntegerField(null=True)
