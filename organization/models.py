# organization/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q

from candidate.models import PROFILE_IMAGE_TYPE_FACEBOOK, PROFILE_IMAGE_TYPE_TWITTER, PROFILE_IMAGE_TYPE_UNKNOWN, \
    PROFILE_IMAGE_TYPE_UPLOADED, PROFILE_IMAGE_TYPE_VOTE_USA, PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES
from exception.models import handle_exception, \
    handle_record_found_more_than_one_exception, handle_record_not_saved_exception, handle_record_not_found_exception
from import_export_facebook.models import FacebookManager
from twitter.functions import retrieve_twitter_user_info
from twitter.models import TwitterApiCounterManager, TwitterLinkToOrganization, TwitterLinkToVoter, TwitterUserManager
from voter.models import VoterManager
import wevote_functions.admin
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
TRADE_ASSOCIATION = 'TA'
UNKNOWN = 'U'
VOTER = 'V'
ORGANIZATION_TYPE_CHOICES = (
    (CORPORATION, 'Corporation'),
    (GROUP, 'Group'),
    (INDIVIDUAL, 'Individual'),
    (NEWS_ORGANIZATION, 'News Corporation'),
    (NONPROFIT, 'Nonpartisan'),
    (NONPROFIT_501C3, 'Nonprofit 501c3'),
    (NONPROFIT_501C4, 'Nonprofit 501c4'),
    (POLITICAL_ACTION_COMMITTEE, 'Political Action Committee'),
    (PUBLIC_FIGURE, 'Public Figure'),
    (TRADE_ASSOCIATION, 'Trade Association or Union'),
    (UNKNOWN, 'Unknown Type'),
    (ORGANIZATION, 'Group - Organization'),  # Deprecated
)
ORGANIZATION_TYPE_CHOICES_IN_PUBLIC_SPHERE = [CORPORATION, GROUP, NONPROFIT, NONPROFIT_501C3, NONPROFIT_501C4,
                                              NEWS_ORGANIZATION, ORGANIZATION, POLITICAL_ACTION_COMMITTEE,
                                              PUBLIC_FIGURE, TRADE_ASSOCIATION]

# These names lead to text matches on Candidate "I am endorsed by this group" pages that are too common
ORGANIZATION_NAMES_TO_EXCLUDE_FROM_SCRAPER = [
    "ACCE", "ADAction", "BLOC", "Check", "Cher", "cia", "CoD", "CS", "CSS",
    "data", "DID", "donate", "Google", "Greg",
    "Ian", "IMG", "Isaac",
    "JAC", "Jenn", "Location", "Mark", "Module", "More",
    "NEA", "NEWS", "NEXT",
    "Pat", "People", "Ping", "plan", "products",
    "Ray", "RESULTS", "Ro",
    "Sarah", "SAVE", "Section", "Settings", "spa", "steve",
    "The Candidate", "The Democrats", "TIME", "Twitter", "Uber", "vote", "Will", "Z",
]

# We strip out straight 'wixsite.com', but not 'candidate.wixsite.com'
ORGANIZATION_WEBSITES_TO_EXCLUDE_FROM_SCRAPER = [
    'ballotpedia.org',
    'bit.ly',
    'developer.chrome.com',
    'developer.mozilla.org',
    'en.wikipedia.org',
    'facebook.com',
    'instagram.com',
    'linkedin.com',
    'linktr.ee',
    'nationbuilder.com',
    'secure.actblue.com',
    'secure.anedot.com',
    'secure.ngpvan.com',
    'secure.winred.com',
    't.co',
    'tinyurl.com',
    'twitter.com',
    'wix.com',
    'wixsite.com',
    'wordpress.com',
    'www.',
    'youtube.com',
]

ORGANIZATION_TYPE_MAP = {
    CORPORATION:                'Corporation',
    GROUP:                      'Group',
    INDIVIDUAL:                 'Individual',
    NEWS_ORGANIZATION:          'News Organization',
    NONPROFIT:                  'Nonpartisan',
    NONPROFIT_501C3:            'Nonprofit 501c3 - Remove',
    NONPROFIT_501C4:            'Nonprofit 501c4 - Remove',
    POLITICAL_ACTION_COMMITTEE: 'Political Action Committee',
    PUBLIC_FIGURE:              'Public Figure',
    TRADE_ASSOCIATION:          'Trade Association or Union',
    UNKNOWN:                    'Unknown Type',
}

# When merging organizations, these are the fields we check for figure_out_organization_conflict_values
ORGANIZATION_UNIQUE_IDENTIFIERS = [
    'ballotpedia_page_title',
    'ballotpedia_photo_url',
    'chosen_domain_string',
    'chosen_domain_string2',
    'chosen_domain_string3',
    'chosen_favicon_url_https',
    'chosen_feature_package',
    'chosen_google_analytics_tracking_id',
    'chosen_hide_we_vote_logo',
    'chosen_html_verification_string',
    'chosen_logo_url_https',
    'chosen_organization_api_pass_code',
    'chosen_prevent_sharing_opinions',
    'chosen_ready_introduction_text',
    'chosen_ready_introduction_title',
    'chosen_social_share_description',
    'chosen_social_share_image_256x256_url_https',
    'chosen_social_share_master_image_url_https',
    'chosen_subdomain_string',
    'chosen_subscription_plan',
    'facebook_background_image_url_https',
    'facebook_email',
    'facebook_id',
    'facebook_profile_image_url_https',
    'fb_username',
    'issue_analysis_admin_notes',
    'issue_analysis_done',
    'most_recent_name_update_from_voter_first_and_last',
    'organization_address',
    'organization_city',
    'organization_contact_form_url',
    'organization_contact_name',
    'organization_description',
    'organization_email',
    'organization_endorsements_api_url',
    'organization_facebook',
    'organization_fax',
    'organization_image',
    'organization_instagram_handle',
    'organization_name',
    'organization_phone1',
    'organization_phone2',
    'organization_state',
    'organization_twitter_handle',
    'organization_type',
    'organization_website',
    'organization_zip',
    'state_served_code',
    'subscription_plan_end_day_text',
    'subscription_plan_features_active',
    # 'twitter_description',
    # 'twitter_followers_count',
    # 'twitter_location',
    # 'twitter_name',
    # 'twitter_profile_background_image_url_https',
    # 'twitter_profile_banner_url_https',
    # 'twitter_profile_image_url_https',
    # 'twitter_user_id',
    'vote_smart_id',
    'we_vote_hosted_profile_image_url_large',
    'we_vote_hosted_profile_image_url_medium',
    'we_vote_hosted_profile_image_url_tiny',
    'wikipedia_page_id',
    'wikipedia_page_title',
    'wikipedia_photo_url',
    'wikipedia_thumbnail_height',
    'wikipedia_thumbnail_url',
    'wikipedia_thumbnail_width',
]

# These are values used in features_provided_bitmap
# Mirrored in WebApp/src/js/constants/VoterConstants.js
# Related to MasterFeaturePackage in donate/models.py, features_provided_bitmap
# Related to Organization, features_provided_bitmap
CHOSEN_FAVICON_ALLOWED = 1  # Able to upload/display custom favicon in browser
CHOSEN_FULL_DOMAIN_ALLOWED = 2  # Able to specify full domain for white label version of WeVote.US
CHOSEN_GOOGLE_ANALYTICS_ALLOWED = 4  # Able to specify and have rendered org's Google Analytics Javascript
CHOSEN_SOCIAL_SHARE_IMAGE_ALLOWED = 8  # Able to specify sharing images for white label version of WeVote.US
CHOSEN_SOCIAL_SHARE_DESCRIPTION_ALLOWED = 16  # Able to specify sharing description for white label version of WeVote.US
CHOSEN_PROMOTED_ORGANIZATIONS_ALLOWED = 32  # Able to promote endorsements from specific organizations

alphanumeric = RegexValidator(r'^[0-9a-zA-Z]*$', message='Only alphanumeric characters are allowed.')

logger = wevote_functions.admin.get_logger(__name__)


class OrganizationLinkToHashtag(models.Model):

    objects = None
    organization_we_vote_id = models.CharField(verbose_name="we vote permanent id", max_length=255, unique=False)
    hashtag_text = models.CharField(verbose_name="hashtag text", max_length=255, unique=False)
    # tweet_id = models.BigIntegerField(verbose_name="tweet id", unique=True)
    # published_datetime = models.DateTimeField(verbose_name="published datetime")
    # organization_twitter_handle = models.CharField(verbose_name="organization twitter handle", max_length=15,
    #                                               unique=False)


class OrganizationLinkToWordOrPhrase(models.Model):
    def __unicode__(self):
        return "OrganizationLinkToWordOrPhrase"

    organization_we_vote_id = models.CharField(verbose_name="we vote permanent id", max_length=255, unique=True)
    word_or_phrase_text = models.CharField(verbose_name="text of a word or phrase", max_length=255, unique=False)
    tweet_id = models.BigIntegerField(verbose_name="tweet id", unique=True)
    published_datetime = models.DateTimeField(verbose_name="published datetime")
    organization_twitter_handle = models.CharField(verbose_name="organization twitter handle", max_length=15,
                                                   unique=False)
    # organization_we_vote_id
    # word_or_phrase
    # tweet_id
    # published_datetime


class OrganizationMembershipLinkToVoter(models.Model):
    """
    This is the link between an Organization and a We Vote voter account, so we can show organizations
    data about their members.
    """
    objects = None
    organization_we_vote_id = models.CharField(verbose_name="we vote id for organization", max_length=255, unique=False)
    voter_we_vote_id = models.CharField(verbose_name="we vote id for the voter owner", max_length=255, unique=False)
    external_voter_id = models.CharField(
        verbose_name="id for the voter in other system", max_length=255, unique=False)


