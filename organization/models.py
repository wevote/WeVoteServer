# organization/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

import wevote_functions.admin
from exception.models import handle_exception, \
    handle_record_found_more_than_one_exception, handle_record_not_saved_exception, handle_record_not_found_exception
from import_export_facebook.models import FacebookManager
from twitter.functions import retrieve_twitter_user_info
from twitter.models import TwitterLinkToOrganization, TwitterLinkToVoter, TwitterUserManager
from voter.models import VoterManager
from wevote_functions.functions import convert_to_int, extract_twitter_handle_from_text_string, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_org_integer, fetch_site_unique_id_prefix

# Also see a copy of these in wevote_function/functions.py
CORPORATION = 'C'
GROUP = 'G'  # Group of people (not an individual), but org status unknown
INDIVIDUAL = 'I'  # One person
NONPROFIT = 'NP'
NONPROFIT_501C3 = 'C3'
NONPROFIT_501C4 = 'C4'
NEWS_ORGANIZATION = 'NW'
ORGANIZATION = 'O'  # Deprecated
POLITICAL_ACTION_COMMITTEE = 'P'
PUBLIC_FIGURE = 'PF'
UNKNOWN = 'U'
VOTER = 'V'
ORGANIZATION_TYPE_CHOICES = (
    (CORPORATION, 'Corporation'),
    (GROUP, 'Group'),
    (INDIVIDUAL, 'Individual'),
    (NEWS_ORGANIZATION, 'News Corporation'),
    (NONPROFIT, 'Nonprofit'),
    (NONPROFIT_501C3, 'Nonprofit 501c3'),
    (NONPROFIT_501C4, 'Nonprofit 501c4'),
    (POLITICAL_ACTION_COMMITTEE, 'Political Action Committee'),
    (PUBLIC_FIGURE, 'Public Figure'),
    (UNKNOWN, 'Unknown Type'),
    (ORGANIZATION, 'Group - Organization'),  # Deprecated
)

ORGANIZATION_TYPE_MAP = {
    CORPORATION:                'Corporation',
    GROUP:                      'Group',
    INDIVIDUAL:                 'Individual',
    NEWS_ORGANIZATION:          'News Organization',
    NONPROFIT:                  'Nonprofit (c?)',
    NONPROFIT_501C3:            'Nonprofit 501c3',
    NONPROFIT_501C4:            'Nonprofit 501c4',
    POLITICAL_ACTION_COMMITTEE: 'Political Action Committee',
    PUBLIC_FIGURE:              'Public Figure',
    UNKNOWN:                    'Unknown Type',
}

alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', message='Only alphanumeric characters are allowed.')

logger = wevote_functions.admin.get_logger(__name__)


class OrganizationLinkToHashtag():
    def __unicode__(self):
        return "OrganizationLinkToHashtag"
    
    organization_we_vote_id = models.CharField(verbose_name="we vote permanent id", max_length=255, unique=True)
    hashtag_text = models.CharField(verbose_name="hashtag text", max_length=255, unique=False)
    tweet_id = models.BigIntegerField(verbose_name="tweet id", unique=True)
    published_datetime = models.DateTimeField(verbose_name="published datetime")
    # organization_we_vote_id
    # hashtag_text
    # tweet_id
    # published_datetime


class OrganizationLinkToWordOrPhrase():
    def __unicode__(self):
        return "OrganizationLinkToWordOrPhrase"

    organization_we_vote_id = models.CharField(verbose_name="we vote permanent id", max_length=255, unique=True)
    word_or_phrase_text = models.CharField(verbose_name="text of a word or phrase", max_length=255, unique=False)
    tweet_id = models.BigIntegerField(verbose_name="tweet id",unique=True)
    published_datetime = models.DateTimeField(verbose_name="published datetime")
    # organization_we_vote_id
    # word_or_phrase
    # tweet_id
    # published_datetime


class OrganizationManager(models.Manager):
    """
    A class for working with the Organization model
    """
    # Create organizationLinkToHashtag
    def create_organization_simple(self, organization_name, organization_website, organization_twitter_handle,
                                   organization_email='', organization_facebook='', organization_image='',
                                   organization_type=''):
        try:
            if organization_twitter_handle is False or organization_twitter_handle == 'False':
                organization_twitter_handle = ""
            organization = self.create(organization_name=organization_name,
                                       organization_website=organization_website,
                                       organization_twitter_handle=organization_twitter_handle,
                                       organization_email=organization_email,
                                       organization_facebook=organization_facebook,
                                       organization_image=organization_image,
                                       organization_type=organization_type)
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            organization = Organization
        return organization

    def create_organization(self, organization_name, organization_website='', organization_twitter_handle='',
                            organization_email='', organization_facebook='', organization_image='', twitter_id='',
                            organization_type=''):
        try:
            if not positive_value_exists(organization_name):
                organization_name = ""
            if organization_twitter_handle is False or organization_twitter_handle == 'False':
                organization_twitter_handle = ""
            # External to this function, we should be setting up TwitterLinkToOrganization entry tying the
            #  organization_twitter_handle to the new organization's we_vote_id (assuming a link to another
            #  organization doesn't already exist.

            twitter_user = None
            if positive_value_exists(twitter_id):
                twitter_user = self.get_twitter_user(twitter_id)
            if twitter_user is not None:
                # twitter_user is the authoritative source for this data
                organization_twitter_handle = twitter_user.twitter_handle
                twitter_user_id = twitter_user.twitter_id
                twitter_name = twitter_user.twitter_name
                twitter_location = twitter_user.twitter_location
                twitter_followers_count = twitter_user.twitter_followers_count if \
                    positive_value_exists(twitter_user.twitter_followers_count) else 0
                twitter_profile_image_url_https = twitter_user.twitter_profile_background_image_url_https
                twitter_profile_background_image_url_https = twitter_user.twitter_profile_background_image_url_https
                twitter_profile_banner_url_https = twitter_user.twitter_profile_banner_url_https
                twitter_description = twitter_user.twitter_description
                we_vote_hosted_profile_image_url_large = twitter_user.we_vote_hosted_profile_image_url_large
                we_vote_hosted_profile_image_url_medium = twitter_user.we_vote_hosted_profile_image_url_medium
                we_vote_hosted_profile_image_url_tiny = twitter_user.we_vote_hosted_profile_image_url_tiny
                organization = Organization.create(
                    organization_name=organization_name,
                    organization_website=organization_website,
                    organization_twitter_handle=organization_twitter_handle,
                    organization_email=organization_email,
                    organization_facebook=organization_facebook,
                    organization_image=organization_image,
                    organization_type=organization_type,
                    twitter_user_id=twitter_user_id,
                    twitter_name=twitter_name,
                    twitter_location=twitter_location,
                    twitter_followers_count=twitter_followers_count,
                    twitter_profile_image_url_https=twitter_profile_image_url_https,
                    twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                    twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                    twitter_description=twitter_description,
                    we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                    we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
            else:
                organization = Organization.create(
                    organization_name=organization_name,
                    organization_website=organization_website,
                    organization_twitter_handle=organization_twitter_handle,
                    organization_email=organization_email,
                    organization_facebook=organization_facebook,
                    organization_image=organization_image,
                    organization_type=organization_type)
            organization.save()  # We do this so the we_vote_id is created
            status = "CREATE_ORGANIZATION_SUCCESSFUL"
            success = True
            organization_created = True
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            organization = Organization
            status = "CREATE_ORGANIZATION_FAILED"
            success = False
            organization_created = False
        results = {
            'success':              success,
            'status':               status,
            'organization':         organization,
            'organization_created': organization_created,
        }
        return results

    @staticmethod
    def get_twitter_user(twitter_id):
        twitter_user_manager = TwitterUserManager()

        twitter_user_results = twitter_user_manager.retrieve_twitter_user(twitter_id)
        if twitter_user_results['twitter_user_found']:
            return twitter_user_results['twitter_user']
        return None

    def duplicate_organization_destination_twitter(self, organization):
        """
        Starting with an existing organization, create a duplicate version with different we_vote_id
        :param organization:
        :return:
        """
        success = False
        status = ""
        organization_duplicated = False

        try:
            organization.id = None  # Remove the primary key so it is forced to save a new entry
            organization.pk = None
            organization.facebook_email = ""
            organization.fb_username = ""
            organization.we_vote_id = None  # Clear out existing we_vote_id
            organization.generate_new_we_vote_id()
            organization.save()  # We do this so the we_vote_id is created
            status += "DUPLICATE_ORGANIZATION_SUCCESSFUL"
            success = True
            organization_duplicated = True
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            organization = Organization
            status += "DUPLICATE_ORGANIZATION_FAILED"
        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
            'organization_duplicated':  organization_duplicated,
        }
        return results

    def retrieve_organization_from_id(self, organization_id):
        return self.retrieve_organization(organization_id)

    def retrieve_organization_from_we_vote_id(self, organization_we_vote_id):
        return self.retrieve_organization(0, organization_we_vote_id)

    def retrieve_organization_from_vote_smart_id(self, vote_smart_id):
        return self.retrieve_organization(0, '', vote_smart_id)

    def retrieve_organization_from_twitter_handle(self, twitter_handle):
        organization_id = 0
        organization_we_vote_id = ""

        twitter_user_manager = TwitterUserManager()
        twitter_retrieve_results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
            twitter_handle)
        if twitter_retrieve_results['twitter_link_to_organization_found']:
            twitter_link_to_organization = twitter_retrieve_results['twitter_link_to_organization']
            organization_we_vote_id = twitter_link_to_organization.organization_we_vote_id

        return self.retrieve_organization(organization_id, organization_we_vote_id)

    def retrieve_organization_from_twitter_user_id(self, twitter_user_id):
        organization_we_vote_id = ''

        twitter_user_manager = TwitterUserManager()
        twitter_retrieve_results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
            twitter_user_id)
        if twitter_retrieve_results['twitter_link_to_organization_found']:
            twitter_link_to_organization = twitter_retrieve_results['twitter_link_to_organization']
            organization_we_vote_id = twitter_link_to_organization.organization_we_vote_id

        organization_id = 0
        return self.retrieve_organization(organization_id, organization_we_vote_id)

    def retrieve_organization_from_twitter_user_id_old(self, twitter_user_id):
        """
        We will phase this out
        :param twitter_user_id:
        :return:
        """
        return self.retrieve_organization(0, '', '', twitter_user_id)

    def retrieve_organization_from_facebook_id(self, facebook_id):
        status = ""
        facebook_manager = FacebookManager()
        results = facebook_manager.retrieve_facebook_link_to_voter_from_facebook_id(facebook_id)
        if results['facebook_link_to_voter_found']:
            facebook_link_to_voter = results['facebook_link_to_voter']
            if positive_value_exists(facebook_link_to_voter.voter_we_vote_id):
                voter_manager = VoterManager()
                voter_results = voter_manager.retrieve_voter_by_we_vote_id(facebook_link_to_voter.voter_we_vote_id)
                if voter_results['voter_found']:
                    voter = voter_results['voter']
                    if positive_value_exists(voter.linked_organization_we_vote_id):
                        return self.retrieve_organization_from_we_vote_id(voter.linked_organization_we_vote_id)
                    else:
                        status += "RETRIEVE_ORGANIZATION_FROM_FACEBOOK_ID-MISSING_LINKED_ORGANIZATION_WE_VOTE_ID"
                else:
                    status += "RETRIEVE_ORGANIZATION_FROM_FACEBOOK_ID-MISSING_VOTER"
            else:
                status += "RETRIEVE_ORGANIZATION_FROM_FACEBOOK_ID-MISSING_LINK_TO_VOTER_WE_VOTE_ID"
        else:
            status += "RETRIEVE_ORGANIZATION_FROM_FACEBOOK_ID-MISSING_FACEBOOK_LINK_TO_VOTER"

        # If here, we failed to find it
        results = {
            'success':                      False,
            'status':                       status,
            'organization_found':           False,
            'organization_id':              0,
            'we_vote_id':                   "",
            'organization':                 Organization(),
            'error_result':                 {},
            'DoesNotExist':                 False,
            'MultipleObjectsReturned':      False,
        }
        return results

    def retrieve_organization(self, organization_id, we_vote_id=None, vote_smart_id=None, twitter_user_id=None):
        """
        Get an organization, based the passed in parameters
        :param organization_id:
        :param we_vote_id:
        :param vote_smart_id:
        :param twitter_user_id:
        :return: the matching organization object
        """
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        organization_on_stage = Organization()
        organization_on_stage_id = 0
        status = "ERROR_ENTERING_RETRIEVE_ORGANIZATION"
        try:
            if positive_value_exists(organization_id):
                status = "ERROR_RETRIEVING_ORGANIZATION_WITH_ID"
                organization_on_stage = Organization.objects.get(id=organization_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_ID"
            elif positive_value_exists(we_vote_id):
                status = "ERROR_RETRIEVING_ORGANIZATION_WITH_WE_VOTE_ID"
                organization_on_stage = Organization.objects.get(we_vote_id=we_vote_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_WE_VOTE_ID"
            elif positive_value_exists(vote_smart_id):
                status = "ERROR_RETRIEVING_ORGANIZATION_WITH_VOTE_SMART_ID"
                organization_on_stage = Organization.objects.get(vote_smart_id=vote_smart_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_VOTE_SMART_ID"
            elif positive_value_exists(twitter_user_id):
                status = "ERROR_RETRIEVING_ORGANIZATION_WITH_TWITTER_ID"
                organization_on_stage = Organization.objects.get(twitter_user_id=twitter_user_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_TWITTER_ID"
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status = "ERROR_MORE_THAN_ONE_ORGANIZATION_FOUND"
            # logger.warning("Organization.MultipleObjectsReturned")
        except Organization.DoesNotExist as e:
            status += ", ORGANIZATION_NOT_FOUND"
            handle_exception(e, logger=logger, exception_message=status)
            error_result = True
            exception_does_not_exist = True
            # logger.warning("Organization.DoesNotExist")

        organization_on_stage_found = True if organization_on_stage_id > 0 else False
        results = {
            'success':                      True if organization_on_stage_found else False,
            'status':                       status,
            'organization_found':           organization_on_stage_found,
            'organization_id':
                organization_on_stage.id if organization_on_stage.id else organization_on_stage_id,
            'we_vote_id':
                organization_on_stage.we_vote_id if organization_on_stage.we_vote_id else we_vote_id,
            'organization':                 organization_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def fetch_organization_id(self, we_vote_id):
        organization_id = 0
        if positive_value_exists(we_vote_id):
            organization_manager = OrganizationManager()
            results = organization_manager.retrieve_organization(organization_id, we_vote_id)
            if results['success']:
                return results['organization_id']
        return 0

    def fetch_twitter_id_from_organization_we_vote_id(self, organization_we_vote_id):
        if positive_value_exists(organization_we_vote_id):
            twitter_user_manager = TwitterUserManager()
            organization_twitter_id = twitter_user_manager.fetch_twitter_id_from_organization_we_vote_id(
                organization_we_vote_id)
        else:
            organization_twitter_id = 0

        return organization_twitter_id

    def fetch_twitter_handle_from_organization_we_vote_id(self, organization_we_vote_id):
        if positive_value_exists(organization_we_vote_id):
            twitter_user_manager = TwitterUserManager()
            organization_twitter_handle = twitter_user_manager.fetch_twitter_handle_from_organization_we_vote_id(
                organization_we_vote_id)
        else:
            organization_twitter_handle = ''

        return organization_twitter_handle

    def fetch_we_vote_id_from_local_id(self, organization_id):
        if positive_value_exists(organization_id):
            results = self.retrieve_organization(organization_id)
            if results['organization_found']:
                organization = results['organization']
                return organization.we_vote_id
            else:
                return ''
        else:
            return ''

    def organization_name_needs_repair(self, organization):
        """
        See also position_speaker_name_needs_repair
        :param organization:
        :return:
        """
        if not hasattr(organization, 'organization_name'):
            return False
        if organization.organization_name.startswith("Voter-") \
                or organization.organization_name.startswith("null") \
                or organization.organization_name is "" \
                or organization.organization_name.startswith("wv"):
            return True
        return False

    def repair_missing_linked_organization_we_vote_id(self, voter):
        """
        Take in a voter that is missing a linked_organization_we_vote_id (or has a we_vote_id for a missing organization
        entry), and repair the link.
        :param voter:
        :return:
        """
        status = ""
        success = False
        voter_repaired = False
        linked_organization_we_vote_id = ""
        twitter_link_to_voter = TwitterLinkToVoter()
        twitter_link_to_voter_found = False
        twitter_link_to_voter_twitter_id = 0
        create_twitter_link_to_organization = False
        repair_twitter_link_to_organization = False
        twitter_link_to_organization = TwitterLinkToOrganization()
        twitter_link_to_organization_found = False
        twitter_organization_found = False
        create_new_organization = False
        organization_manager = OrganizationManager()
        twitter_user_manager = TwitterUserManager()
        voter_manager = VoterManager()

        # Gather what we know about TwitterLinkToVoter
        twitter_id = 0
        twitter_link_to_voter_results = twitter_user_manager.retrieve_twitter_link_to_voter(
            twitter_id, voter.we_vote_id)
        if twitter_link_to_voter_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_link_to_voter_results['twitter_link_to_voter']
            twitter_link_to_voter_twitter_id = twitter_link_to_voter.twitter_id
            twitter_link_to_voter_found = True
            twitter_link_to_organization_results = \
                twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
                    twitter_link_to_voter_twitter_id)
            if twitter_link_to_organization_results['twitter_link_to_organization_found']:
                twitter_link_to_organization = twitter_link_to_organization_results['twitter_link_to_organization']
                twitter_link_to_organization_found = True
                twitter_organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                    twitter_link_to_organization.organization_we_vote_id)
                if twitter_organization_results['organization_found']:
                    # This is the simplest case of the linked_organization_we_vote_id not stored in the voter table
                    twitter_organization_found = True
                    existing_linked_organization = twitter_organization_results['organization']
                    linked_organization_we_vote_id = existing_linked_organization.we_vote_id
            else:
                status += "NO_LINKED_ORGANIZATION_WE_VOTE_ID_FOUND "

        if positive_value_exists(voter.linked_organization_we_vote_id):
            # If here check to see if an organization exists with the value in linked_organization_we_vote_id
            organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                voter.linked_organization_we_vote_id)
            if organization_results['organization_found']:
                create_new_organization = False
                # If here, we found organization that matches the value stored in voter.linked_organization_we_vote_id
                linked_organization_we_vote_id = voter.linked_organization_we_vote_id
                if positive_value_exists(twitter_link_to_voter_twitter_id):
                    # If this voter is linked to a Twitter account, we want to make sure there is a
                    # TwitterLinkToOrganization as well
                    twitter_link_to_organization_results = \
                        twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
                            twitter_link_to_voter_twitter_id)
                    if twitter_link_to_organization_results['twitter_link_to_organization_found']:
                        twitter_link_to_organization = twitter_link_to_organization_results[
                            'twitter_link_to_organization']
                    else:
                        create_twitter_link_to_organization = True
            else:
                status += "NO_LINKED_ORGANIZATION_FOUND "
                create_new_organization = True
                if positive_value_exists(twitter_link_to_voter_twitter_id):
                    create_twitter_link_to_organization = True
        else:
            # If here, linked_organization_we_vote_id is not stored in the voter record

            # Is there another with linked_organization_we_vote_id matching?
            if positive_value_exists(linked_organization_we_vote_id):
                # If here, we have found the organization linked to the voter's twitter_id.
                # Check to make sure another voter isn't using linked_organization_we_vote_id (which
                # would prevent this voter account from claiming that twitter org with linked_organization_we_vote_id
                # If found, we want to forcibly move that organization to this voter
                # Search for another voter that has voter.linked_organization_we_vote_id
                voter_results = voter_manager.retrieve_voter_by_organization_we_vote_id(linked_organization_we_vote_id)
                if voter_results['voter_found']:
                    voter_with_linked_organization_we_vote_id = voter_results['voter']
                    if voter.we_vote_id != voter_with_linked_organization_we_vote_id.we_vote_id:
                        try:
                            voter_with_linked_organization_we_vote_id.linked_organization_we_vote_id = None
                            voter_with_linked_organization_we_vote_id.save()
                            status += "REPAIR_MISSING_LINKED_ORG-REMOVED_LINKED_ORGANIZATION_WE_VOTE_ID "
                        except Exception as e:
                            status += "REPAIR_MISSING_LINKED_ORG-COULD_NOT_REMOVE_LINKED_ORGANIZATION_WE_VOTE_ID "

            # If this voter is linked to a Twitter id, see if there is also an org linked to the same Twitter id
            #  so we can use that information to find an existing organization we should link to this voter
            if twitter_organization_found:
                # If here, there was a complete chain from TwitterLinkToVoter -> TwitterLinkToOrganization
                create_new_organization = False
                repair_twitter_link_to_organization = False
                create_twitter_link_to_organization = False
            elif twitter_link_to_organization_found:
                # If here, we know that a twitter_link_to_organization was found, but the organization wasn't
                create_new_organization = True
                repair_twitter_link_to_organization = True
                create_twitter_link_to_organization = False
            elif twitter_link_to_voter_found:
                if positive_value_exists(twitter_link_to_voter_twitter_id):
                    # If here, we know the voter is linked to a twitter account, but NOT a twitter_link_to_organization
                    # There could be an organization out there that informally has Twitter info associated with it
                    create_new_organization = True
                    repair_twitter_link_to_organization = False
                    create_twitter_link_to_organization = True
                else:
                    # If here, the twitter_link_to_voter entry is damaged and should be removed
                    try:
                        twitter_link_to_voter.delete()
                        status += "REPAIR_MISSING_LINKED_ORG-TWITTER_LINK_TO_VOTER_DELETED "
                        create_new_organization = True
                        repair_twitter_link_to_organization = False
                        create_twitter_link_to_organization = True
                    except Exception as e:
                        status += "REPAIR_MISSING_LINKED_ORG-TWITTER_LINK_TO_VOTER_COULD_NOT_DELETE "
            else:
                status += "NO_TWITTER_LINKED_ORGANIZATION_FOUND "
                create_new_organization = True

        if create_new_organization:
            # If here, then we know that there isn't a pre-existing organization related to this voter
            # Create new organization
            organization_name = voter.get_full_name()
            organization_website = ""
            organization_twitter_handle = ""
            organization_twitter_id = ""
            organization_email = ""
            organization_facebook = ""
            organization_image = voter.voter_photo_url()
            organization_type = INDIVIDUAL
            organization_manager = OrganizationManager()
            create_results = organization_manager.create_organization(
                organization_name, organization_website, organization_twitter_handle,
                organization_email, organization_facebook, organization_image, organization_twitter_id,
                organization_type)
            if create_results['organization_created']:
                # Add value to twitter_owner_voter.linked_organization_we_vote_id when done.
                organization = create_results['organization']
                linked_organization_we_vote_id = organization.we_vote_id

        if positive_value_exists(linked_organization_we_vote_id):
            if repair_twitter_link_to_organization:
                try:
                    twitter_link_to_organization.twitter_id = twitter_link_to_voter_twitter_id
                    twitter_link_to_organization.organization_we_vote_id = linked_organization_we_vote_id
                    twitter_link_to_organization.save()
                    status += "REPAIRED_TWITTER_LINK_TO_ORGANIZATION "
                except Exception as e:
                    status += "UNABLE_TO_REPAIR_TWITTER_LINK_TO_ORGANIZATION "
            elif create_twitter_link_to_organization:
                # Create TwitterLinkToOrganization
                results = twitter_user_manager.create_twitter_link_to_organization(
                    twitter_link_to_voter_twitter_id, linked_organization_we_vote_id)
                if results['twitter_link_to_organization_saved']:
                    status += "TwitterLinkToOrganization_CREATED_AFTER_REPAIR_LINKED_ORGANIZATION "
                else:
                    status += "TwitterLinkToOrganization_NOT_CREATED_AFTER_REPAIR_LINKED_ORGANIZATION "

            if voter.linked_organization_we_vote_id != linked_organization_we_vote_id:
                voter.linked_organization_we_vote_id = linked_organization_we_vote_id
                try:
                    voter.save()
                    status += "REPAIR_MISSING_LINKED_ORG-SUCCESS "
                    voter_repaired = True
                    success = True
                except Exception as e:
                    status += "REPAIR_MISSING_LINKED_ORG-COULD_NOT_SAVE_VOTER "
            else:
                status += "NO_REPAIR_NEEDED "

        results = {
            'status': status,
            'success': success,
            'voter_repaired': voter_repaired,
            'voter': voter,
        }
        return results

    def repair_organization(self, organization):
        if not hasattr(organization, 'organization_name'):
            return organization

        # Is there a Twitter handle linked to this organization? If so, update the information.
        twitter_user_manager = TwitterUserManager()
        twitter_link_results = twitter_user_manager.retrieve_twitter_link_to_organization_from_organization_we_vote_id(
            organization.we_vote_id)
        if twitter_link_results['twitter_link_to_organization_found']:
            twitter_link_to_organization = twitter_link_results['twitter_link_to_organization']

            twitter_results = \
                twitter_user_manager.retrieve_twitter_user_locally_or_remotely(twitter_link_to_organization.twitter_id)

            if twitter_results['twitter_user_found']:
                twitter_user = twitter_results['twitter_user']
                try:
                    organization.organization_name = twitter_user.twitter_name
                    organization.twitter_description = twitter_user.twitter_description
                    organization.twitter_followers_count = twitter_user.twitter_followers_count if \
                        positive_value_exists(twitter_user.twitter_followers_count) else 0
                    organization.twitter_profile_image_url_https = twitter_user.twitter_profile_image_url_https
                    organization.organization_website = twitter_user.twitter_url
                    organization.twitter_name = twitter_user.twitter_name
                    organization.save()

                    organization_list_manager = OrganizationListManager()
                    repair_results = organization_list_manager.repair_twitter_related_organization_caching(
                        twitter_link_to_organization.twitter_id)

                except Exception as e:
                    pass
        return organization

    # We can use any of these four unique identifiers:
    #   organization.id, we_vote_id, organization_website, organization_twitter_handle
    # Pass in the value if we want it saved. Pass in "False" if we want to leave it the same.
    def update_or_create_organization(self, organization_id, we_vote_id,
                                      organization_website_search, organization_twitter_search,
                                      organization_name=False, organization_website=False,
                                      organization_twitter_handle=False, organization_email=False,
                                      organization_facebook=False, organization_image=False,
                                      organization_type=UNKNOWN, refresh_from_twitter=False,
                                      facebook_id=False, facebook_email=False,
                                      facebook_profile_image_url_https=False,
                                      facebook_background_image_url_https=False,
                                      ):
        """
        Either update or create an organization entry.
        :param organization_id:
        :param we_vote_id:
        :param organization_website_search:
        :param organization_twitter_search:
        :param organization_name:
        :param organization_website:
        :param organization_twitter_handle:
        :param organization_email:
        :param organization_facebook:
        :param organization_image:
        :param refresh_from_twitter:
        :param facebook_id:
        :param facebook_email:
        :param facebook_profile_image_url_https:
        :param facebook_background_image_url_https:
        :return:
        """

        exception_does_not_exist = False
        exception_multiple_object_returned = False
        organization_on_stage_found = False
        new_organization_created = False
        organization_on_stage = Organization()
        status = "ENTERING_UPDATE_OR_CREATE_ORGANIZATION"

        organization_id = convert_to_int(organization_id) if positive_value_exists(organization_id) else False
        we_vote_id = we_vote_id.strip().lower() if we_vote_id else False
        organization_website_search = organization_website_search.strip() if organization_website_search else False
        organization_twitter_search = organization_twitter_search.strip() if organization_twitter_search else False
        organization_name = organization_name.strip() if organization_name else False
        organization_website = organization_website.strip() if organization_website else False
        # TODO DALE We should stop saving organization_twitter_handle without saving a TwitterLinkToOrganization
        if organization_twitter_handle is False or organization_twitter_handle == 'False':
            organization_twitter_handle = ""
        organization_twitter_handle = organization_twitter_handle.strip() if organization_twitter_handle else False
        organization_email = organization_email.strip() if organization_email else False
        organization_facebook = organization_facebook.strip() if organization_facebook else False
        organization_image = organization_image.strip() if organization_image else False
        organization_type = organization_type.strip() if organization_type else UNKNOWN

        # Values that can only be updated by a refresh_from_twitter
        twitter_user_id = False
        twitter_name = False
        twitter_followers_count = False
        twitter_profile_image_url_https = False
        twitter_profile_banner_url_https = False
        twitter_profile_background_image_url_https = False
        twitter_description = False
        twitter_location = False
        twitter_url = False

        # Facebook values
        facebook_email = facebook_email.strip() if facebook_email else False

        # In order of authority
        # 1) organization_id exists? Find it with organization_id or fail
        # 2) we_vote_id exists? Find it with we_vote_id or fail
        # 3) facebook_id exists? Try to find it. If not, go to step 4
        # 4) organization_website_search exists? Try to find it. If not, go to step 5
        # 5) organization_twitter_search exists? Try to find it. If not, exit

        success = False
        if positive_value_exists(organization_id) or positive_value_exists(we_vote_id):
            # If here, we know we are updating
            # 1) organization_id exists? Find it with organization_id or fail
            # 2) we_vote_id exists? Find it with we_vote_id or fail
            organization_results = self.retrieve_organization(organization_id, we_vote_id)
            if organization_results['success']:
                organization_on_stage = organization_results['organization']
                organization_on_stage_found = True

                # Now that we have an organization to update, get supplemental data from Twitter if
                # refresh_from_twitter is true
                if positive_value_exists(organization_twitter_handle) and refresh_from_twitter:
                    twitter_user_id = 0
                    results = retrieve_twitter_user_info(twitter_user_id, organization_twitter_handle)
                    if results['success']:
                        twitter_json = results['twitter_json']
                        if positive_value_exists(twitter_json['id']):
                            twitter_user_id = convert_to_int(twitter_json['id'])
                        if positive_value_exists(twitter_json['name']):
                            twitter_name = twitter_json['name']
                            # Use Twitter value if a value for this variable was NOT passed in
                            if not positive_value_exists(organization_name):
                                organization_name = twitter_json['name']
                        # TODO DALE Look more closely at saving the actual url from twitter (not the Twitter shortcut)
                        # if positive_value_exists(twitter_json['twitter_url']):
                        #     # Use Twitter value if a value for this variable was NOT passed in
                        #     if not positive_value_exists(organization_website):
                        #         organization_website = twitter_json['twitter_url']
                        twitter_followers_count = convert_to_int(twitter_json['followers_count'])
                        if positive_value_exists(twitter_json['profile_image_url_https']):
                            twitter_profile_image_url_https = twitter_json['profile_image_url_https']
                        if 'profile_banner_url' in twitter_json:
                            twitter_profile_banner_url_https = twitter_json['profile_banner_url']
                        twitter_profile_background_image_url_https = \
                            twitter_json['profile_background_image_url_https']
                        twitter_description = twitter_json['description']
                        twitter_location = twitter_json['location']

                value_changed = False
                if organization_name or organization_website or organization_twitter_handle \
                        or organization_email or organization_facebook or organization_image:
                    value_changed = True
                    if organization_name:
                        organization_on_stage.organization_name = organization_name
                    if organization_website:
                        organization_on_stage.organization_website = organization_website
                    if organization_twitter_handle:
                        organization_on_stage.organization_twitter_handle = organization_twitter_handle
                    if organization_email:
                        organization_on_stage.organization_email = organization_email
                    if organization_facebook:
                        organization_on_stage.organization_facebook = organization_facebook
                    if organization_image:
                        organization_on_stage.organization_image = organization_image

                if twitter_user_id or twitter_name or twitter_followers_count or twitter_profile_image_url_https \
                        or twitter_profile_banner_url_https or twitter_profile_background_image_url_https \
                        or twitter_description or twitter_location:
                    # Values that can only be added by a refresh_from_twitter
                    value_changed = True
                    if twitter_user_id:
                        organization_on_stage.twitter_user_id = twitter_user_id
                    if twitter_name:
                        organization_on_stage.twitter_name = twitter_name
                    if twitter_followers_count:
                        organization_on_stage.twitter_followers_count = twitter_followers_count
                    if twitter_profile_image_url_https:
                        organization_on_stage.twitter_profile_image_url_https = twitter_profile_image_url_https
                    if twitter_profile_banner_url_https:
                        organization_on_stage.twitter_profile_banner_url_https = twitter_profile_banner_url_https
                    if twitter_profile_background_image_url_https:
                        organization_on_stage.twitter_profile_background_image_url_https = \
                            twitter_profile_background_image_url_https
                    if twitter_description:
                        organization_on_stage.twitter_description = twitter_description
                    if twitter_location:
                        organization_on_stage.twitter_location = twitter_location

                if facebook_id or facebook_email or facebook_profile_image_url_https or \
                        facebook_background_image_url_https:
                    value_changed = True
                    status += " FACEBOOK_VALUES_TO_BE_ADDED"
                    if facebook_id:
                        organization_on_stage.facebook_id = facebook_id
                    if facebook_email:
                        organization_on_stage.facebook_email = facebook_email
                    if facebook_profile_image_url_https:
                        organization_on_stage.facebook_profile_image_url_https = facebook_profile_image_url_https
                    if facebook_background_image_url_https:
                        organization_on_stage.facebook_background_image_url_https = \
                            facebook_background_image_url_https

                if value_changed:
                    try:
                        organization_on_stage.save()
                        success = True
                        status = "SAVED_WITH_ORG_ID_OR_WE_VOTE_ID"
                    except Exception as e:
                        logger.error("organization_on_stage.save() failed to save #1")
                else:
                    success = True
                    status = "NO_CHANGES_SAVED_WITH_ORG_ID_OR_WE_VOTE_ID"
            else:
                status = "ORGANIZATION_COULD_NOT_BE_FOUND_WITH_ORG_ID_OR_WE_VOTE_ID"
        else:
            try:
                found_with_status = ''
                organization_on_stage_found = False

                # 3a) FacebookLinkToVoter exists? If not, go to step 3b
                if not organization_on_stage_found and positive_value_exists(facebook_id):
                    facebook_manager = FacebookManager()
                    facebook_results = facebook_manager.retrieve_facebook_link_to_voter(facebook_id)
                    if facebook_results['facebook_link_to_voter_found']:
                        facebook_link_to_voter = facebook_results['facebook_link_to_voter']
                        voter_manager = VoterManager()
                        voter_results = \
                            voter_manager.retrieve_voter_by_we_vote_id(facebook_link_to_voter.voter_we_vote_id)
                        if voter_results['voter_found']:
                            voter = voter_results['voter']
                            if positive_value_exists(voter.linked_organization_we_vote_id):
                                try:
                                    organization_on_stage = Organization.objects.get(
                                        we_vote_id=voter.linked_organization_we_vote_id)
                                    organization_on_stage_found = True
                                    found_with_status = "FOUND_WITH_FACEBOOK_LINK_TO_VOTER"
                                except Organization.MultipleObjectsReturned as e:
                                    exception_multiple_object_returned = True
                                    logger.warning("Organization.MultipleObjectsReturned FACEBOOK_LINK_TO_VOTER")
                                except Organization.DoesNotExist as e:
                                    # Not a problem -- an organization matching this facebook_id wasn't found
                                    exception_does_not_exist = True

                # 3b) facebook_id exists? Try to find it. If not, go to step 4
                if not organization_on_stage_found and positive_value_exists(facebook_id):
                    try:
                        organization_on_stage = Organization.objects.get(
                            facebook_id=facebook_id)
                        organization_on_stage_found = True
                        found_with_status = "FOUND_WITH_FACEBOOK_ID"
                    except Organization.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        logger.warning("Organization.MultipleObjectsReturned facebook_id")
                    except Organization.DoesNotExist as e:
                        # Not a problem -- an organization matching this facebook_id wasn't found
                        exception_does_not_exist = True

                # 4) organization_website_search exists? Try to find it. If not, go to step 5
                if not organization_on_stage_found and positive_value_exists(organization_website_search):
                    try:
                        organization_on_stage = Organization.objects.get(
                            organization_website__iexact=organization_website_search)
                        organization_on_stage_found = True
                        found_with_status = "FOUND_WITH_WEBSITE"
                    except Organization.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        logger.warning("Organization.MultipleObjectsReturned organization_website")
                    except Organization.DoesNotExist as e:
                        # Not a problem -- an organization matching this organization_website wasn't found
                        exception_does_not_exist = True

                # 5) organization_twitter_search exists? Try to find it. If not, exit
                if not organization_on_stage_found and positive_value_exists(organization_twitter_search):
                    try:
                        organization_on_stage = Organization.objects.get(
                            organization_twitter_handle__iexact=organization_twitter_search)
                        organization_on_stage_found = True
                        found_with_status = "FOUND_WITH_TWITTER"
                    except Organization.MultipleObjectsReturned as e:
                        handle_record_found_more_than_one_exception(e, logger)
                        exception_multiple_object_returned = True
                        logger.warning("Organization.MultipleObjectsReturned organization_twitter_handle")
                    except Organization.DoesNotExist as e:
                        # Not a problem -- an organization matching this twitter handle wasn't found
                        exception_does_not_exist = True

                if organization_on_stage_found:
                    value_changed = False

                    # 3) Save based on facebook_id
                    if facebook_id or facebook_email or facebook_profile_image_url_https:
                        value_changed = True
                        if facebook_id:
                            organization_on_stage.facebook_id = facebook_id
                        if facebook_email:
                            organization_on_stage.facebook_email = facebook_email
                        if facebook_profile_image_url_https:
                            organization_on_stage.facebook_profile_image_url_https = facebook_profile_image_url_https

                    # 4 & 5) Save values entered in steps 4 & 5
                    # Now that we have an organization to update, get supplemental data from Twitter if
                    # refresh_from_twitter is true
                    if positive_value_exists(organization_twitter_handle) and refresh_from_twitter:
                        twitter_user_id = 0
                        results = retrieve_twitter_user_info(twitter_user_id, organization_twitter_handle)
                        if results['success']:
                            twitter_json = results['twitter_json']
                            if positive_value_exists(twitter_json['id']):
                                twitter_user_id = convert_to_int(twitter_json['id'])
                            if positive_value_exists(twitter_json['name']):
                                twitter_name = twitter_json['name']
                                # Use Twitter value if a value for this variable was NOT passed in
                                if not positive_value_exists(organization_name):
                                    organization_name = twitter_json['name']
                            twitter_followers_count = convert_to_int(twitter_json['followers_count'])
                            if positive_value_exists(twitter_json['profile_image_url_https']):
                                twitter_profile_image_url_https = twitter_json['profile_image_url_https']
                            if 'profile_banner_url' in twitter_json:
                                twitter_profile_banner_url_https = twitter_json['profile_banner_url']
                            twitter_profile_background_image_url_https = \
                                twitter_json['profile_background_image_url_https']
                            twitter_description = twitter_json['description']
                            twitter_location = twitter_json['location']

                    if organization_name or organization_website or organization_twitter_handle \
                            or organization_email or organization_facebook or organization_image:
                        value_changed = True
                        if organization_name:
                            organization_on_stage.organization_name = organization_name
                        if organization_website:
                            organization_on_stage.organization_website = organization_website
                        if organization_twitter_handle:
                            organization_on_stage.organization_twitter_handle = organization_twitter_handle
                        if organization_email:
                            organization_on_stage.organization_email = organization_email
                        if organization_facebook:
                            organization_on_stage.organization_facebook = organization_facebook
                        if organization_image:
                            organization_on_stage.organization_image = organization_image

                    if twitter_user_id or twitter_name or twitter_followers_count or twitter_profile_image_url_https \
                            or twitter_profile_banner_url_https or twitter_profile_background_image_url_https \
                            or twitter_description or twitter_location:
                        # Values that can only be added by a refresh_from_twitter
                        value_changed = True
                        if twitter_user_id:
                            organization_on_stage.twitter_user_id = twitter_user_id
                        if twitter_name:
                            organization_on_stage.twitter_name = twitter_name
                        if twitter_followers_count:
                            organization_on_stage.twitter_followers_count = twitter_followers_count
                        if twitter_profile_image_url_https:
                            organization_on_stage.twitter_profile_image_url_https = twitter_profile_image_url_https
                        if twitter_profile_banner_url_https:
                            organization_on_stage.twitter_profile_banner_url_https = twitter_profile_banner_url_https
                        if twitter_profile_background_image_url_https:
                            organization_on_stage.twitter_profile_background_image_url_https = \
                                twitter_profile_background_image_url_https
                        if twitter_description:
                            organization_on_stage.twitter_description = twitter_description
                        if twitter_location:
                            organization_on_stage.twitter_location = twitter_location

                    if value_changed:
                        try:
                            organization_on_stage.save()
                            success = True
                            status = found_with_status + " SAVED"
                        except Exception as e:
                            logger.error("organization_on_stage.save() failed to save #2")

                    else:
                        success = True
                        status = found_with_status + " NO_CHANGES_SAVED"
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)

        if not organization_on_stage_found:
            try:
                # Now that we have an organization to update, get supplemental data from Twitter if
                # refresh_from_twitter is true
                twitter_user_id = 0
                if positive_value_exists(organization_twitter_handle) and refresh_from_twitter:
                    results = retrieve_twitter_user_info(twitter_user_id, organization_twitter_handle)
                    if results['success']:
                        twitter_json = results['twitter_json']
                        if positive_value_exists(twitter_json['id']):
                            twitter_user_id = convert_to_int(twitter_json['id'])
                        if positive_value_exists(twitter_json['name']):
                            twitter_name = twitter_json['name']
                            # Use Twitter value if a value for this variable was NOT passed in
                            if not positive_value_exists(organization_name):
                                organization_name = twitter_json['name']
                        twitter_followers_count = convert_to_int(twitter_json['followers_count'])
                        if positive_value_exists(twitter_json['profile_image_url_https']):
                            twitter_profile_image_url_https = twitter_json['profile_image_url_https']
                        if 'profile_banner_url' in twitter_json:
                            twitter_profile_banner_url_https = twitter_json['profile_banner_url']
                        twitter_profile_background_image_url_https = \
                            twitter_json['profile_background_image_url_https']
                        twitter_description = twitter_json['description']
                        twitter_location = twitter_json['location']

                # If here, create new organization
                results = Organization.objects.create_organization(organization_name, organization_website,
                                                                   organization_twitter_handle, organization_email,
                                                                   organization_facebook, organization_image,
                                                                   twitter_user_id, organization_type)
                if results['success']:
                    new_organization_created = True
                    success = True
                    value_changed = False
                    status = "NEW_ORGANIZATION_CREATED_IN_UPDATE_OR_CREATE"
                    organization_on_stage = results['organization']

                    if twitter_user_id or twitter_name or twitter_followers_count or twitter_profile_image_url_https \
                            or twitter_profile_banner_url_https or twitter_profile_background_image_url_https \
                            or twitter_description or twitter_location:
                        value_changed = True
                        status += " TWITTER_VALUES_RETRIEVED"

                        # Values that can only be added by a refresh_from_twitter
                        if twitter_user_id:
                            organization_on_stage.twitter_user_id = twitter_user_id
                        if twitter_name:
                            organization_on_stage.twitter_name = twitter_name
                        if twitter_followers_count:
                            organization_on_stage.twitter_followers_count = twitter_followers_count
                        if twitter_profile_image_url_https:
                            organization_on_stage.twitter_profile_image_url_https = twitter_profile_image_url_https
                        if twitter_profile_banner_url_https:
                            organization_on_stage.twitter_profile_banner_url_https = twitter_profile_banner_url_https
                        if twitter_profile_background_image_url_https:
                            organization_on_stage.twitter_profile_background_image_url_https = \
                                twitter_profile_background_image_url_https
                        if twitter_description:
                            organization_on_stage.twitter_description = twitter_description
                        if twitter_location:
                            organization_on_stage.twitter_location = twitter_location

                    if facebook_id or facebook_email or facebook_profile_image_url_https or \
                            facebook_background_image_url_https:
                        value_changed = True
                        status += " FACEBOOK_VALUES_TO_BE_ADDED"
                        if facebook_id:
                            organization_on_stage.facebook_id = facebook_id
                        if facebook_email:
                            organization_on_stage.facebook_email = facebook_email
                        if facebook_profile_image_url_https:
                            organization_on_stage.facebook_profile_image_url_https = facebook_profile_image_url_https
                        if facebook_background_image_url_https:
                            organization_on_stage.facebook_background_image_url_https = \
                                facebook_background_image_url_https

                    if value_changed:
                        try:
                            organization_on_stage.save()
                            status += " EXTRA_VALUES_SAVED"
                        except Exception as e:
                            logger.error("organization_on_stage.save() failed to save #3")
                    else:
                        status += " EXTRA_VALUES_NOT_SAVED"

                else:
                    success = False
                    status = results['status']
                    organization_on_stage = Organization

            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                success = False
                status = "NEW_ORGANIZATION_COULD_NOT_BE_CREATED_OR_EXTRA_VALUES_ADDED"
                organization_on_stage = Organization

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'organization':             organization_on_stage,
            'new_organization_created': new_organization_created,
        }
        return results

    def update_organization_social_media(self, organization, organization_twitter_handle=False,
                                         organization_facebook=False):
        """
        Update an organization entry with general social media data. If a value is passed in False
        it means "Do not update"
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        success = False
        status = "ENTERING_UPDATE_ORGANIZATION_SOCIAL_MEDIA"
        values_changed = False

        if organization_twitter_handle is False or organization_twitter_handle == 'False':
            organization_twitter_handle = ""
        organization_twitter_handle = organization_twitter_handle.strip() if organization_twitter_handle else False
        organization_facebook = organization_facebook.strip() if organization_facebook else False
        # organization_image = organization_image.strip() if organization_image else False

        if organization:
            if organization_twitter_handle:
                organization_twitter_handle = str(organization_twitter_handle)
                object_organization_twitter_handle = str(organization.organization_twitter_handle)
                if organization_twitter_handle.lower() != object_organization_twitter_handle.lower():
                    organization.organization_twitter_handle = organization_twitter_handle
                    values_changed = True
            if organization_facebook:
                if organization_facebook != organization.organization_facebook:
                    organization.organization_facebook = organization_facebook
                    values_changed = True

            if values_changed:
                organization.save()
                success = True
                status = "SAVED_ORG_SOCIAL_MEDIA"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_ORG_SOCIAL_MEDIA"

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'organization':             organization,
        }
        return results

    def update_organization_twitter_details(self, organization, twitter_json,
                                            cached_twitter_profile_image_url_https=False,
                                            cached_twitter_profile_background_image_url_https=False,
                                            cached_twitter_profile_banner_url_https=False,
                                            we_vote_hosted_profile_image_url_large=False,
                                            we_vote_hosted_profile_image_url_medium=False,
                                            we_vote_hosted_profile_image_url_tiny=False):
        """
        Update an organization entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_ORGANIZATION_TWITTER_DETAILS"
        values_changed = False

        # TODO DALE We should stop saving organization_twitter_handle without saving a TwitterLinkToOrganization
        if organization:
            if 'id' in twitter_json and positive_value_exists(twitter_json['id']):
                if convert_to_int(twitter_json['id']) != organization.twitter_user_id:
                    organization.twitter_user_id = convert_to_int(twitter_json['id'])
                    values_changed = True
            if 'screen_name' in twitter_json and positive_value_exists(twitter_json['screen_name']):
                incoming_twitter_screen_name = str(twitter_json['screen_name'])
                if incoming_twitter_screen_name is False or incoming_twitter_screen_name == 'False':
                    incoming_twitter_screen_name = ""
                organization_twitter_handle = str(organization.organization_twitter_handle)
                if organization_twitter_handle is False or organization_twitter_handle == 'False':
                    organization_twitter_handle = ""
                if incoming_twitter_screen_name.lower() != organization_twitter_handle.lower():
                    organization.organization_twitter_handle = twitter_json['screen_name']
                    values_changed = True
            if 'name' in twitter_json and positive_value_exists(twitter_json['name']):
                if twitter_json['name'] != organization.twitter_name:
                    organization.twitter_name = twitter_json['name']
                    values_changed = True
            if 'followers_count' in twitter_json and positive_value_exists(twitter_json['followers_count']):
                if convert_to_int(twitter_json['followers_count']) != organization.twitter_followers_count:
                    organization.twitter_followers_count = convert_to_int(twitter_json['followers_count'])
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_image_url_https):
                organization.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                values_changed = True
            elif 'profile_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_image_url_https']):
                if twitter_json['profile_image_url_https'] != organization.twitter_profile_image_url_https:
                    organization.twitter_profile_image_url_https = twitter_json['profile_image_url_https']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                organization.twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
                values_changed = True
            elif 'profile_banner_url' in twitter_json and positive_value_exists(twitter_json['profile_banner_url']):
                if twitter_json['profile_banner_url'] != organization.twitter_profile_banner_url_https:
                    organization.twitter_profile_banner_url_https = twitter_json['profile_banner_url']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                organization.twitter_profile_background_image_url_https = \
                    cached_twitter_profile_background_image_url_https
                values_changed = True
            elif 'profile_background_image_url_https' in twitter_json and positive_value_exists(
                    twitter_json['profile_background_image_url_https']):
                if twitter_json['profile_background_image_url_https'] != \
                        organization.twitter_profile_background_image_url_https:
                    organization.twitter_profile_background_image_url_https = \
                        twitter_json['profile_background_image_url_https']
                    values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                organization.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                organization.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                organization.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_json and positive_value_exists(twitter_json['description']):
                if twitter_json['description'] != organization.twitter_description:
                    organization.twitter_description = twitter_json['description']
                    values_changed = True
            if 'location' in twitter_json and positive_value_exists(twitter_json['location']):
                if twitter_json['location'] != organization.twitter_location:
                    organization.twitter_location = twitter_json['location']
                    values_changed = True

            if values_changed:
                organization.save()
                success = True
                status = "SAVED_ORG_TWITTER_DETAILS"
            else:
                success = True
                status = "NO_CHANGES_SAVED_TO_ORG_TWITTER_DETAILS"

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
        }
        return results

    @staticmethod
    def update_organization_single_voter_data(twitter_user_id,
                                              we_vote_hosted_profile_image_url_large,
                                              we_vote_hosted_profile_image_url_medium,
                                              we_vote_hosted_profile_image_url_tiny,
                                              twitter_profile_banner_url_https):
        """
        Make a best effort to update the organization for a single voter with twitter images
        :param twitter_user_id:
        :param we_vote_hosted_profile_image_url_large:
        :param we_vote_hosted_profile_image_url_medium:
        :param we_vote_hosted_profile_image_url_tiny:
        :param twitter_profile_banner_url_https:
        :return: True/False
        """

        organization_manager = OrganizationManager()
        results = organization_manager.retrieve_organization(0, '', '', twitter_user_id)

        if not results['organization_found']:
            logger.info("update_organization_single_voter_data was not able to find " + str(twitter_user_id))
            return False
        try:
            organization = results['organization']

            organization.twitter_profile_banner_url_https = twitter_profile_banner_url_https
            organization.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
            organization.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
            organization.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
            organization.save()

        except Exception as e:
            handle_exception(e, logger=logger,
                             exception_message="exception thrown in update_organization_single_voter_data")

        return True

    def reset_organization_image_details(self, organization, twitter_profile_image_url_https=None,
                                         twitter_profile_background_image_url_https=None,
                                         twitter_profile_banner_url_https=None, facebook_profile_image_url_https=None):
        """
        Reset an organization entry with original image details from we vote image.
        """
        success = False
        status = "ENTERING_RESET_ORGANIZATION_IMAGE_DETAILS"

        if organization:
            if positive_value_exists(twitter_profile_image_url_https):
                organization.twitter_profile_image_url_https = twitter_profile_image_url_https
            if positive_value_exists(twitter_profile_background_image_url_https):
                organization.twitter_profile_background_image_url_https = twitter_profile_background_image_url_https
            if positive_value_exists(twitter_profile_banner_url_https):
                organization.twitter_profile_banner_url_https = twitter_profile_banner_url_https

            if positive_value_exists(facebook_profile_image_url_https):
                organization.facebook_profile_image_url_https = facebook_profile_image_url_https

            organization.we_vote_hosted_profile_image_url_large = ''
            organization.we_vote_hosted_profile_image_url_medium = ''
            organization.we_vote_hosted_profile_image_url_tiny = ''
            organization.save()
            success = True
            status = "RESET_ORGANIZATION_IMAGE_DETAILS"

        results = {
            'success':      success,
            'status':       status,
            'organization': organization,
        }
        return results

    def clear_organization_twitter_details(self, organization):
        """
        Update an organization entry with details retrieved from the Twitter API.
        """
        success = False
        status = "ENTERING_UPDATE_ORGANIZATION_TWITTER_DETAILS"

        if organization:
            organization.twitter_user_id = 0
            # We leave the handle in place
            # organization.organization_twitter_handle = ""
            organization.twitter_name = ''
            organization.twitter_followers_count = 0
            organization.twitter_profile_image_url_https = ''
            organization.we_vote_hosted_profile_image_url_large = ''
            organization.we_vote_hosted_profile_image_url_medium = ''
            organization.we_vote_hosted_profile_image_url_tiny = ''
            organization.twitter_description = ''
            organization.twitter_location = ''
            organization.save()
            success = True
            status = "CLEARED_ORG_TWITTER_DETAILS"

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
        }
        return results

    def delete_organization(self, organization_id):
        organization_id = convert_to_int(organization_id)
        organization_deleted = False

        try:
            if organization_id:
                results = self.retrieve_organization(organization_id)
                if results['organization_found']:
                    organization = results['organization']
                    organization_id = organization.id
                    organization.delete()
                    organization_deleted = True
        except Exception as e:
            handle_exception(e, logger=logger, exception_message="exception thrown in delete_organization")

        results = {
            'success':              organization_deleted,
            'organization_deleted': organization_deleted,
            'organization_id':      organization_id,
        }
        return results