class OrganizationManager(models.Manager):
    """
    A class for working with the Organization model
    """
    # DO WE WANT CREATE OR UPDATE AND CREATE # Do we want the organization twitter handle
    @staticmethod
    def update_or_create_organization_link_to_hashtag(organization_we_vote_id, hashtag_text):
        success = False
        status = ""
        organization_link_to_hashtag_created = False

        if not positive_value_exists(organization_we_vote_id):
            status = 'CREATE_ORGANIZATION_LINK_TO_HASHTAG_MISSING_WE_VOTE_ID '
            results = {
                'success':                              success,
                'status':                               status,
                'organization_link_to_hashtag_created': organization_link_to_hashtag_created,
            }
            return results
        # add required for hashtag_text similar to organization_we_vote_id
        try:    
            defaults = {
                "organization_we_vote_id": organization_we_vote_id,
                "hashtag_text": hashtag_text,
            }
            new_organization_link_to_hastag, created = OrganizationLinkToHashtag.objects.update_or_create(
                organization_we_vote_id__iexact=organization_we_vote_id,
                hashtag_text__iexact=hashtag_text,
                defaults=defaults,)
            # NOTE: Hashtags are only significant if there are more than one for a particular issue so I'm not sure
            #   if it makes sense to have individual tweet's id or date.
            # tweet_id=hashtag['tweet_id'],
            # published_datetime=tweet_list['date_published'],
            # organization_twitter_handle=tweet_list['author_handle'])
            status = "CREATE_ORGANIZATION_LINK_TO_HASHTAG_SUCCESSFUL"
            success = True
            organization_link_to_hashtag_created = True
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            success = False
            status = "CREATE_ORGANIZATION_LINK_TO_HASHTAG_FAILED"
            organization_link_to_hashtag_created = False
        results = {
            'success':                              success,
            'status':                               status,
            'organization_link_to_hashtag_created': organization_link_to_hashtag_created,
        }
        return results

    @staticmethod
    def update_or_create_organization_membership_link_to_voter(
            organization_we_vote_id,
            external_voter_id,
            voter_we_vote_id):
        success = False
        status = ""
        insufficient_variables = False
        organization_link_created = False
        organization_link_updated = False

        if not positive_value_exists(organization_we_vote_id):
            status += 'CREATE_ORGANIZATION_MEMBERSHIP_LINK_TO_VOTER_MISSING_ORG_WE_VOTE_ID '
            insufficient_variables = True
        if not positive_value_exists(external_voter_id):
            status += 'CREATE_ORGANIZATION_MEMBERSHIP_LINK_TO_VOTER_MISSING_EXTERNAL_VOTER_ID '
            insufficient_variables = True
        if not positive_value_exists(voter_we_vote_id):
            status += 'CREATE_ORGANIZATION_MEMBERSHIP_LINK_TO_VOTER_MISSING_VOTER_WE_VOTE_ID '
            insufficient_variables = True
        if insufficient_variables:
            results = {
                'success':                      success,
                'status':                       status,
                'organization_link_created':    organization_link_created,
                'organization_link_updated':    organization_link_updated,
            }
            return results
        try:
            defaults = {
                "organization_we_vote_id":  organization_we_vote_id,
                "external_voter_id":        external_voter_id,
                "voter_we_vote_id":         voter_we_vote_id,
            }
            new_organization_link_to_voter, created = OrganizationMembershipLinkToVoter.objects.update_or_create(
                organization_we_vote_id__iexact=organization_we_vote_id,
                external_voter_id=external_voter_id,
                voter_we_vote_id__iexact=voter_we_vote_id,
                defaults=defaults,)
            status += "CREATE_ORGANIZATION_LINK_TO_VOTER_SUCCESSFUL "
            success = True
            organization_link_created = created
            organization_link_updated = not created
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            success = False
            status += "CREATE_ORGANIZATION_LINK_TO_VOTER_FAILED " + str(e) + " "
            organization_link_created = False
            organization_link_updated = False
        results = {
            'success':                      success,
            'status':                       status,
            'organization_link_created':    organization_link_created,
            'organization_link_updated':    organization_link_updated,
        }
        return results

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

    def create_organization(
            self,
            organization_name='',
            organization_website='',
            organization_twitter_handle='',
            organization_email='',
            organization_facebook='',
            organization_image='',
            twitter_id='',
            organization_type='',
            state_served_code=None,
            twitter_profile_background_image_url_https=None,
            twitter_profile_banner_url_https=None,
            twitter_profile_image_url_https=None,
            we_vote_hosted_profile_image_url_large='',
            we_vote_hosted_profile_image_url_medium='',
            we_vote_hosted_profile_image_url_tiny=''):
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
                twitter_profile_image_url_https = twitter_user.twitter_profile_image_url_https
                twitter_profile_background_image_url_https = twitter_user.twitter_profile_background_image_url_https
                twitter_profile_banner_url_https = twitter_user.twitter_profile_banner_url_https
                twitter_description = twitter_user.twitter_description
                if twitter_user.we_vote_hosted_profile_image_url_large:
                    we_vote_hosted_profile_image_url_large = twitter_user.we_vote_hosted_profile_image_url_large
                if twitter_user.we_vote_hosted_profile_image_url_medium:
                    we_vote_hosted_profile_image_url_medium = twitter_user.we_vote_hosted_profile_image_url_medium
                if twitter_user.we_vote_hosted_profile_image_url_tiny:
                    we_vote_hosted_profile_image_url_tiny = twitter_user.we_vote_hosted_profile_image_url_tiny
                organization = Organization.create(
                    organization_name=organization_name,
                    organization_website=organization_website,
                    organization_twitter_handle=organization_twitter_handle,
                    organization_email=organization_email,
                    organization_facebook=organization_facebook,
                    organization_image=organization_image,
                    organization_type=organization_type,
                    state_served_code=state_served_code,
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
                    organization_type=organization_type,
                    state_served_code=state_served_code,
                    twitter_profile_image_url_https=twitter_profile_image_url_https,
                    twitter_profile_background_image_url_https=twitter_profile_background_image_url_https,
                    twitter_profile_banner_url_https=twitter_profile_banner_url_https,
                    we_vote_hosted_profile_image_url_large=we_vote_hosted_profile_image_url_large,
                    we_vote_hosted_profile_image_url_medium=we_vote_hosted_profile_image_url_medium,
                    we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny
                )
            organization.save()  # We do this so the we_vote_id is created
            status = "CREATE_ORGANIZATION_SUCCESSFUL "
            success = True
            organization_created = True
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            organization = Organization
            status = "CREATE_ORGANIZATION_FAILED " + str(e)
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

    @staticmethod
    def duplicate_organization(organization):
        """
        Starting with an existing organization, create a duplicate version with different we_vote_id
        :param organization:
        :return:
        """
        success = False
        status = ""
        organization_duplicated = False

        try:
            organization.id = None  # Remove the primary key, so it is forced to save a new entry
            organization.pk = None
            organization.facebook_email = None
            organization.fb_username = None
            # clear unique Twitter information
            organization.organization_twitter_handle = None
            organization.twitter_description = None
            organization.twitter_followers_count = 0
            organization.twitter_location = None
            organization.twitter_user_id = None
            organization.we_vote_id = None  # Clear out existing we_vote_id
            organization.generate_new_we_vote_id()
            organization.save()  # We do this so the we_vote_id is created
            status += "DUPLICATE_ORGANIZATION_SUCCESSFUL "
            success = True
            organization_duplicated = True
        except Exception as e:
            handle_record_not_saved_exception(e, logger=logger)
            organization = Organization
            status += "DUPLICATE_ORGANIZATION_FAILED " + str(e) + " "
        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
            'organization_duplicated':  organization_duplicated,
        }
        return results

    def heal_voter_missing_linked_organization_we_vote_id(self, voter_on_stage):
        success = True
        status = ''
        voter_healed = False
        organization_manager = OrganizationManager()
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
                voter_healed = True
                status += "LINKED_ORGANIZATION_WE_VOTE_ID_CREATED "
            except Exception as e:
                status += "COULD_NOT_SAVE_VOTER: " + str(e) + " "
                success = False
        else:
            status += "CREATE_ORGANIZATION_FUNCTION_FAILED "
            success = False

        results = {
            'success': success,
            'status': status,
            'voter_healed': voter_healed,
            'voter': voter_on_stage,
        }
        return results

    def retrieve_organization_from_id(self, organization_id, read_only=False):
        return self.retrieve_organization(organization_id, read_only=read_only)

    def retrieve_organization_from_we_vote_id(self, organization_we_vote_id, read_only=False):
        return self.retrieve_organization(0, organization_we_vote_id, read_only=read_only)

    def retrieve_organization_from_we_vote_id_and_pass_code(self, organization_we_vote_id, organization_api_pass_code,
                                                            read_only=False):
        return self.retrieve_organization(0, organization_we_vote_id,
                                          organization_api_pass_code=organization_api_pass_code,
                                          read_only=read_only)

    def retrieve_organization_from_vote_smart_id(self, vote_smart_id, read_only=False):
        return self.retrieve_organization(0, '', vote_smart_id, read_only=read_only)

    def retrieve_organization_from_incoming_hostname(self, incoming_hostname, read_only=False):
        return self.retrieve_organization(incoming_hostname=incoming_hostname, read_only=read_only)

    def retrieve_organization_from_twitter_handle(self, twitter_handle, read_only=False):
        organization_id = 0
        organization_we_vote_id = ""

        twitter_user_manager = TwitterUserManager()
        twitter_retrieve_results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
            twitter_handle, read_only=True)  # Always read_only
        if twitter_retrieve_results['twitter_link_to_organization_found']:
            twitter_link_to_organization = twitter_retrieve_results['twitter_link_to_organization']
            organization_we_vote_id = twitter_link_to_organization.organization_we_vote_id

        return self.retrieve_organization(organization_id, organization_we_vote_id, read_only=read_only)

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
        results = facebook_manager.retrieve_facebook_link_to_voter_from_facebook_id(facebook_id, read_only=True)
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

    def retrieve_organization(
            self,
            organization_id=None,
            we_vote_id=None,
            vote_smart_id=None,
            twitter_user_id=None,
            incoming_hostname=None,
            organization_api_pass_code=False,
            read_only=False):
        """
        Get an organization, based the passed in parameters
        :param organization_id:
        :param we_vote_id:
        :param vote_smart_id:
        :param twitter_user_id:
        :param incoming_hostname:
        :param organization_api_pass_code:
        :param read_only:
        :return: the matching organization object
        """
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        organization_on_stage = Organization()
        organization_on_stage_id = 0
        status = ""
        try:
            if positive_value_exists(organization_id):
                status = "RETRIEVING_ORGANIZATION_WITH_ID "
                if read_only:
                    organization_on_stage = Organization.objects.using('readonly').get(id=organization_id)
                else:
                    organization_on_stage = Organization.objects.get(id=organization_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_ID "
            elif positive_value_exists(we_vote_id) and positive_value_exists(organization_api_pass_code):
                status = "RETRIEVING_ORGANIZATION_WITH_WE_VOTE_ID_AND_PASS_CODE "
                if read_only:
                    organization_on_stage = Organization.objects.using('readonly').get(
                        we_vote_id=we_vote_id,
                        chosen_organization_api_pass_code=organization_api_pass_code,
                    )
                else:
                    organization_on_stage = Organization.objects.get(
                        we_vote_id=we_vote_id,
                        chosen_organization_api_pass_code=organization_api_pass_code,
                    )
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_WE_VOTE_ID_AND_PASS_CODE "
            elif positive_value_exists(we_vote_id):
                status = "RETRIEVING_ORGANIZATION_WITH_WE_VOTE_ID "
                if read_only:
                    organization_on_stage = Organization.objects.using('readonly').get(we_vote_id=we_vote_id)
                else:
                    organization_on_stage = Organization.objects.get(we_vote_id=we_vote_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_WE_VOTE_ID "
            elif positive_value_exists(vote_smart_id):
                status = "ERROR_RETRIEVING_ORGANIZATION_WITH_VOTE_SMART_ID "
                if read_only:
                    organization_on_stage = Organization.objects.using('readonly').get(vote_smart_id=vote_smart_id)
                else:
                    organization_on_stage = Organization.objects.get(vote_smart_id=vote_smart_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_VOTE_SMART_ID "
            elif positive_value_exists(twitter_user_id):
                status = "RETRIEVING_ORGANIZATION_WITH_TWITTER_ID "
                if read_only:
                    organization_on_stage = Organization.objects.using('readonly').get(twitter_user_id=twitter_user_id)
                else:
                    organization_on_stage = Organization.objects.get(twitter_user_id=twitter_user_id)
                organization_on_stage_id = organization_on_stage.id
                status = "ORGANIZATION_FOUND_WITH_TWITTER_ID "
            elif positive_value_exists(incoming_hostname):
                skip = ['wevote.us', 'quality.wevote.us', 'localhost', 'wevotedeveloper']
                if incoming_hostname not in skip:
                    status = "RETRIEVING_ORGANIZATION_WITH_INCOMING_HOSTNAME "
                    incoming_hostname = incoming_hostname.strip().lower()
                    incoming_hostname = incoming_hostname.replace('http://', '')
                    incoming_hostname = incoming_hostname.replace('https://', '')
                    incoming_subdomain = incoming_hostname.replace('.wevote.us', '')
                    if read_only:
                        organization_on_stage = Organization.objects.using('readonly')\
                            .get(Q(chosen_domain_string__iexact=incoming_hostname) |
                                 Q(chosen_domain_string2__iexact=incoming_hostname) |
                                 Q(chosen_domain_string3__iexact=incoming_hostname) |
                                 Q(chosen_subdomain_string__iexact=incoming_subdomain))
                    else:
                        organization_on_stage = Organization.objects\
                            .get(Q(chosen_domain_string__iexact=incoming_hostname) |
                                 Q(chosen_domain_string2__iexact=incoming_hostname) |
                                 Q(chosen_domain_string3__iexact=incoming_hostname) |
                                 Q(chosen_subdomain_string__iexact=incoming_subdomain))
                    organization_on_stage_id = organization_on_stage.id
                    status = "ORGANIZATION_FOUND_WITH_INCOMING_HOSTNAME "
                else:
                    # No need to do an expensive query
                    status = "ORGANIZATION_CHECK_FOR_WEVOTE_US "
                    error_result = True
                    exception_does_not_exist = True
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status += "ERROR_MORE_THAN_ONE_ORGANIZATION_FOUND "
            # logger.warning("Organization.MultipleObjectsReturned")
        except Organization.DoesNotExist as e:
            status += "DOES_NOT_EXIST-ORGANIZATION_NOT_FOUND "
            # handle_exception(e, logger=logger, exception_message=status)
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

    def retrieve_organization_reserved_hostname(self, incoming_hostname, read_only=False):
        status = ""
        success = False
        hostname_is_reserved = False
        reserved_domain_found = False
        reserved_domain = None
        if not positive_value_exists(incoming_hostname):
            status += "MISSING_INCOMING_HOSTNAME "
            results = {
                'success': success,
                'status': status,
                'hostname_is_reserved':     hostname_is_reserved,
                'reserved_domain':          reserved_domain,
                'reserved_domain_found':    reserved_domain_found,
            }
            return results

        if incoming_hostname == 'localhost':
            status += "INCOMING_HOSTNAME_IS_LOCALHOST "
            results = {
                'success': True,
                'status': True,
                'hostname_is_reserved': True,
                'reserved_domain': False,
                'reserved_domain_found': False,
            }
            return results

        incoming_hostname = incoming_hostname.strip().lower()
        incoming_hostname = incoming_hostname.replace('http://', '')
        incoming_hostname = incoming_hostname.replace('https://', '')
        incoming_subdomain = incoming_hostname.replace('.wevote.us', '')

        try:
            if read_only:
                reserved_domain = OrganizationReservedDomain.objects.using('readonly') \
                    .get(Q(full_domain_string__iexact=incoming_hostname) |
                         Q(subdomain_string__iexact=incoming_subdomain))
                reserved_domain_found = True
                hostname_is_reserved = True
            else:
                reserved_domain = OrganizationReservedDomain.objects \
                    .get(Q(full_domain_string__iexact=incoming_hostname) |
                         Q(subdomain_string__iexact=incoming_subdomain))
                reserved_domain_found = True
                hostname_is_reserved = True
        except OrganizationReservedDomain.MultipleObjectsReturned as e:
            hostname_is_reserved = True
            status += "RETRIEVE_ISSUE_MULTIPLE_OBJECTS_RETURNED " + str(e) + " "
        except Exception as e:
            success = False
            status += "COULD_NOT_FIND_SINGLE_ENTRY " + str(e) + " "
        results = {
            'success':                  success,
            'status':                   status,
            'hostname_is_reserved':     hostname_is_reserved,
            'reserved_domain':          reserved_domain,
            'reserved_domain_found':    reserved_domain_found,
        }
        return results

    def retrieve_team_member_list(
            self,
            can_edit_campaignx_owned_by_organization=None,
            organization_we_vote_id='',
            voter_we_vote_id='',
            read_only=False):
        team_member_list_found = False
        team_member_list = []
        try:
            if positive_value_exists(read_only):
                queryset = OrganizationTeamMember.objects.using('readonly').all()
            else:
                queryset = OrganizationTeamMember.objects.all()
            if can_edit_campaignx_owned_by_organization is not None:
                queryset = queryset.filter(
                    can_edit_campaignx_owned_by_organization=can_edit_campaignx_owned_by_organization)
            if positive_value_exists(organization_we_vote_id):
                queryset = queryset.filter(organization_we_vote_id=organization_we_vote_id)
            if positive_value_exists(voter_we_vote_id):
                queryset = queryset.filter(voter_we_vote_id=voter_we_vote_id)
            team_member_list = list(queryset)
            if len(team_member_list):
                team_member_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if team_member_list_found:
            return team_member_list
        else:
            team_member_list = []
            return team_member_list

    def fetch_external_voter_id(self, organization_we_vote_id, voter_we_vote_id):
        if positive_value_exists(organization_we_vote_id) and positive_value_exists(voter_we_vote_id):
            link_query = OrganizationMembershipLinkToVoter.objects.using('readonly').all()
            link_query = link_query.filter(organization_we_vote_id=organization_we_vote_id)
            link_query = link_query.filter(voter_we_vote_id=voter_we_vote_id)
            external_voter = link_query.first()
            if external_voter:
                return external_voter.external_voter_id
        return ''

    def fetch_organization_id(self, we_vote_id):
        organization_id = 0
        if positive_value_exists(we_vote_id):
            organization_manager = OrganizationManager()
            results = organization_manager.retrieve_organization(organization_id, we_vote_id, read_only=True)
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
            results = self.retrieve_organization(organization_id, read_only=True)
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
                or organization.organization_name == "" \
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
            twitter_id, voter.we_vote_id)  # Cannot be read_only
        if twitter_link_to_voter_results['twitter_link_to_voter_found']:
            twitter_link_to_voter = twitter_link_to_voter_results['twitter_link_to_voter']
            twitter_link_to_voter_twitter_id = twitter_link_to_voter.twitter_id
            twitter_link_to_voter_found = True
            twitter_link_to_organization_results = \
                twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_user_id(
                    twitter_link_to_voter_twitter_id)  # Cannot be read_only
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
                    status += "NO_ORGANIZATION_FOUND_BASED_ON_TWITTER_LINK "
            else:
                status += "NO_TWITTER_LINK_TO_ORGANIZATION_FOUND "
        else:
            status += "NO_TWITTER_LINK_TO_VOTER_FOUND "

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
                            twitter_link_to_voter_twitter_id)  # Cannot be read_only
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
            status += "LINKED_ORG_NOT_ATTACHED_TO_VOTER_OBJECT "

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
                            status += "REPAIR_MISSING_LINKED_ORG-COULD_NOT_REMOVE_LINKED_ORGANIZATION_WE_VOTE_ID " + \
                                      str(e) + " "

            # If this voter is linked to a Twitter id, see if there is also an org linked to the same Twitter id,
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
            organization_manager = OrganizationManager()
            create_results = organization_manager.create_organization(
                organization_name=voter.get_full_name(),
                organization_image=voter.voter_photo_url(),
                organization_type=INDIVIDUAL,
                we_vote_hosted_profile_image_url_large=voter.we_vote_hosted_profile_image_url_large,
                we_vote_hosted_profile_image_url_medium=voter.we_vote_hosted_profile_image_url_medium,
                we_vote_hosted_profile_image_url_tiny=voter.we_vote_hosted_profile_image_url_tiny
            )
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
        elif self.organization_name_needs_repair(organization):
            voter_manager = VoterManager()
            results = voter_manager.retrieve_voter_by_organization_we_vote_id(organization.we_vote_id, read_only=True)
            if results['voter_found']:
                voter = results['voter']
                try:
                    real_name_only = True
                    replacement_organization_name = voter.get_full_name(real_name_only)
                    if positive_value_exists(replacement_organization_name):
                        organization.organization_name = replacement_organization_name
                        organization.save()
                except Exception as e:
                    pass
        return organization

    def save_fresh_twitter_details_to_organization(
            self,
            organization=None,
            organization_we_vote_id='',
            twitter_user=None):
        """
        Update organization entry with details retrieved from the Twitter API.
        """
        organization_updated = False
        success = True
        status = ""
        values_changed = False

        if not hasattr(twitter_user, 'twitter_id'):
            success = False
            status += "VALID_TWITTER_USER_NOT_PROVIDED "

        if success:
            if not hasattr(organization, 'organization_twitter_handle') \
                    and positive_value_exists(organization_we_vote_id):
                # Retrieve organization to update
                pass

        if not hasattr(organization, 'organization_twitter_handle'):
            status += "VALID_ORGANIZATION_NOT_PROVIDED_TO_UPDATE_TWITTER_DETAILS "
            success = False

        if not positive_value_exists(organization.organization_twitter_handle):
            status += "ORGANIZATION_TWITTER_HANDLE_MISSING "
            success = False

        if success:
            if organization.organization_twitter_handle.lower() != twitter_user.twitter_handle.lower():
                status += "ORGANIZATION_TWITTER_HANDLE_MISMATCH "
                success = False

        if not success:
            results = {
                'success':              success,
                'status':               status,
                'organization':         organization,
                'organization_updated': organization_updated,
            }
            return results

        if positive_value_exists(twitter_user.twitter_description):
            if twitter_user.twitter_description != organization.twitter_description:
                organization.twitter_description = twitter_user.twitter_description
                values_changed = True
        if positive_value_exists(twitter_user.twitter_followers_count):
            if twitter_user.twitter_followers_count != organization.twitter_followers_count:
                organization.twitter_followers_count = twitter_user.twitter_followers_count
                values_changed = True
        if positive_value_exists(twitter_user.twitter_handle):
            # In case the capitalization of the name changes
            if twitter_user.twitter_handle != organization.organization_twitter_handle:
                organization.organization_twitter_handle = twitter_user.twitter_handle
                values_changed = True
        if positive_value_exists(twitter_user.twitter_handle_updates_failing):
            if twitter_user.twitter_handle_updates_failing != organization.twitter_handle_updates_failing:
                organization.twitter_handle_updates_failing = twitter_user.twitter_handle_updates_failing
                values_changed = True
        if positive_value_exists(twitter_user.twitter_id):
            if twitter_user.twitter_id != organization.twitter_user_id:
                organization.twitter_user_id = twitter_user.twitter_id
                values_changed = True
        if positive_value_exists(twitter_user.twitter_location):
            if twitter_user.twitter_location != organization.twitter_location:
                organization.twitter_location = twitter_user.twitter_location
                values_changed = True
        if positive_value_exists(twitter_user.twitter_name):
            if twitter_user.twitter_name != organization.twitter_name:
                organization.twitter_name = twitter_user.twitter_name
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_image_url_https):
            if twitter_user.twitter_profile_image_url_https != organization.twitter_profile_image_url_https:
                organization.twitter_profile_image_url_https = twitter_user.twitter_profile_image_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_background_image_url_https):
            if twitter_user.twitter_profile_background_image_url_https != \
                    organization.twitter_profile_background_image_url_https:
                organization.twitter_profile_background_image_url_https = \
                    twitter_user.twitter_profile_background_image_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_profile_banner_url_https):
            if twitter_user.twitter_profile_banner_url_https != organization.twitter_profile_banner_url_https:
                organization.twitter_profile_banner_url_https = twitter_user.twitter_profile_banner_url_https
                values_changed = True
        if positive_value_exists(twitter_user.twitter_url):
            if not positive_value_exists(organization.organization_website):
                organization.organization_website = twitter_user.twitter_url
                values_changed = True
            # Use this when we add more website fields
            # from representative.controllers import add_value_to_next_representative_spot
            # results = add_value_to_next_representative_spot(
            #     field_name_base='organization_website',
            #     new_value_to_add=twitter_user.twitter_url,
            #     representative=organization,
            # )
            # if results['success'] and results['values_changed']:
            #     organization = results['organization']
            #     values_changed = True
            # if not results['success']:
            #     status += results['status']
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_large):
            if twitter_user.we_vote_hosted_profile_image_url_large != \
                    organization.we_vote_hosted_profile_twitter_image_url_large:
                organization.we_vote_hosted_profile_twitter_image_url_large = \
                    twitter_user.we_vote_hosted_profile_image_url_large
                values_changed = True
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_medium):
            if twitter_user.we_vote_hosted_profile_image_url_medium != \
                    organization.we_vote_hosted_profile_twitter_image_url_medium:
                organization.we_vote_hosted_profile_twitter_image_url_medium = \
                    twitter_user.we_vote_hosted_profile_image_url_medium
                values_changed = True
        if positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_tiny):
            if twitter_user.we_vote_hosted_profile_image_url_tiny != \
                    organization.we_vote_hosted_profile_twitter_image_url_tiny:
                organization.we_vote_hosted_profile_twitter_image_url_tiny = \
                    twitter_user.we_vote_hosted_profile_image_url_tiny
                values_changed = True

        if organization.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_UNKNOWN and \
                positive_value_exists(twitter_user.we_vote_hosted_profile_image_url_large):
            organization.profile_image_type_currently_active = PROFILE_IMAGE_TYPE_TWITTER
            values_changed = True
        if organization.profile_image_type_currently_active == PROFILE_IMAGE_TYPE_TWITTER:
            if twitter_user.we_vote_hosted_profile_image_url_large != \
                    organization.we_vote_hosted_profile_image_url_large:
                organization.we_vote_hosted_profile_image_url_large = \
                    twitter_user.we_vote_hosted_profile_image_url_large
                values_changed = True
            if twitter_user.we_vote_hosted_profile_image_url_medium != \
                    organization.we_vote_hosted_profile_image_url_medium:
                organization.we_vote_hosted_profile_image_url_medium = \
                    twitter_user.we_vote_hosted_profile_image_url_medium
                values_changed = True
            if twitter_user.we_vote_hosted_profile_image_url_tiny != \
                    organization.we_vote_hosted_profile_image_url_tiny:
                organization.we_vote_hosted_profile_image_url_tiny = \
                    twitter_user.we_vote_hosted_profile_image_url_tiny
                values_changed = True

        if values_changed:
            try:
                organization.save()
                organization_updated = True
                success = True
                status += "SAVED_ORGANIZATION_TWITTER_DETAILS "
            except Exception as e:
                success = False
                status += "NO_CHANGES_SAVED_TO_ORGANIZATION_TWITTER_DETAILS: " + str(e) + " "

        results = {
            'success':              success,
            'status':               status,
            'organization':         organization,
            'organization_updated': organization_updated,
        }
        return results

    # We can use any of these four unique identifiers:
    #   organization.id, we_vote_id, organization_website, organization_twitter_handle
    # Pass in the value if we want it saved. Pass in "False" if we want to leave it the same.
    def update_or_create_organization(
            self,
            # Values for search
            organization_id=0,
            we_vote_id='',
            organization_website_search='',
            organization_twitter_search='',
            # Values to save
            chosen_domain_string=False,
            chosen_domain_string2=False,
            chosen_domain_string3=False,
            chosen_google_analytics_tracking_id=False,
            chosen_html_verification_string=False,
            chosen_hide_we_vote_logo=None,
            chosen_prevent_sharing_opinions=None,
            chosen_ready_introduction_text=False,
            chosen_ready_introduction_title=False,
            chosen_social_share_description=False,
            chosen_subdomain_string=False,
            chosen_subscription_plan=False,
            facebook_background_image_url_https=False,
            facebook_email=False,
            facebook_id=False,
            facebook_profile_image_url_https=False,
            organization_description=False,
            organization_email=False,
            organization_facebook=False,
            organization_image=False,
            organization_instagram_handle=False,
            organization_name=False,
            organization_twitter_handle=False,
            organization_type=False,
            organization_website=False,
            profile_image_type_currently_active=False,
            refresh_from_twitter=False,
    ):
        """
        Either update or create an organization entry.
        :param organization_id:
        :param we_vote_id:
        :param organization_website_search:
        :param organization_twitter_search:
        :param chosen_domain_string:
        :param chosen_domain_string2:
        :param chosen_domain_string3:
        :param chosen_google_analytics_tracking_id:
        :param chosen_html_verification_string:
        :param chosen_hide_we_vote_logo:
        :param chosen_prevent_sharing_opinions:
        :param chosen_ready_introduction_text:
        :param chosen_ready_introduction_title:
        :param chosen_social_share_description:
        :param chosen_subdomain_string:
        :param chosen_subscription_plan:
        :param facebook_background_image_url_https:
        :param facebook_email:
        :param facebook_id:
        :param facebook_profile_image_url_https:
        :param organization_description:
        :param organization_email:
        :param organization_facebook:
        :param organization_image:
        :param organization_instagram_handle:
        :param organization_name:
        :param organization_twitter_handle:
        :param organization_type:
        :param organization_website:
        :param profile_image_type_currently_active:
        :param refresh_from_twitter:
        :return:
        """
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        organization_on_stage_found = False
        new_organization_created = False
        organization_on_stage = Organization()
        twitter_api_counter_manager = TwitterApiCounterManager()
        status = "ENTERING_UPDATE_OR_CREATE_ORGANIZATION "

        organization_id = convert_to_int(organization_id) if positive_value_exists(organization_id) else False
        we_vote_id = we_vote_id.strip().lower() if we_vote_id else False
        organization_website_search = organization_website_search.strip() if organization_website_search else False
        organization_twitter_search = organization_twitter_search.strip() if organization_twitter_search else False
        organization_name = organization_name.strip() if organization_name is not False else False
        organization_description = organization_description.strip() \
            if organization_description is not False else False
        organization_website = organization_website.strip() if organization_website is not False else False
        # TODO DALE We should stop saving organization_twitter_handle without saving a TwitterLinkToOrganization
        if organization_twitter_handle is False or organization_twitter_handle == 'False':
            organization_twitter_handle = ""
        organization_twitter_handle = organization_twitter_handle.strip() if organization_twitter_handle else False
        organization_email = organization_email.strip() if organization_email is not False else False
        organization_facebook = organization_facebook.strip() if organization_facebook is not False else False
        organization_instagram_handle = organization_instagram_handle.strip() \
            if organization_instagram_handle is not False \
            else False
        organization_image = organization_image.strip() if organization_image is not False else False
        organization_type = organization_type.strip() if organization_type is not False else False
        chosen_domain_string = chosen_domain_string.strip() if chosen_domain_string is not False else False
        chosen_domain_string2 = chosen_domain_string2.strip() if chosen_domain_string2 is not False else False
        chosen_domain_string3 = chosen_domain_string3.strip() if chosen_domain_string3 is not False else False
        chosen_google_analytics_tracking_id = chosen_google_analytics_tracking_id.strip() \
            if chosen_google_analytics_tracking_id is not False else False
        chosen_html_verification_string = chosen_html_verification_string.strip() \
            if chosen_html_verification_string is not False else False
        # if isinstance(chosen_ready_introduction_text, str):
        #     chosen_ready_introduction_text = chosen_ready_introduction_text.strip()
        # if isinstance(chosen_ready_introduction_title, str):
        #     chosen_ready_introduction_title = chosen_ready_introduction_title.strip()
        chosen_social_share_description = chosen_social_share_description.strip() \
            if chosen_social_share_description is not False else False
        chosen_subdomain_string = chosen_subdomain_string.strip() if chosen_subdomain_string is not False else False

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
                    results = retrieve_twitter_user_info(
                        twitter_user_id,
                        organization_twitter_handle,
                        twitter_api_counter_manager=twitter_api_counter_manager,
                        parent='parent = update_or_create_organization #1',
                    )
                    if results['success']:
                        twitter_dict = results['twitter_dict']
                        if positive_value_exists(twitter_dict['id']):
                            twitter_user_id = convert_to_int(twitter_dict['id'])
                        if positive_value_exists(twitter_dict['name']):
                            twitter_name = twitter_dict['name']
                            # Use Twitter value if a value for this variable was NOT passed in
                            if not positive_value_exists(organization_name):
                                organization_name = twitter_dict['name']
                        # TODO DALE Look more closely at saving the actual url from twitter (not the Twitter shortcut)
                        if positive_value_exists(twitter_dict['expanded_url']):
                            if not positive_value_exists(organization_website):
                                organization_website = twitter_dict['expanded_url']
                        twitter_followers_count = convert_to_int(twitter_dict['followers_count'])
                        if positive_value_exists(twitter_dict['profile_image_url']):
                            twitter_profile_image_url_https = twitter_dict['profile_image_url']
                        # 2024-01-27 Twitter API v2 doesn't return profile_banner_url anymore
                        # if 'profile_banner_url' in twitter_dict:
                        #     twitter_profile_banner_url_https = twitter_dict['profile_banner_url']
                        # 2024-01-27 Twitter API v2 doesn't return profile_background_image_url_https anymore
                        # twitter_profile_background_image_url_https = \
                        #     twitter_dict['profile_background_image_url_https']
                        twitter_description = twitter_dict['description']
                        twitter_location = twitter_dict['location']

                value_changed = False
                if chosen_domain_string is not False:
                    value_changed = True
                    organization_on_stage.chosen_domain_string = chosen_domain_string
                if chosen_domain_string2 is not False:
                    value_changed = True
                    organization_on_stage.chosen_domain_string2 = chosen_domain_string2
                if chosen_domain_string3 is not False:
                    value_changed = True
                    organization_on_stage.chosen_domain_string3 = chosen_domain_string3
                if chosen_google_analytics_tracking_id is not False:
                    value_changed = True
                    organization_on_stage.chosen_google_analytics_tracking_id = \
                        chosen_google_analytics_tracking_id
                if chosen_html_verification_string is not False:
                    value_changed = True
                    organization_on_stage.chosen_html_verification_string = chosen_html_verification_string
                if chosen_hide_we_vote_logo is not None:
                    value_changed = True
                    organization_on_stage.chosen_hide_we_vote_logo = positive_value_exists(chosen_hide_we_vote_logo)
                if chosen_prevent_sharing_opinions is not None:
                    value_changed = True
                    organization_on_stage.chosen_prevent_sharing_opinions = \
                        positive_value_exists(chosen_prevent_sharing_opinions)
                if chosen_ready_introduction_text is not False:
                    value_changed = True
                    organization_on_stage.chosen_ready_introduction_text = chosen_ready_introduction_text
                if chosen_ready_introduction_title is not False:
                    value_changed = True
                    organization_on_stage.chosen_ready_introduction_title = chosen_ready_introduction_title
                if chosen_social_share_description is not False:
                    value_changed = True
                    organization_on_stage.chosen_social_share_description = chosen_social_share_description
                if chosen_subdomain_string is not False:
                    value_changed = True
                    organization_on_stage.chosen_subdomain_string = chosen_subdomain_string
                if chosen_subscription_plan is not False:
                    value_changed = True
                    organization_on_stage.chosen_subscription_plan = chosen_subscription_plan
                if organization_name is not False:
                    organization_on_stage.organization_name = organization_name
                    organization_on_stage.most_recent_name_update_from_voter_first_and_last = False
                    value_changed = True
                if organization_description is not False:
                    organization_on_stage.organization_description = organization_description
                    value_changed = True
                if organization_website is not False:
                    organization_on_stage.organization_website = organization_website
                    value_changed = True
                if organization_twitter_handle is not False:
                    organization_on_stage.organization_twitter_handle = organization_twitter_handle
                    value_changed = True
                if organization_email is not False:
                    organization_on_stage.organization_email = organization_email
                    value_changed = True
                if organization_facebook is not False:
                    organization_on_stage.organization_facebook = organization_facebook
                    value_changed = True
                if organization_image is not False:
                    organization_on_stage.organization_image = organization_image
                    value_changed = True
                if organization_instagram_handle is not False:
                    value_changed = True
                    organization_on_stage.organization_instagram_handle = organization_instagram_handle
                if organization_type is not False:
                    value_changed = True
                    organization_on_stage.organization_type = organization_type
                if profile_image_type_currently_active is not False:
                    value_changed = True
                    organization_on_stage.profile_image_type_currently_active = profile_image_type_currently_active

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
                        status += "SAVED_WITH_ORG_ID_OR_WE_VOTE_ID "
                    except Exception as e:
                        status += 'organization_on_stage.save() failed to save #1 ' \
                                  '{error} [type: {error_type}] '.format(error=e.message, error_type=type(e))
                else:
                    success = True
                    status += "NO_CHANGES_SAVED_WITH_ORG_ID_OR_WE_VOTE_ID "
            else:
                status += "ORGANIZATION_COULD_NOT_BE_FOUND_WITH_ORG_ID_OR_WE_VOTE_ID "
        else:
            try:
                found_with_status = ''
                organization_on_stage_found = False

                # 3a) FacebookLinkToVoter exists? If not, go to step 3b
                if not organization_on_stage_found and positive_value_exists(facebook_id):
                    facebook_manager = FacebookManager()
                    facebook_results = facebook_manager.retrieve_facebook_link_to_voter(facebook_id, read_only=True)
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
                        results = retrieve_twitter_user_info(
                            twitter_user_id,
                            organization_twitter_handle,
                            twitter_api_counter_manager=twitter_api_counter_manager,
                            parent='parent = update_or_create_organization #2',
                        )
                        if results['success']:
                            twitter_dict = results['twitter_dict']
                            if positive_value_exists(twitter_dict['id']):
                                twitter_user_id = convert_to_int(twitter_dict['id'])
                            if positive_value_exists(twitter_dict['name']):
                                twitter_name = twitter_dict['name']
                                # Use Twitter value if a value for this variable was NOT passed in
                                if not positive_value_exists(organization_name):
                                    organization_name = twitter_dict['name']
                            twitter_followers_count = convert_to_int(twitter_dict['followers_count'])
                            if positive_value_exists(twitter_dict['profile_image_url']):
                                twitter_profile_image_url_https = twitter_dict['profile_image_url']
                            # 2024-01-27 Twitter API v2 doesn't return anymore
                            # if 'profile_banner_url' in twitter_dict:
                            #     twitter_profile_banner_url_https = twitter_dict['profile_banner_url']
                            # twitter_profile_background_image_url_https = \
                            #     twitter_dict['profile_background_image_url_https']
                            twitter_description = twitter_dict['description']
                            twitter_location = twitter_dict['location']

                    value_changed = False
                    if chosen_domain_string is not False:
                        value_changed = True
                        organization_on_stage.chosen_domain_string = chosen_domain_string
                    if chosen_domain_string2 is not False:
                        value_changed = True
                        organization_on_stage.chosen_domain_string2 = chosen_domain_string2
                    if chosen_domain_string3 is not False:
                        value_changed = True
                        organization_on_stage.chosen_domain_string3 = chosen_domain_string3
                    if chosen_google_analytics_tracking_id is not False:
                        value_changed = True
                        organization_on_stage.chosen_google_analytics_tracking_id = \
                            chosen_google_analytics_tracking_id
                    if chosen_html_verification_string is not False:
                        value_changed = True
                        organization_on_stage.chosen_html_verification_string = chosen_html_verification_string
                    if chosen_hide_we_vote_logo is not None:
                        value_changed = True
                        organization_on_stage.chosen_hide_we_vote_logo = chosen_hide_we_vote_logo
                    if chosen_prevent_sharing_opinions is not None:
                        value_changed = True
                        organization_on_stage.chosen_prevent_sharing_opinions = \
                            positive_value_exists(chosen_prevent_sharing_opinions)
                    if chosen_ready_introduction_text is not False:
                        value_changed = True
                        organization_on_stage.chosen_ready_introduction_text = chosen_ready_introduction_text
                    if chosen_ready_introduction_title is not False:
                        value_changed = True
                        organization_on_stage.chosen_ready_introduction_title = chosen_ready_introduction_title
                    if chosen_social_share_description is not False:
                        value_changed = True
                        organization_on_stage.chosen_social_share_description = chosen_social_share_description
                    if chosen_subdomain_string is not False:
                        value_changed = True
                        organization_on_stage.chosen_subdomain_string = chosen_subdomain_string
                    if chosen_subscription_plan is not False:
                        value_changed = True
                        organization_on_stage.chosen_subscription_plan = chosen_subscription_plan
                    if organization_name is not False:
                        organization_on_stage.organization_name = organization_name
                        organization_on_stage.most_recent_name_update_from_voter_first_and_last = False
                        value_changed = True
                    if organization_description is not False:
                        organization_on_stage.organization_description = organization_description
                        value_changed = True
                    if organization_website is not False:
                        organization_on_stage.organization_website = organization_website
                        value_changed = True
                    if organization_twitter_handle is not False:
                        organization_on_stage.organization_twitter_handle = organization_twitter_handle
                        value_changed = True
                    if organization_email is not False:
                        organization_on_stage.organization_email = organization_email
                        value_changed = True
                    if organization_facebook is not False:
                        organization_on_stage.organization_facebook = organization_facebook
                        value_changed = True
                    if organization_image is not False:
                        organization_on_stage.organization_image = organization_image
                        value_changed = True
                    if organization_instagram_handle is not False:
                        value_changed = True
                        organization_on_stage.organization_instagram_handle = organization_instagram_handle
                    if organization_type is not False:
                        value_changed = True
                        organization_on_stage.organization_type = organization_type
                    if profile_image_type_currently_active is not False:
                        value_changed = True
                        organization_on_stage.profile_image_type_currently_active = profile_image_type_currently_active

                    if positive_value_exists(twitter_user_id) or positive_value_exists(twitter_name) \
                            or positive_value_exists(twitter_followers_count) \
                            or positive_value_exists(twitter_profile_image_url_https) \
                            or positive_value_exists(twitter_profile_banner_url_https) \
                            or positive_value_exists(twitter_profile_background_image_url_https) \
                            or positive_value_exists(twitter_description) or positive_value_exists(twitter_location):
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
                            status += found_with_status + " SAVED "
                        except Exception as e:
                            status += "ORGANIZATION_SAVE_FAILED: " + str(e) + " "
                            logger.error("organization_on_stage.save() failed to save #2")

                    else:
                        success = True
                        status += found_with_status + " NO_CHANGES_SAVED "
            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)

        if not organization_on_stage_found:
            try:
                # Now that we have an organization to update, get supplemental data from Twitter if
                # refresh_from_twitter is true
                twitter_user_id = 0
                if positive_value_exists(organization_twitter_handle) and refresh_from_twitter:
                    results = retrieve_twitter_user_info(
                        twitter_user_id,
                        organization_twitter_handle,
                        twitter_api_counter_manager=twitter_api_counter_manager,
                        parent='parent = update_or_create_organization #3',
                    )
                    if results['success']:
                        twitter_dict = results['twitter_dict']
                        if positive_value_exists(twitter_dict['id']):
                            twitter_user_id = convert_to_int(twitter_dict['id'])
                        if positive_value_exists(twitter_dict['name']):
                            twitter_name = twitter_dict['name']
                            # Use Twitter value if a value for this variable was NOT passed in
                            if not positive_value_exists(organization_name):
                                organization_name = twitter_dict['name']
                        twitter_followers_count = convert_to_int(twitter_dict['followers_count'])
                        if positive_value_exists(twitter_dict['profile_image_url']):
                            twitter_profile_image_url_https = twitter_dict['profile_image_url']
                        # 2024-01-27 Twitter API v2 doesn't return anymore
                        # if 'profile_banner_url' in twitter_dict:
                        #     twitter_profile_banner_url_https = twitter_dict['profile_banner_url']
                        # twitter_profile_background_image_url_https = \
                        #     twitter_dict['profile_background_image_url_https']
                        twitter_description = twitter_dict['description']
                        twitter_location = twitter_dict['location']

                if positive_value_exists(organization_type):
                    new_organization_type = organization_type
                else:
                    new_organization_type = UNKNOWN

                # If here, create new organization
                results = Organization.objects.create_organization(
                    organization_name=organization_name,
                    organization_website=organization_website,
                    organization_twitter_handle=organization_twitter_handle,
                    organization_email=organization_email,
                    organization_facebook=organization_facebook,
                    organization_image=organization_image,
                    twitter_id=twitter_user_id,
                    organization_type=new_organization_type)
                if results['success']:
                    new_organization_created = True
                    success = True
                    value_changed = False
                    status += "NEW_ORGANIZATION_CREATED_IN_UPDATE_OR_CREATE "
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

                    if positive_value_exists(organization_instagram_handle):
                        organization_on_stage.organization_instagram_handle = organization_instagram_handle

                    if chosen_domain_string is not False:
                        value_changed = True
                        organization_on_stage.chosen_domain_string = chosen_domain_string
                    if chosen_domain_string2 is not False:
                        value_changed = True
                        organization_on_stage.chosen_domain_string2 = chosen_domain_string2
                    if chosen_domain_string3 is not False:
                        value_changed = True
                        organization_on_stage.chosen_domain_string3 = chosen_domain_string3
                    if chosen_google_analytics_tracking_id is not False:
                        value_changed = True
                        organization_on_stage.chosen_google_analytics_tracking_id = \
                            chosen_google_analytics_tracking_id
                    if chosen_html_verification_string is not False:
                        value_changed = True
                        organization_on_stage.chosen_html_verification_string = chosen_html_verification_string
                    if chosen_hide_we_vote_logo is not None:
                        value_changed = True
                        organization_on_stage.chosen_hide_we_vote_logo = chosen_hide_we_vote_logo
                    if chosen_prevent_sharing_opinions is not None:
                        value_changed = True
                        organization_on_stage.chosen_prevent_sharing_opinions = \
                            positive_value_exists(chosen_prevent_sharing_opinions)
                    if chosen_ready_introduction_text is not False:
                        value_changed = True
                        organization_on_stage.chosen_ready_introduction_text = chosen_ready_introduction_text
                    if chosen_ready_introduction_title is not False:
                        value_changed = True
                        organization_on_stage.chosen_ready_introduction_title = chosen_ready_introduction_title
                    if chosen_social_share_description is not False:
                        value_changed = True
                        organization_on_stage.chosen_social_share_description = chosen_social_share_description
                    if chosen_subdomain_string is not False:
                        value_changed = True
                        organization_on_stage.chosen_subdomain_string = chosen_subdomain_string
                    if chosen_subscription_plan is not False:
                        value_changed = True
                        organization_on_stage.chosen_subscription_plan = chosen_subscription_plan
                    if profile_image_type_currently_active is not False:
                        value_changed = True
                        organization_on_stage.profile_image_type_currently_active = profile_image_type_currently_active

                    if value_changed:
                        try:
                            organization_on_stage.save()
                            status += " EXTRA_VALUES_SAVED "
                        except Exception as e:
                            logger.error("organization_on_stage.save() failed to save #3:" + str(e))
                            status += "organization_on_stage.save() failed to save #3:" + str(e) + " "
                    else:
                        status += " EXTRA_VALUES_NOT_SAVED "

                else:
                    success = False
                    status += results['status']
                    organization_on_stage = Organization

            except Exception as e:
                handle_record_not_saved_exception(e, logger=logger)
                success = False
                status += "NEW_ORGANIZATION_COULD_NOT_BE_CREATED_OR_EXTRA_VALUES_ADDED: " + str(e) + " "
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

    def update_organization_photos(
            self, organization_id=False, organization_we_vote_id=False,
            chosen_favicon_url_https=False,
            chosen_logo_url_https=False,
            chosen_social_share_master_image_url_https=False,
            delete_chosen_favicon=False,
            delete_chosen_logo=False,
            delete_chosen_social_share_master_image=False):
        organization = None
        organization_updated = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        success = False
        status = "ENTERING_UPDATE_ORGANIZATION_PHOTOS "
        values_changed = False
        chosen_favicon_url_https = chosen_favicon_url_https.strip() if chosen_favicon_url_https else False
        chosen_logo_url_https = chosen_logo_url_https.strip() if chosen_logo_url_https else False
        chosen_social_share_master_image_url_https = chosen_social_share_master_image_url_https.strip() \
            if chosen_social_share_master_image_url_https else False

        if not positive_value_exists(chosen_favicon_url_https) \
                and not positive_value_exists(chosen_logo_url_https) \
                and not positive_value_exists(chosen_social_share_master_image_url_https) \
                and not positive_value_exists(delete_chosen_favicon) \
                and not positive_value_exists(delete_chosen_logo) \
                and not positive_value_exists(delete_chosen_social_share_master_image):
            status += "NO_VALUES_TO_SAVE_OR_DELETE "
            results = {
                'success':                  success,
                'status':                   status,
                'DoesNotExist':             exception_does_not_exist,
                'MultipleObjectsReturned':  exception_multiple_object_returned,
                'organization':             None,
                'organization_updated':     organization_updated,
            }
            return results

        organization_found = False
        if positive_value_exists(organization_id):
            results = self.retrieve_organization_from_id(organization_id)
            if results['organization_found']:
                organization_found = True
                organization = results['organization']
        elif positive_value_exists(organization_we_vote_id):
            results = self.retrieve_organization_from_we_vote_id(organization_we_vote_id)
            if results['organization_found']:
                organization_found = True
                organization = results['organization']

        if organization_found:
            if chosen_favicon_url_https:
                organization.chosen_favicon_url_https = str(chosen_favicon_url_https)
                values_changed = True
            elif delete_chosen_favicon:
                organization.chosen_favicon_url_https = None
                values_changed = True
            if chosen_logo_url_https:
                organization.chosen_logo_url_https = str(chosen_logo_url_https)
                values_changed = True
            elif delete_chosen_logo:
                organization.chosen_logo_url_https = None
                values_changed = True
            if chosen_social_share_master_image_url_https:
                organization.chosen_social_share_master_image_url_https = \
                    str(chosen_social_share_master_image_url_https)
                values_changed = True
            elif delete_chosen_social_share_master_image:
                organization.chosen_social_share_master_image_url_https = None
                values_changed = True
            if values_changed:
                organization.save()
                organization_updated = True
                success = True
                status += "SAVED_ORG_PHOTOS "
            else:
                success = True
                status += "NO_CHANGES_SAVED_TO_ORG_PHOTOS "

        results = {
            'success':                  success,
            'status':                   status,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'organization':             organization,
            'organization_updated':     organization_updated,
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

    def update_organization_twitter_details(
            self,
            organization,
            twitter_dict,
            cached_twitter_profile_image_url_https=False,
            cached_twitter_profile_background_image_url_https=False,
            cached_twitter_profile_banner_url_https=False,
            we_vote_hosted_profile_image_url_large=False,
            we_vote_hosted_profile_image_url_medium=False,
            we_vote_hosted_profile_image_url_tiny=False):
        """
        Update an organization entry with details retrieved from the Twitter API.
        See also newer save_fresh_organization_twitter_details.
        """
        success = False
        status = "ENTERING_UPDATE_ORGANIZATION_TWITTER_DETAILS "
        values_changed = False

        # TODO DALE We should stop saving organization_twitter_handle without saving a TwitterLinkToOrganization
        if organization:
            if 'id' in twitter_dict and positive_value_exists(twitter_dict['id']):
                if convert_to_int(twitter_dict['id']) != organization.twitter_user_id:
                    organization.twitter_user_id = convert_to_int(twitter_dict['id'])
                    values_changed = True
            if 'username' in twitter_dict and positive_value_exists(twitter_dict['username']):
                incoming_twitter_screen_name = str(twitter_dict['username'])
                if incoming_twitter_screen_name is False or incoming_twitter_screen_name == 'False':
                    incoming_twitter_screen_name = ""
                organization_twitter_handle = str(organization.organization_twitter_handle)
                if organization_twitter_handle is False or organization_twitter_handle == 'False':
                    organization_twitter_handle = ""
                if incoming_twitter_screen_name.lower() != organization_twitter_handle.lower():
                    organization.organization_twitter_handle = twitter_dict['username']
                    values_changed = True
            if 'name' in twitter_dict and positive_value_exists(twitter_dict['name']):
                if twitter_dict['name'] != organization.twitter_name:
                    organization.twitter_name = twitter_dict['name']
                    values_changed = True
                if not positive_value_exists(organization.organization_name):
                    organization.organization_name = twitter_dict['name']
            if 'followers_count' in twitter_dict and positive_value_exists(twitter_dict['followers_count']):
                if convert_to_int(twitter_dict['followers_count']) != organization.twitter_followers_count:
                    organization.twitter_followers_count = convert_to_int(twitter_dict['followers_count'])
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_image_url_https):
                organization.twitter_profile_image_url_https = cached_twitter_profile_image_url_https
                values_changed = True
            elif 'profile_image_url' in twitter_dict and positive_value_exists(
                    twitter_dict['profile_image_url']):
                if twitter_dict['profile_image_url'] != organization.twitter_profile_image_url_https:
                    organization.twitter_profile_image_url_https = twitter_dict['profile_image_url']
                    values_changed = True

            if positive_value_exists(cached_twitter_profile_banner_url_https):
                organization.twitter_profile_banner_url_https = cached_twitter_profile_banner_url_https
                values_changed = True
            # 2024-01-27 Twitter API v2 doesn't return profile_banner_url anymore
            # elif 'profile_banner_url' in twitter_dict and positive_value_exists(twitter_dict['profile_banner_url']):
            #     if twitter_dict['profile_banner_url'] != organization.twitter_profile_banner_url_https:
            #         organization.twitter_profile_banner_url_https = twitter_dict['profile_banner_url']
            #         values_changed = True

            if positive_value_exists(cached_twitter_profile_background_image_url_https):
                organization.twitter_profile_background_image_url_https = \
                    cached_twitter_profile_background_image_url_https
                values_changed = True
            # 2024-01-27 Twitter API v2 doesn't return profile_background_image_url_https anymore
            # elif 'profile_background_image_url_https' in twitter_dict and positive_value_exists(
            #         twitter_dict['profile_background_image_url_https']):
            #     if twitter_dict['profile_background_image_url_https'] != \
            #             organization.twitter_profile_background_image_url_https:
            #         organization.twitter_profile_background_image_url_https = \
            #             twitter_dict['profile_background_image_url_https']
            #         values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_large):
                organization.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_medium):
                organization.we_vote_hosted_profile_image_url_medium = we_vote_hosted_profile_image_url_medium
                values_changed = True
            if positive_value_exists(we_vote_hosted_profile_image_url_tiny):
                organization.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                values_changed = True

            if 'description' in twitter_dict:  # No value required to update description (so we can clear out)
                if twitter_dict['description'] != organization.twitter_description:
                    organization.twitter_description = twitter_dict['description']
                    values_changed = True
            if 'location' in twitter_dict:  # No value required to update location (so we can clear out)
                if twitter_dict['location'] != organization.twitter_location:
                    organization.twitter_location = twitter_dict['location']
                    values_changed = True

            if values_changed:
                organization.save()
                success = True
                status += "SAVED_ORG_TWITTER_DETAILS "
            else:
                success = True
                status += "NO_CHANGES_SAVED_TO_ORG_TWITTER_DETAILS "

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
            # Steve Aug 17, 2021 -- this clears the saved image if it came from Facebook, so I removed it.
            # organization.we_vote_hosted_profile_image_url_large = ''
            # organization.we_vote_hosted_profile_image_url_medium = ''
            # organization.we_vote_hosted_profile_image_url_tiny = ''
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
    A class for working with lists of endorsers
    """

    def organization_search_find_any_possibilities(self, organization_name='', organization_twitter_handle='',
                                                   organization_website='', organization_email='',
                                                   organization_facebook='', organization_search_term='',
                                                   twitter_handle_list='', facebook_page_list='',
                                                   exact_match=False):
        """
        We want to find *any* possible organization that includes any of the search terms
        We do "OR" across the incoming fields like name, twitter_handle, website, etc.
        We do "AND" with multiple words coming in for organization_search_term
        :param organization_name:
        :param organization_twitter_handle:
        :param organization_website:
        :param organization_email:
        :param organization_facebook:
        :param organization_search_term:
        :param twitter_handle_list:
        :param facebook_page_list:
        :param exact_match:
        :return:
        """
        organization_list_for_json = {}
        if positive_value_exists(organization_search_term):
            organization_search_term_array = organization_search_term.split()
        else:
            organization_search_term_array = []
        try:
            filters = []
            and_filters = []
            organization_list_for_json = []
            organization_objects_list = []
            if positive_value_exists(organization_search_term):
                for search_term in organization_search_term_array:
                    if positive_value_exists(exact_match):
                        organization_twitter_search = extract_twitter_handle_from_text_string(search_term)
                        new_filter = Q(organization_name__iexact=search_term) | \
                            Q(organization_website__iexact=search_term) | \
                            Q(organization_email__iexact=search_term) | \
                            Q(organization_facebook__iexact=search_term) | \
                            Q(organization_twitter_handle__iexact=organization_twitter_search)
                        and_filters.append(new_filter)
                    else:
                        organization_twitter_search = extract_twitter_handle_from_text_string(search_term)
                        new_filter = Q(organization_name__icontains=search_term) | \
                            Q(organization_website__icontains=search_term) | \
                            Q(organization_email__icontains=search_term) | \
                            Q(organization_facebook__icontains=search_term) | \
                            Q(organization_twitter_handle__icontains=organization_twitter_search)
                        and_filters.append(new_filter)

            if positive_value_exists(organization_name):
                if positive_value_exists(exact_match):
                    new_filter = Q(organization_name__iexact=organization_name)
                else:
                    new_filter = Q(organization_name__icontains=organization_name)
                filters.append(new_filter)

            # The master organization twitter_handle data is in TwitterLinkToOrganization, but we try to keep
            # organization_twitter_handle up-to-date for rapid searches like this.
            if positive_value_exists(organization_twitter_handle):
                organization_twitter_handle2 = extract_twitter_handle_from_text_string(organization_twitter_handle)
                if positive_value_exists(exact_match):
                    new_filter = Q(organization_twitter_handle__iexact=organization_twitter_handle2)
                else:
                    new_filter = Q(organization_twitter_handle__icontains=organization_twitter_handle2)
                filters.append(new_filter)

            if positive_value_exists(twitter_handle_list):
                for one_twitter_handle in twitter_handle_list:
                    one_twitter_handle2 = extract_twitter_handle_from_text_string(one_twitter_handle)
                    if positive_value_exists(exact_match):
                        new_filter = Q(organization_twitter_handle__iexact=one_twitter_handle2)
                    else:
                        new_filter = Q(organization_twitter_handle__icontains=one_twitter_handle2)
                    filters.append(new_filter)

            if positive_value_exists(facebook_page_list):
                for one_facebook_page in facebook_page_list:
                    one_facebook_page2 = extract_twitter_handle_from_text_string(one_facebook_page)
                    if positive_value_exists(exact_match):
                        new_filter = Q(organization_facebook__iexact=one_facebook_page2)
                    else:
                        new_filter = Q(organization_facebook__icontains=one_facebook_page2)
                    filters.append(new_filter)

            if positive_value_exists(organization_website):
                if positive_value_exists(exact_match):
                    new_filter = Q(organization_website__iexact=organization_website)
                else:
                    new_filter = Q(organization_website__icontains=organization_website)
                filters.append(new_filter)

            if positive_value_exists(organization_email):
                if positive_value_exists(exact_match):
                    new_filter = Q(organization_email__iexact=organization_email)
                else:
                    new_filter = Q(organization_email__icontains=organization_email)
                filters.append(new_filter)

            if positive_value_exists(organization_facebook):
                if positive_value_exists(exact_match):
                    new_filter = Q(organization_facebook__iexact=organization_facebook)
                else:
                    new_filter = Q(organization_facebook__icontains=organization_facebook)
                filters.append(new_filter)

            organization_query = Organization.objects.all()
            # "OR" filters
            or_filters_found = False
            if len(filters) > 0:
                or_filters_found = True
                final_filters = filters.pop()
                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                organization_query = organization_query.filter(final_filters)
            # "AND" filters
            and_filters_found = False
            if len(and_filters) > 0:
                and_filters_found = True
                final_and_filters = and_filters.pop()
                # ...and "AND" the remaining items in the list
                for item in and_filters:
                    final_and_filters &= item
                organization_query = organization_query.filter(final_and_filters)

            if or_filters_found or and_filters_found:
                organization_query = organization_query[:250]
                organization_objects_list = list(organization_query)

            if len(organization_objects_list):
                organizations_found = True
                status = 'ORGANIZATIONS_RETRIEVED '
                for organization in organization_objects_list:
                    one_organization_json = {
                        'organization_id': organization.id,
                        'organization_we_vote_id': organization.we_vote_id,
                        'organization_name':
                            organization.organization_name
                            if positive_value_exists(organization.organization_name) else '',
                        'organization_type':
                            organization.organization_type
                            if positive_value_exists(organization.organization_type) else '',
                        'organization_twitter_description':
                            organization.twitter_description
                            if positive_value_exists(organization.twitter_description) and
                            len(organization.twitter_description) > 1 else '',
                        'organization_twitter_followers_count':
                            organization.twitter_followers_count
                            if positive_value_exists(organization.twitter_followers_count) else 0,
                        'organization_website':
                            organization.organization_website
                            if positive_value_exists(organization.organization_website) else '',
                        'organization_twitter_handle':
                            organization.organization_twitter_handle
                            if positive_value_exists(organization.organization_twitter_handle) else '',
                        'organization_email':
                            organization.organization_email
                            if positive_value_exists(organization.organization_email) else '',
                        'organization_facebook':
                            organization.organization_facebook
                            if positive_value_exists(organization.organization_facebook) else '',
                        'organization_photo_url_medium': organization.we_vote_hosted_profile_image_url_medium,
                        'organization_photo_url_tiny': organization.we_vote_hosted_profile_image_url_tiny,
                    }
                    organization_list_for_json.append(one_organization_json)
            else:
                organizations_found = False
                status = 'NO_ORGANIZATIONS_RETRIEVED '
            success = True
        except Organization.DoesNotExist:
            # No organizations found. Not a problem.
            organizations_found = False
            status = 'NO_ORGANIZATIONS_FOUND_DoesNotExist '
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

                # Loop through all the organizations that have any of these fields set:
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

    @staticmethod
    def retrieve_public_organizations_for_upcoming_elections(
            limit_to_this_state_code="",
            return_list_of_objects=False,
            super_light_organization_list=False,
            candidate_we_vote_id_to_include="",
    ):
        """
        This function is used for our endorsements scraper.
        :param limit_to_this_state_code:
        :param return_list_of_objects:
        :param super_light_organization_list:
        :param candidate_we_vote_id_to_include:
        :return:
        """
        status = ""
        organization_list_objects = []
        organization_list_light = []
        organization_list_found = False

        try:
            organization_queryset = Organization.objects.using('readonly').all()
            organization_queryset = organization_queryset.filter(
                organization_type__in=ORGANIZATION_TYPE_CHOICES_IN_PUBLIC_SPHERE)
            organization_queryset = organization_queryset.exclude(
                organization_name__in=ORGANIZATION_NAMES_TO_EXCLUDE_FROM_SCRAPER)
            if positive_value_exists(limit_to_this_state_code):
                organization_queryset = organization_queryset.filter(state_served_code__iexact=limit_to_this_state_code)
            organization_list_objects = list(organization_queryset)

            if len(organization_list_objects):
                organization_list_found = True
                status += 'PUBLIC_ORGANIZATIONS_RETRIEVED '
                success = True
            else:
                status += 'NO_PUBLIC_ORGANIZATIONS_RETRIEVED '
                success = True
        except Organization.DoesNotExist:
            # No candidates found. Not a problem.
            status = 'NO_PUBLIC_ORGANIZATIONS_FOUND_DoesNotExist '
            organization_list_objects = []
            success = True
        except Exception as e:
            handle_exception(e, logger=logger)
            status = 'FAILED retrieve_public_organizations_for_upcoming_elections ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        if organization_list_found:
            for organization in organization_list_objects:
                if positive_value_exists(super_light_organization_list):
                    one_organization = {
                        'name':         organization.organization_name,
                        'we_vote_id':   organization.we_vote_id,
                    }
                else:
                    if organization.organization_name == 'The Club for Growth':
                        found_it = True

                    alternate_names = organization.display_alternate_names_list()
                    one_organization = {
                        'ballot_item_display_name':     '',
                        'alternate_names':              alternate_names,
                        'ballot_item_website':          '',
                        'candidate_contact_form_url':   '',
                        'candidate_we_vote_id':         candidate_we_vote_id_to_include,
                        'google_civic_election_id':     '',
                        'office_we_vote_id':            '',
                        'measure_we_vote_id':           '',
                        'more_info_url':                '',
                        'organization_name':            organization.organization_name,
                        'organization_website':         organization.organization_website,
                        'organization_we_vote_id':      organization.we_vote_id,
                    }
                organization_list_light.append(one_organization)

        results = {
            'success':                  success,
            'status':                   status,
            'organization_list_found':  organization_list_found,
            'organization_list_objects': organization_list_objects if return_list_of_objects else [],
            'organization_list_light':  organization_list_light,
        }
        return results

    def retrieve_organizations_from_twitter_handle(self, twitter_handle='', read_only=True):
        keep_looking_for_duplicates = True
        organization_list = []
        organization_list_found = False
        organization_found = False
        multiple_entries_found = False
        organization = Organization()
        success = True
        status = ""
        twitter_handle_filtered = extract_twitter_handle_from_text_string(twitter_handle)

        if positive_value_exists(twitter_handle_filtered):
            # See if we have linked an organization to this Twitter handle
            twitter_user_manager = TwitterUserManager()
            results = twitter_user_manager.retrieve_twitter_link_to_organization_from_twitter_handle(
                twitter_handle_filtered, read_only=True)
            if 'twitter_link_to_organization_found' in results and results['twitter_link_to_organization_found']:
                twitter_link_to_organization = results['twitter_link_to_organization']
                organization_manager = OrganizationManager()
                organization_results = organization_manager.retrieve_organization_from_we_vote_id(
                    twitter_link_to_organization.organization_we_vote_id, read_only=True)
                if organization_results['organization_found']:
                    organization = organization_results['organization']
                    organization_found = True
                    keep_looking_for_duplicates = False
                    organization_list_found = True
                    organization_list.append(organization)
                    status += "ORGANIZATION_FOUND_FROM_TWITTER_LINK_TO_ORGANIZATION "
                else:
                    keep_looking_for_duplicates = True
                    # Heal the data -- the organization is missing, so we should delete the Twitter link
                    twitter_id = 0
                    delete_results = twitter_user_manager.delete_twitter_link_to_organization(
                        twitter_id, twitter_link_to_organization.organization_we_vote_id)

                    if delete_results['twitter_link_to_organization_deleted']:
                        organization_list_manager = OrganizationListManager()
                        repair_results = organization_list_manager.repair_twitter_related_organization_caching(
                            twitter_link_to_organization.twitter_id)
                        status += repair_results['status']

                    organization_list_found = False
                    status += "ORGANIZATION_NOT_FOUND_FROM_TWITTER_LINK_TO_ORGANIZATION-DELETED_BAD_LINK "
            else:
                keep_looking_for_duplicates = True

            if keep_looking_for_duplicates:
                try:
                    if positive_value_exists(read_only):
                        organization_queryset = Organization.objects.using('readonly').all()
                    else:
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
                    else:
                        status += 'NO_ORGANIZATIONS_RETRIEVED_FROM_TWITTER_HANDLE '
                except Organization.DoesNotExist:
                    # No organizations found. Not a problem.
                    status += 'NO_ORGANIZATIONS_FOUND_FROM_TWITTER_HANDLE_DoesNotExist'
                    organization_list = []
                    multiple_entries_found = False
                except Exception as e:
                    handle_exception(e, logger=logger,
                                     exception_message="exception thrown in retrieve_organizations_"
                                                       "from_non_unique_identifiers")
                    status += 'FAILED retrieve_organizations_from_twitter_handle ' \
                              '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                    success = False
                    organization_list = []
                    multiple_entries_found = False

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

    def retrieve_organizations_from_organization_name(self, organization_name=''):
        organization_list = []
        organization_list_found = False
        organization_found = False
        multiple_entries_found = False
        organization = Organization()
        success = False
        status = ""

        if positive_value_exists(organization_name):
            try:
                organization_queryset = Organization.objects.all()
                organization_queryset = organization_queryset.filter(
                    organization_name__iexact=organization_name)

                organization_list = list(organization_queryset)

                if len(organization_list):
                    if len(organization_list) == 1:
                        status += 'ORGANIZATION_RETRIEVED_BY_NAME '
                        organization_list_found = True
                        organization_found = True
                        multiple_entries_found = False
                        organization = organization_list[0]
                        keep_looking_for_duplicates = False
                    else:
                        organization_list_found = True
                        multiple_entries_found = True
                        status += 'ORGANIZATIONS_RETRIEVED_BY_NAME '
                        success = True
                else:
                    status += 'NO_ORGANIZATIONS_RETRIEVED_BY_NAME '
                    success = True
            except Organization.DoesNotExist:
                # No organizations found. Not a problem.
                status += 'NO_ORGANIZATIONS_FOUND_BY_NAME_DoesNotExist'
                organization_list = []
                multiple_entries_found = False
                success = True
            except Exception as e:
                status = 'FAILED retrieve_organizations_from_organization_name ' \
                         '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
                success = False
                organization_list = []
                multiple_entries_found = False

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

    def retrieve_organizations_from_non_unique_identifiers(
            self,
            ignore_we_vote_id_list=[],
            organization_name='',
            read_only=True,
            twitter_handle_list=[],
            vote_smart_id=0):
        filters = []
        organization = None
        organization_found = False
        organization_list = []
        organization_list_found = False
        success = True

        try:
            if positive_value_exists(read_only):
                queryset = Organization.objects.using('readonly').all()
            else:
                queryset = Organization.objects.all()

            twitter_filters = []
            for one_twitter_handle in twitter_handle_list:
                one_twitter_handle_cleaned = extract_twitter_handle_from_text_string(one_twitter_handle)
                new_filter = (
                    Q(organization_twitter_handle__iexact=one_twitter_handle_cleaned)
                )
                twitter_filters.append(new_filter)

            # Add the first query
            final_filters = twitter_filters.pop()
            # ...and "OR" the remaining items in the list
            for item in twitter_filters:
                final_filters |= item

            queryset = queryset.filter(final_filters)

            # Ignore entries with we_vote_id coming in from master server
            if positive_value_exists(len(ignore_we_vote_id_list)):
                queryset = queryset.filter(~Q(we_vote_id__in=ignore_we_vote_id_list))

            # We want to find organizations with *any* of these values
            if positive_value_exists(organization_name):
                new_filter = Q(organization_name__iexact=organization_name)
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

                queryset = queryset.filter(final_filters)

            organization_list = list(queryset)

            if len(organization_list) > 0:
                status = 'DUPLICATE_ORGANIZATIONS_RETRIEVED'
                if len(organization_list) == 1:
                    organization = organization_list[0]
                    organization_found = True
                else:
                    organization_list_found = True
            else:
                status = 'NO_DUPLICATE_ORGANIZATIONS_RETRIEVED'
        except Exception as e:
            handle_exception(e, logger=logger,
                             exception_message="exception thrown in retrieve_organizations_from_non_unique_identifiers")
            status = 'FAILED retrieve_organizations_from_non_unique_identifiers ' \
                     '{error} [type: {error_type}]'.format(error=e, error_type=type(e))
            success = False

        results = {
            'success':                  success,
            'status':                   status,
            'organization':             organization,
            'organization_found':       organization_found,
            'organization_list':        organization_list,
            'organization_list_found':  organization_list_found,
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
    MultipleObjectsReturned = None
    DoesNotExist = None
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=True, db_index=True)
    organization_name = models.CharField(
        verbose_name="organization name", max_length=255, null=False, blank=False)
    most_recent_name_update_from_voter_first_and_last = models.BooleanField(default=False)
    organization_website = models.TextField(verbose_name='url of the endorsing organization', null=True)
    organization_email = models.EmailField(
        verbose_name='organization contact email address', max_length=255, unique=False, null=True, blank=True)
    organization_contact_form_url = models.TextField(verbose_name='url of the contact us form', null=True)
    organization_contact_name = models.CharField(max_length=255, null=True, unique=False)
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
    politician_we_vote_id = models.CharField(max_length=255, null=True, blank=True)

    # Facebook session information
    facebook_id = models.BigIntegerField(verbose_name="facebook big integer id", null=True, blank=True)
    facebook_email = models.EmailField(verbose_name='facebook email address', max_length=255, unique=False,
                                       null=True, blank=True)
    organization_facebook = models.URLField(blank=True, null=True)  # facebook_url
    fb_username = models.CharField(unique=True, max_length=50, validators=[alphanumeric], null=True)
    facebook_profile_image_url_https = models.TextField(
        verbose_name='url of image from facebook', blank=True, null=True)
    facebook_background_image_url_https = models.TextField(
        verbose_name='url of cover image from facebook', blank=True, null=True)
    facebook_photo_url = models.TextField(blank=True, null=True)
    facebook_photo_url_is_placeholder = models.BooleanField(default=False)
    facebook_url_is_broken = models.BooleanField(default=False)

    # Twitter information
    twitter_user_id = models.BigIntegerField(verbose_name="twitter id", null=True, blank=True)
    organization_twitter_handle = models.CharField(
        verbose_name='organization twitter username', max_length=255, null=True, unique=False)
    # organization_twitter_handle2 = models.CharField(
    #     verbose_name='organization twitter screen_name2', max_length=255, null=True, unique=False)
    organization_twitter_updates_failing = models.BooleanField(default=False)
    twitter_handle_updates_failing = models.BooleanField(default=False)
    twitter_handle2_updates_failing = models.BooleanField(default=False)
    twitter_name = models.CharField(
        verbose_name="org name from twitter", max_length=255, null=True, blank=True)
    twitter_location = models.CharField(
        verbose_name="org location from twitter", max_length=255, null=True, blank=True)
    twitter_followers_count = models.IntegerField(verbose_name="number of twitter followers",
                                                  null=False, blank=True, default=0)
    twitter_profile_image_url_https = models.TextField(
        verbose_name='url of user logo from twitter', blank=True, null=True)
    twitter_profile_background_image_url_https = models.TextField(
        verbose_name='tile-able background from twitter', blank=True, null=True)
    twitter_profile_banner_url_https = models.TextField(
        verbose_name='profile banner image from twitter', blank=True, null=True)
    twitter_description = models.CharField(verbose_name="Text description of this organization from twitter.",
                                           max_length=255, null=True, blank=True)

    # Instagram
    organization_instagram_handle = models.CharField(
        verbose_name='organization instagram username', max_length=255, null=True, unique=False)
    instagram_followers_count = models.IntegerField(null=True, blank=True)

    # Which organization image is currently active?
    profile_image_type_currently_active = models.CharField(
        max_length=11, choices=PROFILE_IMAGE_TYPE_CURRENTLY_ACTIVE_CHOICES, default=PROFILE_IMAGE_TYPE_UNKNOWN)
    # Image from Facebook, cached on We Vote's servers. See also facebook_profile_image_url_https.
    we_vote_hosted_profile_facebook_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_facebook_image_url_tiny = models.TextField(blank=True, null=True)
    # Image from Twitter, cached on We Vote's servers. See master twitter_profile_image_url_https.
    we_vote_hosted_profile_twitter_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_twitter_image_url_tiny = models.TextField(blank=True, null=True)
    # Image uploaded to We Vote's servers.
    we_vote_hosted_profile_uploaded_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_uploaded_image_url_tiny = models.TextField(blank=True, null=True)
    # Image from Vote USA, cached on We Vote's servers. See master vote_usa_profile_image_url_https.
    we_vote_hosted_profile_vote_usa_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_vote_usa_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_vote_usa_image_url_tiny = models.TextField(blank=True, null=True)
    # Image we are using as the profile photo (could be sourced from Twitter, Facebook, etc.)
    we_vote_hosted_profile_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)

    # organization_wikipedia = models.URLField(blank=True, null=True)  # wikipedia_url
    wikipedia_page_id = models.BigIntegerField(verbose_name="pageid", null=True, blank=True)
    wikipedia_page_title = models.CharField(
        verbose_name="Page title on Wikipedia", max_length=255, null=True, blank=True)
    wikipedia_thumbnail_url = models.TextField(
        verbose_name='url of wikipedia logo thumbnail', blank=True, null=True)
    wikipedia_thumbnail_width = models.IntegerField(verbose_name="width of photo", null=True, blank=True)
    wikipedia_thumbnail_height = models.IntegerField(verbose_name="height of photo", null=True, blank=True)
    wikipedia_photo_url = models.TextField(
        verbose_name='url of wikipedia logo', blank=True, null=True)
    wikipedia_url = models.TextField(null=True)

    ballotpedia_page_title = models.CharField(
        verbose_name="Page title on Ballotpedia", max_length=255, null=True, blank=True)
    ballotpedia_photo_url = models.TextField(
        verbose_name='url of ballotpedia logo', blank=True, null=True)

    issue_analysis_done = models.BooleanField(default=False)
    issue_analysis_admin_notes = models.TextField(verbose_name="we vote admin notes", null=True, blank=True)

    organization_type = models.CharField(
        verbose_name="type of org", max_length=2, choices=ORGANIZATION_TYPE_CHOICES, default=UNKNOWN)
    date_last_changed = models.DateTimeField(null=True, auto_now=True)

    chosen_about_organization_external_url = models.TextField(blank=True, null=True)
    chosen_domain_type_is_campaign = models.BooleanField(default=False)
    # This is the domain name the client has configured for their We Vote configured site
    chosen_domain_string = models.CharField(
        verbose_name="client domain name for we vote site", max_length=255, null=True, blank=True, db_index=True)
    chosen_domain_string2 = models.CharField(max_length=255, null=True, blank=True, db_index=True)  # Alternate ex/ www
    chosen_domain_string3 = models.CharField(max_length=255, null=True, blank=True, db_index=True)  # Another alternate
    chosen_favicon_url_https = models.TextField(
        verbose_name='url of client favicon', blank=True, null=True)
    chosen_google_analytics_tracking_id = models.CharField(max_length=255, null=True, blank=True)
    chosen_html_verification_string = models.CharField(max_length=255, null=True, blank=True)
    # Set to True to hide We Vote logo
    chosen_hide_we_vote_logo = models.BooleanField(default=False)
    chosen_logo_url_https = models.TextField(
        verbose_name='url of client logo', blank=True, null=True)
    # Client chosen pass code that needs to be sent with organization-focused API calls
    chosen_organization_api_pass_code = models.TextField(null=True, blank=True)
    # For sites managed by 501c3 organizations, we need to prevent voters from sharing their opinions
    chosen_prevent_sharing_opinions = models.BooleanField(default=False)
    # Ready? page title and text
    chosen_ready_introduction_title = models.CharField(max_length=255, null=True, blank=True)
    chosen_ready_introduction_text = models.TextField(null=True, blank=True)
    # Client configured text that will show in index.html
    chosen_social_share_description = models.TextField(null=True, blank=True)
    chosen_social_share_master_image_url_https = models.TextField(
        verbose_name='url of client social share master image', blank=True, null=True)
    chosen_social_share_image_256x256_url_https = models.TextField(
        verbose_name='url of client social share image', blank=True, null=True)
    # This is the subdomain the client has configured for yyy.WeVote.US
    chosen_subdomain_string = models.CharField(
        verbose_name="client we vote subdomain", max_length=255, null=True, blank=True)
    chosen_subscription_plan = models.PositiveIntegerField(verbose_name="number of the plan client chose", default=0)
    # Name added to end of HTML title and used other places throughout private-labeled site
    chosen_website_name = models.CharField(max_length=255, null=True, blank=True)
    # Last date the subscription is paid through ex/ 20200415
    subscription_plan_end_day_text = models.CharField(
        verbose_name="paid through day", max_length=8, null=True, blank=True)
    # subscription_plan_features_active should be replaced by features_provided_bitmap
    subscription_plan_features_active = models.PositiveIntegerField(verbose_name="features that are active", default=0)
    # The cached value of chosen_feature_package in this Organization table will be slave
    # to the chosen_subscription_plan
    chosen_feature_package = models.CharField(
        verbose_name="plan type {FREE, PROFESSIONAL, ENTERPRISE} that is referred to in MasterFeaturePackage",
        max_length=255, null=True, blank=True)
    # These get copied from features_provided_bitmap in MasterFeaturePackage table
    features_provided_bitmap = models.PositiveIntegerField(verbose_name="features that are active", default=0)

    organization_endorsements_api_url = models.TextField(
        verbose_name='endorsements importer url', blank=True, null=True)
    youtube_url = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return str(self.organization_name)

    def display_alternate_names_list(self):
        alternate_names = []
        if self.organization_name and self.organization_name.startswith('The '):
            if len(self.organization_name) > 10:
                # Do not remove "The " from organization names where the word after "The" is shorter than 6 characters
                # because "The Hill" or "The Nation" without the "The" causes "Hill" and "Nation" to show up too often
                alternate_names.append(self.organization_name[len('The '):])
        return alternate_names

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
               we_vote_hosted_profile_image_url_medium=None, we_vote_hosted_profile_image_url_tiny=None,
               state_served_code=None):

        if organization_twitter_handle is False or organization_twitter_handle == 'False':
            organization_twitter_handle = ""

        organization = cls(organization_name=organization_name,
                           organization_website=organization_website,
                           organization_twitter_handle=organization_twitter_handle,
                           organization_email=organization_email,
                           organization_facebook=organization_facebook,
                           organization_image=organization_image,
                           organization_type=organization_type,
                           state_served_code=state_served_code,
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

    # We override the save function, so we can auto-generate we_vote_id
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

    def is_organization(self):
        """
        Parallel to isSpeakerTypeOrganization in WebApp
        :return:
        """
        return self.organization_type in (
            CORPORATION, GROUP, NONPROFIT, NONPROFIT_501C3, NONPROFIT_501C4, NEWS_ORGANIZATION,
            ORGANIZATION, POLITICAL_ACTION_COMMITTEE)

    def is_private_citizen(self):
        # Return True if this person or organization is not in the public sphere
        is_in_public_sphere = self.organization_type in ORGANIZATION_TYPE_CHOICES_IN_PUBLIC_SPHERE
        # CORPORATION,
        # NONPROFIT,
        # NONPROFIT_501C3,
        # NONPROFIT_501C4,
        # NEWS_ORGANIZATION,
        # ORGANIZATION,
        # POLITICAL_ACTION_COMMITTEE,
        # PUBLIC_FIGURE

        return not is_in_public_sphere

    def generate_facebook_link(self):
        if self.organization_facebook:
            if 'http' in self.organization_facebook or 'facebook' in self.organization_facebook:
                return self.organization_facebook
            else:
                return "https://facebook.com/{facebook_page}".format(facebook_page=self.organization_facebook)
        else:
            return ''

    def generate_instagram_link(self):
        if self.organization_instagram_handle:
            return "https://instagram.com/{instagram_handle}/" \
                   "".format(instagram_handle=self.organization_instagram_handle)
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


class OrganizationChangeLog(models.Model):  # OrganizationLogEntry would be another name
    """
    What changes were made, and by whom?
    """
    changed_by_name = models.CharField(max_length=255, default=None, null=True)
    changed_by_voter_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    change_description = models.TextField(null=True, blank=True)
    log_datetime = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)
    organization_we_vote_id = models.CharField(max_length=255, default=None, null=True)
    status = models.TextField(null=True, blank=True)

    def change_description_augmented(self):
        # Issues with smaller integers need to be listed last.
        # If not, 'wv02issue76' gets found when replacing 'wv02issue7' with the name of the issue.
        from issue.models import ACTIVE_ISSUES_DICTIONARY
        issue_we_vote_id_to_name_dictionary = ACTIVE_ISSUES_DICTIONARY
        if self.change_description:
            change_description_augmented = self.change_description
            if 'issue' in change_description_augmented:
                for we_vote_id, issue_name in issue_we_vote_id_to_name_dictionary.items():
                    change_description_augmented = change_description_augmented.replace(
                        we_vote_id,
                        "{issue_name}".format(issue_name=issue_name))
            change_description_augmented = change_description_augmented\
                .replace("ADD", "<span style=\'color: #A9A9A9;\'>ADDED</span><br />")
            change_description_augmented = change_description_augmented\
                .replace("REMOVE", "<span style=\'color: #A9A9A9;\'>REMOVED</span><br />")
            return change_description_augmented
        else:
            return ''


class OrganizationReservedDomain(models.Model):
    MultipleObjectsReturned = None
    objects = None

    def __unicode__(self):
        return "OrganizationReservedDomain"

    # If there is a value, this is the owner
    organization_we_vote_id = models.CharField(max_length=255, null=True, unique=False)

    # One one of the following is expected to be used for each database row
    # Ex/ bestdomain.org
    full_domain_string = models.CharField(
        verbose_name="full domain", max_length=255, null=True, blank=True, unique=True)
    # Ex/ zoom (referring to zoom.wevote.us)
    subdomain_string = models.CharField(
        verbose_name="we vote subdomain", max_length=255, null=True, blank=True, unique=True)


class OrganizationTeamMember(models.Model):
    DoesNotExist = None
    MultipleObjectsReturned = None
    objects = None

    def __unicode__(self):
        return "OrganizationTeamMember"

    organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    can_edit_campaignx_owned_by_organization = models.BooleanField(default=True)
    can_edit_organization = models.BooleanField(default=True)
    can_manage_team_members = models.BooleanField(default=False)
    can_moderate_campaignx_owned_by_organization = models.BooleanField(default=True)
    can_send_updates_for_campaignx_owned_by_organization = models.BooleanField(default=False)
    team_member_name = models.CharField(max_length=255, null=False, blank=False)
    team_member_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    voter_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)