class OrganizationListManager(models.Manager):
    """
    A class for working with lists of Organizations
    """

    def organization_search_find_any_possibilities(self, organization_name, organization_twitter_handle='',
                                                   organization_website='', organization_email='',
                                                   organization_facebook=''):
        """
        We want to find *any* possible organization that includes any of the search terms
        :param organization_name:
        :param organization_twitter_handle:
        :param organization_website:
        :param organization_email:
        :param organization_facebook:
        :return:
        """
        organization_list_for_json = {}
        try:
            filters = []
            organization_list_for_json = []
            organization_objects_list = []
            if positive_value_exists(organization_name):
                new_filter = Q(organization_name__icontains=organization_name)
                # # Find entries with any word in the string - DALE 2016-05-06 This didn't feel right
                # from functools import reduce
                # organization_name_list = organization_name.split(" ")
                # new_filter = reduce(lambda x, y: x | y,
                #                     [Q(organization_name__icontains=word) for word in organization_name_list])
                filters.append(new_filter)

            # The master organization twitter_handle data is in TwitterLinkToOrganization but we try to keep
            # organization_twitter_handle up-to-date for rapid searches like this.
            if positive_value_exists(organization_twitter_handle):
                new_filter = Q(organization_twitter_handle__icontains=organization_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(organization_website):
                new_filter = Q(organization_website__icontains=organization_website)
                filters.append(new_filter)

            if positive_value_exists(organization_email):
                new_filter = Q(organization_email__icontains=organization_email)
                filters.append(new_filter)

            if positive_value_exists(organization_facebook):
                new_filter = Q(organization_facebook__icontains=organization_facebook)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                organization_objects_list = Organization.objects.filter(final_filters)

            if len(organization_objects_list):
                organizations_found = True
                status = 'ORGANIZATIONS_RETRIEVED'
                for organization in organization_objects_list:
                    one_organization_json = {
                        'organization_id': organization.id,
                        'organization_we_vote_id': organization.we_vote_id,
                        'organization_name':
                            organization.organization_name if positive_value_exists(
                                organization.organization_name) else '',
                        'organization_website': organization.organization_website if positive_value_exists(
                            organization.organization_website) else '',
                        'organization_twitter_handle':
                            organization.organization_twitter_handle if positive_value_exists(
                                organization.organization_twitter_handle) else '',
                        'organization_email':
                            organization.organization_email if positive_value_exists(
                                organization.organization_email) else '',
                        'organization_facebook':
                            organization.organization_facebook if positive_value_exists(
                                organization.organization_facebook) else '',
                    }
                    organization_list_for_json.append(one_organization_json)
            else:
                organizations_found = False
                status = 'NO_ORGANIZATIONS_RETRIEVED'
            success = True
        except Organization.DoesNotExist:
            # No organizations found. Not a problem.
            organizations_found = False
            status = 'NO_ORGANIZATIONS_FOUND_DoesNotExist'
            success = True  # We are still successful if no organizations are found
        except Exception as e:
            organizations_found = False
            handle_exception(e, logger=logger,
                             exception_message="exception thrown in organization_search_find_any_possibilities")
            status = 'FAILED organization_search_find_any_possibilities ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))
            success = False

        results = {
            'status':               status,
            'success':              success,
            'organizations_found':  organizations_found,
            'organizations_list':   organization_list_for_json,
        }
        return results

    def repair_twitter_related_organization_caching(self, twitter_user_id):
        """
        Since cached twitter values are used by the WebApp to determine security settings, we want to
        make sure this cached twitter data is up-to-date.
        :param twitter_user_id:
        :return:
        """
        status = ""
        success = False
        filters = []
        organization_list_found = False
        organization_list_objects = []

        if not positive_value_exists(twitter_user_id):
            status += "TWITTER_USER_ID_NOT_INCLUDED "
            error_results = {
                'status':               status,
                'success':              success,
            }
            return error_results

        twitter_user_manager = TwitterUserManager()
        twitter_link_results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
            twitter_user_id)
        if not twitter_link_results['twitter_link_to_organization_found']:
            # We don't have an official TwitterLinkToOrganization, so we don't want to clean up any caching
            status += "TWITTER_LINK_TO_ORGANIZATION_NOT_FOUND-CACHING_REPAIR_NOT_EXECUTED "
        else:
            # Is there an official TwitterLinkToOrganization for this Twitter account? If so, update the information.
            twitter_link_to_organization = twitter_link_results['twitter_link_to_organization']

            twitter_results = \
                twitter_user_manager.retrieve_twitter_user_locally_or_remotely(twitter_link_to_organization.twitter_id)

            if not twitter_results['twitter_user_found']:
                status += "TWITTER_USER_NOT_FOUND "
            else:
                twitter_user = twitter_results['twitter_user']

                # Loop through all of the organizations that have any of these fields set:
                # - organization.twitter_user_id
                # - organization.organization_twitter_handle
                try:
                    organization_queryset = Organization.objects.all()

                    # We want to find organizations with *any* of these values
                    new_filter = Q(twitter_user_id=twitter_user_id)
                    filters.append(new_filter)

                    if positive_value_exists(twitter_user.twitter_handle):
                        new_filter = Q(organization_twitter_handle__iexact=twitter_user.twitter_handle)
                        filters.append(new_filter)

                    # Add the first query
                    if len(filters):
                        final_filters = filters.pop()

                        # ...and "OR" the remaining items in the list
                        for item in filters:
                            final_filters |= item

                        organization_queryset = organization_queryset.filter(final_filters)

                    organization_list_objects = list(organization_queryset)

                    if len(organization_list_objects):
                        organization_list_found = True
                        status += 'TWITTER_RELATED_ORGANIZATIONS_RETRIEVED '
                        success = True
                    else:
                        status += 'NO_TWITTER_RELATED_ORGANIZATIONS_RETRIEVED1 '
                        success = True
                except Organization.DoesNotExist:
                    # No organizations found. Not a problem.
                    status += 'NO_TWITTER_RELATED_ORGANIZATIONS_RETRIEVED2 '
                    organization_list_objects = []
                    success = True
                except Exception as e:
                    handle_exception(e, logger=logger,
                                     exception_message=
                                     "exception thrown in repair_twitter_related_organization_caching")
                    status = 'FAILED repair_twitter_related_organization_caching ' \
                             '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False

                if organization_list_found:
                    # Loop through all organizations found with twitter_user_id and organization_twitter_handle
                    # If not the official TwitterLinkToOrganization, then clear out those values.
                    for organization in organization_list_objects:
                        if organization.we_vote_id != twitter_link_to_organization.organization_we_vote_id:
                            try:
                                organization.twitter_user_id = 0
                                organization.organization_twitter_handle = ""
                                organization.save()
                                status += "CLEARED_TWITTER_VALUES-organization.we_vote_id " \
                                          "" + organization.we_vote_id + " "
                            except Exception as e:
                                status += "COULD_NOT_CLEAR_TWITTER_VALUES-organization.we_vote_id " \
                                          "" + organization.we_vote_id + " "

                # Now make sure that the organization table has values for the organization linked with the
                # official TwitterLinkToOrganization
                organization_manager = OrganizationManager()
                organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                    twitter_link_to_organization.organization_we_vote_id)
                if not organization_results['organization_found']:
                    status += "COULD_NOT_UPDATE_LINKED_ORGANIZATION "
                else:
                    linked_organization = organization_results['organization']
                    try:
                        save_organization = False
                        if linked_organization.twitter_user_id != twitter_user_id:
                            linked_organization.twitter_user_id = twitter_user_id
                            save_organization = True
                        if linked_organization.organization_twitter_handle != twitter_user.twitter_handle:
                            linked_organization.organization_twitter_handle = twitter_user.twitter_handle
                            save_organization = True
                        if save_organization:
                            linked_organization.save()
                            status += "SAVED_LINKED_ORGANIZATION "
                        else:
                            status += "NO_NEED_TO_SAVE_LINKED_ORGANIZATION "

                    except Exception as e:
                        status += "COULD_NOT_SAVE_LINKED_ORGANIZATION "

        results = {
            'status': status,
            'success': success,
        }
        return results

    def retrieve_organizations_by_id_list(self, organization_ids_followed_by_voter):
        organization_list = []
        organization_list_found = False

        if not type(organization_ids_followed_by_voter) is list:
            status = 'NO_ORGANIZATIONS_FOUND_MISSING_ORGANIZATION_LIST'
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'organization_list_found':      organization_list_found,
                'organization_list':            organization_list,
            }
            return results

        if not len(organization_ids_followed_by_voter):
            status = 'NO_ORGANIZATIONS_FOUND_NO_ORGANIZATIONS_IN_LIST'
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'organization_list_found':      organization_list_found,
                'organization_list':            organization_list,
            }
            return results

        try:
            organization_queryset = Organization.objects.all()
            organization_queryset = organization_queryset.filter(
                id__in=organization_ids_followed_by_voter)
            organization_queryset = organization_queryset.order_by('organization_name')
            organization_list = organization_queryset

            if len(organization_list):
                organization_list_found = True
                status = 'ORGANIZATIONS_FOUND_BY_ORGANIZATION_LIST'
            else:
                status = 'NO_ORGANIZATIONS_FOUND_BY_ORGANIZATION_LIST'
            success = True
        except Exception as e:
            status = 'retrieve_organizations_by_id_list: Unable to retrieve organizations from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'organization_list_found':      organization_list_found,
            'organization_list':            organization_list,
        }
        return results

    def retrieve_organizations_from_non_unique_identifiers(self, twitter_handle):
        keep_looking_for_duplicates = True
        organization_list = []
        organization_list_found = False
        organization_found = False
        multiple_entries_found = False
        organization = Organization()
        success = False
        status = ""
        twitter_handle_filtered = extract_twitter_handle_from_text_string(twitter_handle)

        # See if we have linked an organization to this Twitter handle
        twitter_user_manager = TwitterUserManager()
        results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
            twitter_handle_filtered)
        if results['twitter_link_to_organization_found']:
            twitter_link_to_organization = results['twitter_link_to_organization']
            organization_manager = OrganizationManager()
            organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                twitter_link_to_organization.organization_we_vote_id)
            if organization_results['organization_found']:
                organization = organization_results['organization']
                organization_found = True
                keep_looking_for_duplicates = False
                organization_list_found = True
                organization_list.append(organization)
                success = True
                status = "ORGANIZATION_FOUND_FROM_TWITTER_LINK_TO_ORGANIZATION"
            else:
                # Heal the data -- the organization is missing so we should delete the Twitter link
                twitter_id = 0
                delete_results = twitter_user_manager.delete_twitter_link_to_organization(
                    twitter_id, twitter_link_to_organization.organization_we_vote_id)

                if delete_results['twitter_link_to_organization_deleted']:
                    organization_list_manager = OrganizationListManager()
                    repair_results = organization_list_manager.repair_twitter_related_organization_caching(
                        twitter_link_to_organization.twitter_id)
                    status += repair_results['status']

                organization_list_found = False
                success = True
                status += "ORGANIZATION_NOT_FOUND_FROM_TWITTER_LINK_TO_ORGANIZATION-DELETED_BAD_LINK"
        else:
            try:
                organization_queryset = Organization.objects.all()
                organization_queryset = organization_queryset.filter(
                    organization_twitter_handle__iexact=twitter_handle_filtered)
                # If multiple organizations claim the same Twitter handle, select the one with... ??
                # organization_queryset = organization_queryset.order_by('-twitter_followers_count')

                organization_list = list(organization_queryset)

                if len(organization_list):
                    if len(organization_list) == 1:
                        status += 'BATCH_ROW_ACTION_ORGANIZATION_RETRIEVED '
                        organization_list_found = True
                        organization_found = True
                        multiple_entries_found = False
                        organization = organization_list[0]
                        keep_looking_for_duplicates = False
                    else:
                        organization_list_found = True
                        multiple_entries_found = True
                        status += 'ORGANIZATIONS_RETRIEVED_FROM_TWITTER_HANDLE '
                        success = True
                else:
                    status += 'NO_ORGANIZATIONS_RETRIEVED_FROM_TWITTER_HANDLE '
                    success = True
            except Organization.DoesNotExist:
                # No organizations found. Not a problem.
                status += 'NO_ORGANIZATIONS_FOUND_FROM_TWITTER_HANDLE_DoesNotExist'
                organization_list = []
                multiple_entries_found = False
                success = True
            except Exception as e:
                handle_exception(e, logger=logger,
                                 exception_message="exception thrown in retrieve_organizations_"
                                                   "from_non_unique_identifiers")
                status = 'FAILED retrieve_organizations_from_non_unique_identifiers ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
                organization_list = []
                multiple_entries_found = False
                keep_looking_for_duplicates = False

        results = {
            'success':                  success,
            'status':                   status,
            'organization_list_found':  organization_list_found,
            'organization_list':        organization_list,
            'organization_found':       organization_found,
            'organization':             organization,
            'multiple_entries_found':   multiple_entries_found,
        }
        return results

    def retrieve_possible_duplicate_organizations(self, organization_name, organization_twitter_handle, vote_smart_id,
                                                  we_vote_id_from_master=''):
        organization_list_objects = []
        filters = []
        organization_list_found = False

        try:
            organization_queryset = Organization.objects.all()

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(we_vote_id_from_master):
                organization_queryset = organization_queryset.filter(~Q(we_vote_id__iexact=we_vote_id_from_master))

            # We want to find organizations with *any* of these values
            if positive_value_exists(organization_name):
                new_filter = Q(organization_name__iexact=organization_name)
                filters.append(new_filter)

            if positive_value_exists(organization_twitter_handle):
                new_filter = Q(organization_twitter_handle__iexact=organization_twitter_handle)
                filters.append(new_filter)

            if positive_value_exists(vote_smart_id):
                new_filter = Q(vote_smart_id=vote_smart_id)
                filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                organization_queryset = organization_queryset.filter(final_filters)

            organization_list_objects = organization_queryset

            if len(organization_list_objects):
                organization_list_found = True
                status = 'DUPLICATE_ORGANIZATIONS_RETRIEVED'
                success = True
            else:
                status = 'NO_DUPLICATE_ORGANIZATIONS_RETRIEVED'
                success = True
        except Organization.DoesNotExist:
            # No organizations found. Not a problem.
            status = 'NO_DUPLICATE_ORGANIZATIONS_FOUND_DoesNotExist'
            organization_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger,
                             exception_message="exception thrown in retrieve_possible_duplicate_organizations")
            status = 'FAILED retrieve_possible_duplicate_organizations ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'organization_list_found':      organization_list_found,
            'organization_list':            organization_list_objects,
        }
        return results

    def retrieve_organizations_by_organization_we_vote_id_list(self, list_of_organization_we_vote_ids):
        organization_list = []
        organization_list_found = False

        if not type(list_of_organization_we_vote_ids) is list:
            status = 'NO_ORGANIZATIONS_FOUND_MISSING_ORGANIZATION_LIST'
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'organization_list_found':      organization_list_found,
                'organization_list':            organization_list,
            }
            return results

        if not len(list_of_organization_we_vote_ids):
            status = 'NO_ORGANIZATIONS_FOUND_NO_ORGANIZATIONS_IN_LIST'
            success = False
            results = {
                'success':                      success,
                'status':                       status,
                'organization_list_found':      organization_list_found,
                'organization_list':            organization_list,
            }
            return results

        try:
            organization_queryset = Organization.objects.all()
            organization_queryset = organization_queryset.filter(
                we_vote_id__in=list_of_organization_we_vote_ids)
            organization_queryset = organization_queryset.order_by('-twitter_followers_count')
            organization_list = organization_queryset

            if len(organization_list):
                organization_list_found = True
                status = 'ORGANIZATIONS_FOUND_BY_ORGANIZATION_LIST'
            else:
                status = 'NO_ORGANIZATIONS_FOUND_BY_ORGANIZATION_LIST'
            success = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesFollowersRetrieve: Unable to retrieve organizations from db. ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'organization_list_found':      organization_list_found,
            'organization_list':            organization_list,
        }
        return results


class Organization(models.Model):
    # We are relying on built-in Python id field

    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our org info with other
    # organizations
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "org", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_org_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=True)
    organization_name = models.CharField(
        verbose_name="organization name", max_length=255, null=False, blank=False)
    organization_website = models.URLField(verbose_name='url of the endorsing organization', blank=True, null=True)
    organization_email = models.EmailField(
        verbose_name='organization contact email address', max_length=255, unique=False, null=True, blank=True)
    organization_contact_name = models.CharField(max_length=255, null=True, unique=False)
    organization_facebook = models.URLField(verbose_name='url of facebook page', blank=True, null=True)
    organization_image = models.CharField(verbose_name='organization image', max_length=255, null=True, unique=False)
    state_served_code = models.CharField(verbose_name="state this organization serves", max_length=2,
                                         null=True, blank=True)
    # The vote_smart special interest group sigId for this organization
    vote_smart_id = models.BigIntegerField(
        verbose_name="vote smart special interest group id", null=True, blank=True, unique=True)
    organization_description = models.TextField(
        verbose_name="Text description of this organization.", null=True, blank=True)
    organization_address = models.CharField(
        verbose_name='organization street address', max_length=255, unique=False, null=True, blank=True)
    organization_city = models.CharField(max_length=255, null=True, blank=True)
    organization_state = models.CharField(max_length=2, null=True, blank=True)
    organization_zip = models.CharField(max_length=255, null=True, blank=True)
    organization_phone1 = models.CharField(max_length=255, null=True, blank=True)
    organization_phone2 = models.CharField(max_length=255, null=True, blank=True)
    organization_fax = models.CharField(max_length=255, null=True, blank=True)

    # Facebook session information
    facebook_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                       null=True, blank=True)
    fb_username = models.CharField(unique=True, max_length=20, validators=[alphanumeric], null=True)
    facebook_profile_image_url_https = models.URLField(verbose_name='url of image from facebook',
                                                       blank=True, null=True)
    facebook_background_image_url_https = models.URLField(verbose_name='url of cover image from facebook',
                                                          blank=True, null=True)

    # Twitter information
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    organization_twitter_handle = models.CharField(
        verbose_name='organization twitter screen_name', max_length=255, null=True, unique=False)
    twitter_name = models.CharField(
        verbose_name="org name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="org location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(verbose_name="number of twitter followers",
                                                  null=False, blank=True, default=0)
    twitter_profile_image_url_https = models.URLField(verbose_name='url of user logo from twitter',
                                                      blank=True, null=True)
    twitter_profile_background_image_url_https = models.URLField(verbose_name='tile-able background from twitter',
                                                                 blank=True, null=True)
    twitter_profile_banner_url_https = models.URLField(verbose_name='profile banner image from twitter',
                                                       blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)

    # Instagram
    organization_instagram_handle = models.CharField(
        verbose_name='organization instagram screen_name', max_length=255, null=True, unique=False)

    we_vote_hosted_profile_image_url_large = models.URLField(verbose_name='we vote hosted large image url',
                                                              blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.URLField(verbose_name='we vote hosted medium image url',
                                                              blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.URLField(verbose_name='we vote hosted tiny image url',
                                                            blank=True, null=True)

    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_thumbnail_url = models.URLField(verbose_name='url of wikipedia logo thumbnail', blank=True, null=True)
    wikipedia_thumbnail_width = models.IntegerField(verbose_name="width of photo", null=True, blank=True)
    wikipedia_thumbnail_height = models.IntegerField(verbose_name="height of photo", null=True, blank=True)
    wikipedia_photo_url = models.URLField(verbose_name='url of wikipedia logo', blank=True, null=True)

    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.URLField(verbose_name='url of ballotpedia logo', blank=True, null=True)

    organization_type = models.CharField(
        verbose_name="type of org", max_length=2, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    organization_endorsements_api_url = models.URLField(verbose_name='url of endorsements importer', blank=True, null=True)

    def __unicode__(self):
        return str(self.organization_name)

    def organization_photo_url(self):
        """
        For an organization, this heirarchy determines which image gets displayed
        :return: URL to the image to be displayed
        """
        if positive_value_exists(self.organization_image):
            return self.organization_image
        elif positive_value_exists(self.we_vote_hosted_profile_image_url_large):
            return self.we_vote_hosted_profile_image_url_large
        elif positive_value_exists(self.twitter_profile_image_url_https):
            return self.twitter_profile_image_url_https_bigger()
        elif positive_value_exists(self.facebook_profile_image_url_https):
            return self.facebook_profile_image_url_https
        elif positive_value_exists(self.wikipedia_photo_url):
            return self.wikipedia_photo_url
        return ''

    def organization_type_display(self):
        if self.organization_type in ORGANIZATION_TYPE_MAP:
            return ORGANIZATION_TYPE_MAP[self.organization_type]
        else:
            return self.organization_type

    def twitter_profile_image_url_https_bigger(self):
        if self.we_vote_hosted_profile_image_url_large:
            return self.we_vote_hosted_profile_image_url_large
        elif self.twitter_profile_image_url_https:
            return self.twitter_profile_image_url_https.replace("_normal", "_bigger")
        else:
            return ''

    def twitter_profile_image_url_https_original(self):
        if self.twitter_profile_image_url_https:
            return self.twitter_profile_image_url_https.replace("_normal", "")
        else:
            return ''

    class Meta:
        ordering = ('organization_name',)

    objects = OrganizationManager()

    @classmethod
    def create(cls, organization_name, organization_website, organization_twitter_handle, organization_email,
               organization_facebook, organization_image, organization_type, twitter_user_id=None, twitter_name=None,
               twitter_location=None, twitter_followers_count=0, twitter_profile_image_url_https=None,
               twitter_profile_background_image_url_https=None, twitter_profile_banner_url_https=None,
               twitter_description=None, we_vote_hosted_profile_image_url_large=None,
               we_vote_hosted_profile_image_url_medium=None, we_vote_hosted_profile_image_url_tiny=None):

        if organization_twitter_handle is False or organization_twitter_handle == 'False':
            organization_twitter_handle = ""

        organization = cls(organization_name=organization_name,
                           organization_website=organization_website,
                           organization_twitter_handle=organization_twitter_handle,
                           organization_email=organization_email,
                           organization_facebook=organization_facebook,
                           organization_image=organization_image,
                           organization_type=organization_type,
                           twitter_user_id=twitter_user_id,
                           twitter_name=twitter_name,
                           twitter_location=twitter_location,
                           twitter_followers_count=twitter_followers_count,
                           twitter_profile_image_url_https=twitter_profile_image_url_https,
                           twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                           twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                           twitter_description=twitter_description,
                           we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                           we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                           we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)

        return organization

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this organization came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            self.generate_new_we_vote_id()
        super(Organization, self).save(*args, **kwargs)

    def generate_new_we_vote_id(self):
        # ...generate a new id
        site_unique_id_prefix = fetch_site_unique_id_prefix()
        next_local_integer = fetch_next_we_vote_id_org_integer()
        # "wv" = We Vote
        # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
        # "org" = tells us this is a unique id for an org
        # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
        self.we_vote_id = "wv{site_unique_id_prefix}org{next_integer}".format(
            site_unique_id_prefix=site_unique_id_prefix,
            next_integer=next_local_integer,
        )
        # TODO we need to deal with the situation where we_vote_id is NOT unique on save
        return

    def is_nonprofit_501c3(self):
        return self.organization_type in NONPROFIT_501C3

    def is_nonprofit_501c4(self):
        return self.organization_type in NONPROFIT_501C4

    def is_political_action_committee(self):
        return self.organization_type in POLITICAL_ACTION_COMMITTEE

    def is_corporation(self):
        return self.organization_type in CORPORATION

    def is_news_organization(self):
        return self.organization_type in NEWS_ORGANIZATION

    def is_organization_type_specified(self):
        return self.organization_type in (
            NONPROFIT_501C3, NONPROFIT_501C4, POLITICAL_ACTION_COMMITTEE,
            CORPORATION, NEWS_ORGANIZATION)

    def generate_facebook_link(self):
        if self.organization_facebook:
            return "https://facebook.com/{facebook_page}".format(facebook_page=self.organization_facebook)
        else:
            return ''

    def generate_twitter_link(self):
        if self.organization_twitter_handle:
            return "https://twitter.com/{twitter_handle}".format(twitter_handle=self.organization_twitter_handle)
        else:
            return ''

    def generate_wikipedia_link(self):
        if self.wikipedia_page_title:
            encoded_page_title = self.wikipedia_page_title.replace(" ", "_")
            return "https://en.wikipedia.org/wiki/{page_title}".format(page_title=encoded_page_title)
        else:
            return ''
