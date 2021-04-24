# campaign/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception
import json
import string
import wevote_functions.admin
from wevote_functions.functions import generate_random_string, positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_campaignx_integer, fetch_site_unique_id_prefix

logger = wevote_functions.admin.get_logger(__name__)


class CampaignX(models.Model):
    def __unicode__(self):
        return "CampaignX"

    # We call this "CampaignX" since we have some other data objects in We Vote already with "Campaign" in the name
    # These are campaigns anyone can start to gather support or opposition for one or more items on the ballot.
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "camp", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_campaign_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True,
        blank=True, unique=True, db_index=True)
    campaign_description = models.TextField(null=True, blank=True)
    campaign_title = models.CharField(verbose_name="title of campaign", max_length=255, null=False, blank=False)
    # Has not been released for view
    in_draft_mode = models.BooleanField(default=True, db_index=True)
    # Campaign owner allows campaignX to be promoted by We Vote on free home page and elsewhere
    is_ok_to_promote_on_we_vote = models.BooleanField(default=True, db_index=True)
    is_blocked_by_we_vote = models.BooleanField(default=False, db_index=True)
    is_blocked_by_we_vote_reason = models.TextField(null=True, blank=True)
    is_still_active = models.BooleanField(default=True, db_index=True)
    is_victorious = models.BooleanField(default=False, db_index=True)
    politician_starter_list_serialized = models.TextField(null=True, blank=True)
    seo_friendly_path = models.CharField(max_length=255, null=True, unique=True, db_index=True)
    started_by_voter_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    supporters_count = models.PositiveIntegerField(default=0)
    we_vote_hosted_campaign_photo_original_url = models.TextField(blank=True, null=True)
    # Full sized desktop
    we_vote_hosted_campaign_photo_large_url = models.TextField(blank=True, null=True)
    # Maximum size needed for desktop lists
    we_vote_hosted_campaign_photo_medium_url = models.TextField(blank=True, null=True)
    # Maximum size needed for image grids - Stored as "tiny" image
    we_vote_hosted_campaign_photo_small_url = models.TextField(blank=True, null=True)

    # We override the save function so we can auto-generate we_vote_id
    def save(self, *args, **kwargs):
        # Even if this data came from another source we still need a unique we_vote_id
        if self.we_vote_id:
            self.we_vote_id = self.we_vote_id.strip().lower()
        if self.we_vote_id == "" or self.we_vote_id is None:  # If there isn't a value...
            # ...generate a new id
            site_unique_id_prefix = fetch_site_unique_id_prefix()
            next_local_integer = fetch_next_we_vote_id_campaignx_integer()
            # "wv" = We Vote
            # site_unique_id_prefix = a generated (or assigned) unique id for one server running We Vote
            # "camp" = tells us this is a unique id for a CampaignX
            # next_integer = a unique, sequential integer for this server - not necessarily tied to database id
            self.we_vote_id = "wv{site_unique_id_prefix}camp{next_integer}".format(
                site_unique_id_prefix=site_unique_id_prefix,
                next_integer=next_local_integer,
            )
        super(CampaignX, self).save(*args, **kwargs)


class CampaignXListedByOrganization(models.Model):
    """
    An individual or organization can specify a campaign as one they want to list on their private-labeled site.
    This is the link that says "show this campaign on my promotion site".
    """
    def __unicode__(self):
        return "CampaignXListedByOrganization"

    campaignx_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    site_owner_organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    # If a candidate or campaign-starter requests to be included in a private label site:
    listing_requested_by_voter_we_vote_id = \
        models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    # Is this link approved and made visible?
    visible_to_public = models.BooleanField(default=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)


class CampaignXManager(models.Manager):

    def __unicode__(self):
        return "CampaignXManager"

    def fetch_campaignx_supporter_count(self, campaignx_we_vote_id=None):
        status = ""

        try:
            campaignx_queryset = CampaignXSupporter.objects.using('readonly').all()
            campaignx_queryset = campaignx_queryset.filter(campaignx_we_vote_id=campaignx_we_vote_id)
            return campaignx_queryset.count()
        except Exception as e:
            status += "RETRIEVE_CAMPAIGNX_SUPPORTER_LIST_FAILED: " + str(e) + " "

        return 0

    def generate_seo_friendly_path(self, campaignx_we_vote_id='', campaignx_title=None):
        """
        Generate the closest possible SEO friendly path for this campaign. Note that these paths
        are only generated for campaigns which are already published.
        :param campaignx_we_vote_id:
        :param campaignx_title:
        :return:
        """
        final_pathname_string = ''
        pathname_modifier = None
        status = ""

        if not positive_value_exists(campaignx_we_vote_id):
            status += "MISSING_CAMPAIGNX_WE_VOTE_ID "
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        if not campaignx_title:
            status += "MISSING_CAMPAIGN_TITLE "
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        # Generate the ideal path given this title
        try:
            base_pathname_string = slugify(campaignx_title)
        except Exception as e:
            status += 'PROBLEM_WITH_SLUGIFY: ' + str(e) + ' '
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        if not base_pathname_string or not positive_value_exists(len(base_pathname_string)):
            status += "MISSING_BASE_PATHNAME_STRING "
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        # Is that path already stored for this campaign?
        try:
            path_query = CampaignXSEOFriendlyPath.objects.using('readonly').all()
            path_query = path_query.filter(campaignx_we_vote_id=campaignx_we_vote_id)
            path_query = path_query.filter(final_pathname_string__iexact=base_pathname_string)
            match_count = path_query.count()
            if positive_value_exists(match_count):
                status += "PATHNAME_FOUND-OWNED_BY_CAMPAIGNX "
                results = {
                    'seo_friendly_path':            base_pathname_string,
                    'seo_friendly_path_created':    False,
                    'seo_friendly_path_found':      True,
                    'status':                       status,
                    'success':                      True,
                }
                return results
        except Exception as e:
            status += 'PROBLEM_QUERYING_CAMPAIGNX_SEO_FRIENDLY_PATH_TABLE1 {error} [type: {error_type}] ' \
                      ''.format(error=str(e), error_type=type(e))
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        # Is it being used by any campaign?
        owned_by_another_campaignx = False
        try:
            path_query = CampaignXSEOFriendlyPath.objects.using('readonly').all()
            path_query = path_query.filter(final_pathname_string__iexact=base_pathname_string)
            match_count = path_query.count()
            if positive_value_exists(match_count):
                owned_by_another_campaignx = True
                status += "PATHNAME_FOUND-OWNED_BY_ANOTHER_CAMPAIGNX "
        except Exception as e:
            status += 'PROBLEM_QUERYING_CAMPAIGNX_SEO_FRIENDLY_PATH_TABLE2 {error} [type: {error_type}] ' \
                      ''.format(error=str(e), error_type=type(e))
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        if not owned_by_another_campaignx:
            # Double-check that we don't have a reserved entry already in the OrganizationReservedDomain table
            try:
                path_query = CampaignX.objects.using('readonly').all()
                path_query = path_query.filter(seo_friendly_path__iexact=base_pathname_string)
                match_count = path_query.count()
                if positive_value_exists(match_count):
                    owned_by_another_campaignx = True
                    status += "PATHNAME_FOUND_IN_ANOTHER_CAMPAIGNX "
            except Exception as e:
                status += 'PROBLEM_QUERYING_CAMPAIGNX_SEO_FRIENDLY_PATH_TABLE3 {error} [type: {error_type}] ' \
                          ''.format(error=str(e), error_type=type(e))
                results = {
                    'seo_friendly_path':            final_pathname_string,
                    'seo_friendly_path_created':    False,
                    'seo_friendly_path_found':      False,
                    'status':                       status,
                    'success':                      False,
                }
                return results

        if not owned_by_another_campaignx:
            final_pathname_string = base_pathname_string
        else:
            # If already being used, add a random string on the end, verify not in use, and save
            continue_retrieving = True
            pathname_modifiers_already_reviewed_list = []  # Reset
            safety_valve_count = 0
            while continue_retrieving and safety_valve_count < 1000:
                safety_valve_count += 1
                modifier_safety_valve_count = 0
                while pathname_modifier not in pathname_modifiers_already_reviewed_list:
                    if modifier_safety_valve_count > 50:
                        status += 'CAMPAIGNX_MODIFIER_SAFETY_VALVE_EXCEEDED '
                        results = {
                            'seo_friendly_path':            final_pathname_string,
                            'seo_friendly_path_created':    False,
                            'seo_friendly_path_found':      False,
                            'status':                       status,
                            'success':                      False,
                        }
                        return results
                    modifier_safety_valve_count += 1
                    pathname_modifier = generate_random_string(
                        string_length=4,
                        chars=string.ascii_lowercase + string.digits,
                        remove_confusing_digits=True,
                    )
                final_pathname_string_to_test = "{base_pathname_string}-{pathname_modifier}".format(
                    base_pathname_string=base_pathname_string,
                    pathname_modifier=pathname_modifier)
                try:
                    pathname_modifiers_already_reviewed_list.append(pathname_modifier)
                    path_query = CampaignXSEOFriendlyPath.objects.using('readonly').all()
                    path_query = path_query.filter(final_pathname_string__iexact=final_pathname_string_to_test)
                    match_count = path_query.count()
                    if not positive_value_exists(match_count):
                        try:
                            path_query = CampaignX.objects.using('readonly').all()
                            path_query = path_query.filter(seo_friendly_path__iexact=final_pathname_string_to_test)
                            match_count = path_query.count()
                            if positive_value_exists(match_count):
                                status += "FOUND_IN_ANOTHER_CAMPAIGNX2 "
                            else:
                                continue_retrieving = False
                                final_pathname_string = final_pathname_string_to_test
                                owned_by_another_campaignx = False
                                status += "NO_PATHNAME_COLLISION "
                        except Exception as e:
                            status += 'PROBLEM_QUERYING_CAMPAIGNX_TABLE {error} [type: {error_type}] ' \
                                      ''.format(error=str(e), error_type=type(e))
                            results = {
                                'seo_friendly_path':            final_pathname_string,
                                'seo_friendly_path_created':    False,
                                'seo_friendly_path_found':      False,
                                'status':                       status,
                                'success':                      False,
                            }
                            return results
                except Exception as e:
                    status += 'PROBLEM_QUERYING_CAMPAIGNX_SEO_FRIENDLY_PATH_TABLE4 {error} [type: {error_type}] ' \
                              ''.format(error=str(e), error_type=type(e))
                    results = {
                        'seo_friendly_path':            final_pathname_string,
                        'seo_friendly_path_created':    False,
                        'seo_friendly_path_found':      False,
                        'status':                       status,
                        'success':                      False,
                    }
                    return results

        if owned_by_another_campaignx:
            # We have failed to find a unique URL
            status += 'FAILED_TO_FIND_UNIQUE_URL '
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        if not positive_value_exists(final_pathname_string) or not positive_value_exists(campaignx_we_vote_id):
            # We have failed to generate a unique URL
            status += 'MISSING_REQUIRED_VARIABLE '
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        # Create a new entry
        try:
            campaignx_seo_friendly_path = CampaignXSEOFriendlyPath.objects.create(
                base_pathname_string=base_pathname_string,
                campaign_title=campaignx_title,
                campaignx_we_vote_id=campaignx_we_vote_id,
                final_pathname_string=final_pathname_string,
                pathname_modifier=pathname_modifier,
            )
            seo_friendly_path_created = True
            seo_friendly_path_found = True
            success = True
            status += "CAMPAIGNX_SEO_FRIENDLY_PATH_CREATED "
        except Exception as e:
            status += "CAMPAIGNX_SEO_FRIENDLY_PATH_NOT_CREATED: " + str(e) + " "
            results = {
                'seo_friendly_path':            final_pathname_string,
                'seo_friendly_path_created':    False,
                'seo_friendly_path_found':      False,
                'status':                       status,
                'success':                      False,
            }
            return results

        status += "FINAL_PATHNAME_STRING_GENERATED "
        results = {
            'seo_friendly_path':            final_pathname_string,
            'seo_friendly_path_created':    seo_friendly_path_created,
            'seo_friendly_path_found':      seo_friendly_path_found,
            'status':                       status,
            'success':                      success,
        }
        return results

    def is_voter_campaignx_owner(self, campaignx_we_vote_id='', voter_we_vote_id=''):
        status = ''
        voter_is_campaignx_owner = False

        try:
            campaignx_owner_query = CampaignXOwner.objects.using('readonly').filter(
                campaignx_we_vote_id=campaignx_we_vote_id,
                voter_we_vote_id=voter_we_vote_id)
            voter_is_campaignx_owner = positive_value_exists(campaignx_owner_query.count())
            status += 'VOTER_IS_CAMPAIGNX_OWNER '
        except CampaignXOwner as e:
            status += 'CAMPAIGNX_OWNER_QUERY_FAILED: ' + str(e) + ' '

        return voter_is_campaignx_owner

    def remove_campaignx_owner(self, campaignx_we_vote_id='', voter_we_vote_id=''):
        return

    def remove_campaignx_politicians_from_delete_list(self, campaignx_we_vote_id='', politician_delete_list=''):
        success = True
        status = ''
        campaignx_manager = CampaignXManager()
        campaignx_politician_list = \
            campaignx_manager.retrieve_campaignx_politician_list(campaignx_we_vote_id=campaignx_we_vote_id)

        for campaignx_politician in campaignx_politician_list:
            if campaignx_politician.id in politician_delete_list:
                try:
                    campaignx_politician.delete()
                except Exception as e:
                    status += "DELETE_FAILED: " + str(e) + ' '

        results = {
            'status':                       status,
            'success':                      success,
        }
        return results

    def retrieve_campaignx_as_owner(
            self,
            campaignx_we_vote_id='',
            seo_friendly_path='',
            voter_we_vote_id='',
            read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        campaignx = None
        campaignx_manager = CampaignXManager()
        campaignx_owner_list = []
        seo_friendly_path_list = []
        status = ''
        viewer_is_owner = False

        if positive_value_exists(campaignx_we_vote_id):
            viewer_is_owner = campaignx_manager.is_voter_campaignx_owner(
                campaignx_we_vote_id=campaignx_we_vote_id, voter_we_vote_id=voter_we_vote_id)

        try:
            if positive_value_exists(campaignx_we_vote_id):
                if positive_value_exists(read_only):
                    campaignx = CampaignX.objects.using('readonly').get(we_vote_id=campaignx_we_vote_id)
                else:
                    campaignx = CampaignX.objects.get(we_vote_id=campaignx_we_vote_id)
                campaignx_found = True
                campaignx_we_vote_id = campaignx.we_vote_id
                status += 'CAMPAIGNX_AS_OWNER_FOUND_WITH_WE_VOTE_ID '
                success = True
            elif positive_value_exists(seo_friendly_path):
                if positive_value_exists(read_only):
                    campaignx = CampaignX.objects.using('readonly').get(seo_friendly_path__iexact=seo_friendly_path)
                else:
                    campaignx = CampaignX.objects.get(seo_friendly_path__iexact=seo_friendly_path)
                campaignx_found = True
                campaignx_we_vote_id = campaignx.we_vote_id
                status += 'CAMPAIGNX_AS_OWNER_FOUND_WITH_SEO_FRIENDLY_PATH '
                success = True
            elif positive_value_exists(voter_we_vote_id):
                # If ONLY the voter_we_vote_id is passed in, get the campaign for that voter in draft mode
                if positive_value_exists(read_only):
                    campaignx = CampaignX.objects.using('readonly').get(
                        in_draft_mode=True,
                        started_by_voter_we_vote_id=voter_we_vote_id)
                else:
                    campaignx = CampaignX.objects.get(
                        in_draft_mode=True,
                        started_by_voter_we_vote_id=voter_we_vote_id)
                campaignx_found = True
                campaignx_we_vote_id = campaignx.we_vote_id
                viewer_is_owner = True
                status += 'CAMPAIGNX_AS_OWNER_FOUND_WITH_ORGANIZATION_WE_VOTE_ID-IN_DRAFT_MODE '
                success = True
            else:
                status += 'CAMPAIGNX_AS_OWNER_NOT_FOUND-MISSING_VARIABLES '
                success = False
                campaignx_found = False
        except CampaignX.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            campaignx_found = False
            campaignx_we_vote_id = ''
            exception_multiple_object_returned = True
            status += 'CAMPAIGNX_AS_OWNER_NOT_FOUND_MultipleObjectsReturned '
            success = False
        except CampaignX.DoesNotExist:
            campaignx_found = False
            campaignx_we_vote_id = ''
            exception_does_not_exist = True
            status += 'CAMPAIGNX_AS_OWNER_NOT_FOUND_DoesNotExist '
            success = True

        if positive_value_exists(campaignx_found):
            campaignx_owner_object_list = campaignx_manager.retrieve_campaignx_owner_list(
                campaignx_we_vote_id=campaignx_we_vote_id, viewer_is_owner=viewer_is_owner)

            for campaignx_owner in campaignx_owner_object_list:
                campaignx_owner_organization_name = '' if campaignx_owner.organization_name is None \
                    else campaignx_owner.organization_name
                campaignx_owner_organization_we_vote_id = '' if campaignx_owner.organization_we_vote_id is None \
                    else campaignx_owner.organization_we_vote_id
                campaignx_owner_we_vote_hosted_profile_image_url_tiny = '' \
                    if campaignx_owner.we_vote_hosted_profile_image_url_tiny is None \
                    else campaignx_owner.we_vote_hosted_profile_image_url_tiny
                campaign_owner_dict = {
                    'organization_name':                        campaignx_owner_organization_name,
                    'organization_we_vote_id':                  campaignx_owner_organization_we_vote_id,
                    'feature_this_profile_image':                       campaignx_owner.feature_this_profile_image,
                    'visible_to_public':                        campaignx_owner.visible_to_public,
                    'we_vote_hosted_profile_image_url_tiny':    campaignx_owner_we_vote_hosted_profile_image_url_tiny,
                }
                campaignx_owner_list.append(campaign_owner_dict)

            seo_friendly_path_list = \
                campaignx_manager.retrieve_seo_friendly_path_simple_list(
                    campaignx_we_vote_id=campaignx_we_vote_id)

            # campaignx_politician_object_list = campaignx_manager.retrieve_campaignx_politician_list(
            #     campaignx_we_vote_id=campaignx_we_vote_id)
            #
            # for campaignx_politician in campaignx_politician_object_list:
            #     campaignx_politician_organization_name = '' if campaignx_politician.organization_name is None \
            #         else campaignx_politician.organization_name
            #     campaignx_politician_organization_we_vote_id = '' \
            #         if campaignx_politician.organization_we_vote_id is None \
            #         else campaignx_politician.organization_we_vote_id
            #     campaignx_politician_we_vote_hosted_profile_image_url_tiny = '' \
            #         if campaignx_politician.we_vote_hosted_profile_image_url_tiny is None \
            #         else campaignx_politician.we_vote_hosted_profile_image_url_tiny
            #     campaignx_politician_dict = {
            #         'organization_name':                        campaignx_politician_organization_name,
            #         'organization_we_vote_id':                  campaignx_politician_organization_we_vote_id,
            #         'we_vote_hosted_profile_image_url_tiny':
            #         campaignx_politician_we_vote_hosted_profile_image_url_tiny,
            #         'visible_to_public':                        campaignx_politician.visible_to_public,
            #     }
            #     campaignx_politician_list.append(campaignx_politician_dict)

        results = {
            'status':                       status,
            'success':                      success,
            'campaignx':                    campaignx,
            'campaignx_found':              campaignx_found,
            'campaignx_we_vote_id':         campaignx_we_vote_id,
            'campaignx_owner_list':         campaignx_owner_list,
            'seo_friendly_path_list':       seo_friendly_path_list,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def retrieve_campaignx(self, campaignx_we_vote_id='', seo_friendly_path='', read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        campaignx = None
        campaignx_found = False
        campaignx_manager = CampaignXManager()
        campaignx_owner_list = []
        seo_friendly_path_list = []
        status = ''

        try:
            if positive_value_exists(campaignx_we_vote_id):
                if positive_value_exists(read_only):
                    campaignx = CampaignX.objects.using('readonly').get(we_vote_id=campaignx_we_vote_id)
                else:
                    campaignx = CampaignX.objects.get(we_vote_id=campaignx_we_vote_id)
                campaignx_found = True
                status += 'CAMPAIGNX_FOUND_WITH_WE_VOTE_ID '
                success = True
            elif positive_value_exists(seo_friendly_path):
                if positive_value_exists(read_only):
                    campaignx = CampaignX.objects.using('readonly').get(seo_friendly_path__iexact=seo_friendly_path)
                else:
                    campaignx = CampaignX.objects.get(seo_friendly_path__iexact=seo_friendly_path)
                campaignx_found = True
                campaignx_we_vote_id = campaignx.we_vote_id
                status += 'CAMPAIGNX_FOUND_WITH_SEO_FRIENDLY_PATH '
                success = True
            else:
                status += 'CAMPAIGNX_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except CampaignX.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status += 'CAMPAIGNX_NOT_FOUND_MultipleObjectsReturned '
            success = False
        except CampaignX.DoesNotExist:
            exception_does_not_exist = True
            status += 'CAMPAIGNX_NOT_FOUND_DoesNotExist '
            success = True

        if positive_value_exists(campaignx_found):
            campaignx_owner_object_list = campaignx_manager.retrieve_campaignx_owner_list(
                campaignx_we_vote_id=campaignx_we_vote_id, viewer_is_owner=False)
            for campaignx_owner in campaignx_owner_object_list:
                campaign_owner_dict = {
                    'organization_name':                        campaignx_owner.organization_name,
                    'organization_we_vote_id':                  campaignx_owner.organization_we_vote_id,
                    'feature_this_profile_image':                       campaignx_owner.feature_this_profile_image,
                    'visible_to_public':                        campaignx_owner.visible_to_public,
                    'we_vote_hosted_profile_image_url_tiny':    campaignx_owner.we_vote_hosted_profile_image_url_tiny,
                }
                campaignx_owner_list.append(campaign_owner_dict)

            seo_friendly_path_list = \
                campaignx_manager.retrieve_seo_friendly_path_simple_list(
                    campaignx_we_vote_id=campaignx_we_vote_id)

        results = {
            'status':                   status,
            'success':                  success,
            'campaignx':                campaignx,
            'campaignx_found':          campaignx_found,
            'campaignx_we_vote_id':     campaignx_we_vote_id,
            'campaignx_owner_list':     campaignx_owner_list,
            'seo_friendly_path_list':   seo_friendly_path_list,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
        }
        return results

    def retrieve_campaignx_listed_by_organization_list(
            self,
            site_owner_organization_we_vote_id='',
            visible_to_public=True,
            ignore_visible_to_public=False,
            read_only=True):
        campaignx_listed_by_organization_list_found = False
        campaignx_listed_by_organization_list = []
        try:
            if read_only:
                query = CampaignXListedByOrganization.objects.using('readonly').all()
            else:
                query = CampaignXListedByOrganization.objects.all()
            query = query.filter(site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            if not positive_value_exists(ignore_visible_to_public):
                query = query.filter(visible_to_public=visible_to_public)
            campaignx_listed_by_organization_list = list(query)
            if len(campaignx_listed_by_organization_list):
                campaignx_listed_by_organization_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if campaignx_listed_by_organization_list_found:
            return campaignx_listed_by_organization_list
        else:
            campaignx_listed_by_organization_list = []
            return campaignx_listed_by_organization_list

    def retrieve_campaignx_listed_by_organization_simple_list(
            self,
            site_owner_organization_we_vote_id='',
            visible_to_public=True):
        campaignx_listed_by_organization_list = \
            self.retrieve_campaignx_listed_by_organization_list(
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id,
                visible_to_public=visible_to_public,
                read_only=True)
        simple_list = []
        for one_link in campaignx_listed_by_organization_list:
            simple_list.append(one_link.campaignx_we_vote_id)
        return simple_list

    def retrieve_visible_on_this_site_campaignx_simple_list(
            self,
            site_owner_organization_we_vote_id='',
            visible_to_public=True):
        campaignx_listed_by_organization_list = \
            self.retrieve_campaignx_listed_by_organization_list(
                site_owner_organization_we_vote_id=site_owner_organization_we_vote_id,
                visible_to_public=visible_to_public,
                read_only=True)
        simple_list = []
        for one_link in campaignx_listed_by_organization_list:
            simple_list.append(one_link.campaignx_we_vote_id)

        campaignx_owned_by_organization_list = \
            self.retrieve_campaignx_owner_list(organization_we_vote_id=site_owner_organization_we_vote_id)
        for one_owner in campaignx_owned_by_organization_list:
            simple_list.append(one_owner.campaignx_we_vote_id)
        return simple_list

    def retrieve_campaignx_list(
            self,
            including_started_by_voter_we_vote_id=None,
            including_campaignx_we_vote_id_list=[],
            excluding_campaignx_we_vote_id_list=[],
            including_politicians_in_any_of_these_states=None,
            including_politicians_with_support_in_any_of_these_issues=None,
            limit=25,
            read_only=True):
        campaignx_list = []
        campaignx_list_found = False
        success = True
        status = ""
        voter_started_campaignx_we_vote_ids = []
        voter_supported_campaignx_we_vote_ids = []

        try:
            if read_only:
                campaignx_queryset = CampaignX.objects.using('readonly').all()
            else:
                campaignx_queryset = CampaignX.objects.all()

            # #########
            # All "OR" queries
            filters = []
            if positive_value_exists(including_started_by_voter_we_vote_id):
                new_filter = Q(started_by_voter_we_vote_id__iexact=including_started_by_voter_we_vote_id)
                filters.append(new_filter)

            new_filter = Q(in_draft_mode=False,
                           is_blocked_by_we_vote=False,
                           is_still_active=True,
                           is_ok_to_promote_on_we_vote=True)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                campaignx_queryset = campaignx_queryset.filter(final_filters)

            campaignx_queryset = campaignx_queryset.order_by('-supporters_count')
            campaignx_queryset = campaignx_queryset.order_by('-in_draft_mode')

            campaignx_list = campaignx_queryset[:limit]
            campaignx_list_found = positive_value_exists(len(campaignx_list))
            status += "RETRIEVE_CAMPAIGNX_LIST_SUCCEEDED "
        except Exception as e:
            success = False
            status += "RETRIEVE_CAMPAIGNX_LIST_FAILED: " + str(e) + " "
            campaignx_list_found = False

        campaignx_list_modified = []
        for campaignx in campaignx_list:
            campaignx.visible_on_this_site = True
            campaignx_list_modified.append(campaignx)

        results = {
            'success':                                  success,
            'status':                                   status,
            'campaignx_list_found':                     campaignx_list_found,
            'campaignx_list':                           campaignx_list_modified,
            'voter_started_campaignx_we_vote_ids':      voter_started_campaignx_we_vote_ids,
            'voter_supported_campaignx_we_vote_ids':    voter_supported_campaignx_we_vote_ids,
        }
        return results

    def retrieve_campaignx_list_for_private_label(
            self,
            including_started_by_voter_we_vote_id='',
            limit=25,
            site_owner_organization_we_vote_id='',
            read_only=True):
        campaignx_list = []
        success = True
        status = ""
        visible_on_this_site_campaignx_we_vote_id_list = []
        campaignx_list_modified = []
        voter_started_campaignx_we_vote_ids = []
        voter_supported_campaignx_we_vote_ids = []

        # Limit the campaigns retrieved to the ones approved by the site owner
        if positive_value_exists(site_owner_organization_we_vote_id):
            try:
                campaignx_manager = CampaignXManager()
                visible_on_this_site_campaignx_we_vote_id_list = \
                    campaignx_manager.retrieve_visible_on_this_site_campaignx_simple_list(
                        site_owner_organization_we_vote_id=site_owner_organization_we_vote_id)
            except Exception as e:
                success = False
                status += "RETRIEVE_CAMPAIGNX_LIST_FOR_PRIVATE_LABEL_FAILED: " + str(e) + " "

        try:
            if read_only:
                campaignx_queryset = CampaignX.objects.using('readonly').all()
            else:
                campaignx_queryset = CampaignX.objects.all()

            # #########
            # All "OR" queries
            filters = []
            # Campaigns started by this voter
            if positive_value_exists(including_started_by_voter_we_vote_id):
                new_filter = \
                    Q(started_by_voter_we_vote_id__iexact=including_started_by_voter_we_vote_id)  # , in_draft_mode=True
                filters.append(new_filter)

            # Campaigns approved to be shown on this site
            new_filter = \
                Q(we_vote_id__in=visible_on_this_site_campaignx_we_vote_id_list,
                  in_draft_mode=False,
                  is_blocked_by_we_vote=False,
                  is_still_active=True)
            filters.append(new_filter)

            # Add the first query
            if len(filters):
                final_filters = filters.pop()

                # ...and "OR" the remaining items in the list
                for item in filters:
                    final_filters |= item

                campaignx_queryset = campaignx_queryset.filter(final_filters)

            campaignx_queryset = campaignx_queryset.order_by('-supporters_count')
            campaignx_queryset = campaignx_queryset.order_by('-in_draft_mode')

            campaignx_list = campaignx_queryset[:limit]
            campaignx_list_found = positive_value_exists(len(campaignx_list))
            for one_campaignx in campaignx_list:
                if one_campaignx.we_vote_id in visible_on_this_site_campaignx_we_vote_id_list:
                    one_campaignx.visible_on_this_site = True
                else:
                    one_campaignx.visible_on_this_site = False
                campaignx_list_modified.append(one_campaignx)
            status += "RETRIEVE_CAMPAIGNX_LIST_FOR_PRIVATE_LABEL_SUCCEEDED "
        except Exception as e:
            success = False
            status += "RETRIEVE_CAMPAIGNX_LIST_FOR_PRIVATE_LABEL_FAILED: " + str(e) + " "
            campaignx_list_found = False

        results = {
            'success':                                  success,
            'status':                                   status,
            'visible_on_this_site_campaignx_we_vote_id_list': visible_on_this_site_campaignx_we_vote_id_list,
            'campaignx_list_found':                     campaignx_list_found,
            'campaignx_list':                           campaignx_list_modified,
            'voter_started_campaignx_we_vote_ids':      voter_started_campaignx_we_vote_ids,
            'voter_supported_campaignx_we_vote_ids':    voter_supported_campaignx_we_vote_ids,
        }
        return results

    def retrieve_campaignx_list_for_voter(self, voter_id):
        campaignx_list_found = False
        campaignx_list = {}
        try:
            campaignx_list = CampaignX.objects.all()
            campaignx_list = campaignx_list.filter(voter_id=voter_id)
            if len(campaignx_list):
                campaignx_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if campaignx_list_found:
            return campaignx_list
        else:
            campaignx_list = {}
            return campaignx_list

    def retrieve_campaignx_owner(self, campaignx_we_vote_id='', voter_we_vote_id='', read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        campaignx_owner = None
        campaignx_owner_found = False
        status = ''

        try:
            if positive_value_exists(campaignx_we_vote_id) and positive_value_exists(voter_we_vote_id):
                if positive_value_exists(read_only):
                    campaignx_owner = CampaignXOwner.objects.using('readonly').get(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                else:
                    campaignx_owner = CampaignXOwner.objects.get(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                campaignx_owner_found = True
                status += 'CAMPAIGNX_OWNER_FOUND_WITH_WE_VOTE_ID '
                success = True
            else:
                status += 'CAMPAIGNX_OWNER_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except CampaignXOwner.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status += 'CAMPAIGNX_OWNER_NOT_FOUND_MultipleObjectsReturned '
            success = False
        except CampaignXOwner.DoesNotExist:
            exception_does_not_exist = True
            status += 'CAMPAIGNX_OWNER_NOT_FOUND_DoesNotExist '
            success = True

        results = {
            'status':                   status,
            'success':                  success,
            'campaignx_owner':          campaignx_owner,
            'campaignx_owner_found':    campaignx_owner_found,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
        }
        return results

    def retrieve_campaignx_owner_list(self, campaignx_we_vote_id='', organization_we_vote_id='', viewer_is_owner=False):
        campaignx_owner_list_found = False
        campaignx_owner_list = []
        try:
            campaignx_owner_query = CampaignXOwner.objects.all()
            if not positive_value_exists(viewer_is_owner):
                # If not already an owner, limit to owners who are visible to public
                campaignx_owner_query = campaignx_owner_query.filter(visible_to_public=True)
            if positive_value_exists(campaignx_we_vote_id):
                campaignx_owner_query = campaignx_owner_query.filter(campaignx_we_vote_id=campaignx_we_vote_id)
            if positive_value_exists(organization_we_vote_id):
                campaignx_owner_query = campaignx_owner_query.filter(organization_we_vote_id=organization_we_vote_id)
            campaignx_owner_list = list(campaignx_owner_query)
            if len(campaignx_owner_list):
                campaignx_owner_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if campaignx_owner_list_found:
            return campaignx_owner_list
        else:
            campaignx_owner_list = []
            return campaignx_owner_list

    def retrieve_campaignx_politician(
            self,
            campaignx_we_vote_id='',
            politician_we_vote_id='',
            politician_name='',
            read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        campaignx_politician = None
        campaignx_politician_found = False
        status = ''

        try:
            if positive_value_exists(campaignx_we_vote_id) and positive_value_exists(politician_we_vote_id):
                if positive_value_exists(read_only):
                    campaignx_politician = CampaignXPolitician.objects.using('readonly').get(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        politician_we_vote_id=politician_we_vote_id)
                else:
                    campaignx_politician = CampaignXPolitician.objects.get(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        politician_we_vote_id=politician_we_vote_id)
                campaignx_politician_found = True
                status += 'CAMPAIGNX_POLITICIAN_FOUND_WITH_WE_VOTE_ID '
                success = True
            elif positive_value_exists(campaignx_we_vote_id) and positive_value_exists(politician_name):
                if positive_value_exists(read_only):
                    campaignx_politician = CampaignXPolitician.objects.using('readonly').get(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        politician_name=politician_name)
                else:
                    campaignx_politician = CampaignXPolitician.objects.get(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        politician_name=politician_name)
                campaignx_politician_found = True
                status += 'CAMPAIGNX_POLITICIAN_FOUND_WITH_NAME '
                success = True
            else:
                status += 'CAMPAIGNX_POLITICIAN_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except CampaignXPolitician.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status += 'CAMPAIGNX_POLITICIAN_NOT_FOUND_MultipleObjectsReturned '
            success = False
        except CampaignXPolitician.DoesNotExist:
            exception_does_not_exist = True
            status += 'CAMPAIGNX_POLITICIAN_NOT_FOUND_DoesNotExist '
            success = True

        results = {
            'status':                       status,
            'success':                      success,
            'campaignx_politician':         campaignx_politician,
            'campaignx_politician_found':   campaignx_politician_found,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def retrieve_campaignx_politician_list(self, campaignx_we_vote_id=''):
        campaignx_politician_list_found = False
        campaignx_politician_list = []
        try:
            campaignx_politician_query = CampaignXPolitician.objects.all()
            campaignx_politician_query = campaignx_politician_query.filter(campaignx_we_vote_id=campaignx_we_vote_id)
            campaignx_politician_list = list(campaignx_politician_query)
            if len(campaignx_politician_list):
                campaignx_politician_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if campaignx_politician_list_found:
            return campaignx_politician_list
        else:
            campaignx_politician_list = []
            return campaignx_politician_list

    def retrieve_campaignx_supporter(self, campaignx_we_vote_id='', voter_we_vote_id='', read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        campaignx_supporter = None
        campaignx_supporter_found = False
        status = ''

        try:
            if positive_value_exists(campaignx_we_vote_id) and positive_value_exists(voter_we_vote_id):
                if positive_value_exists(read_only):
                    campaignx_supporter = CampaignXSupporter.objects.using('readonly').get(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                else:
                    campaignx_supporter = CampaignXSupporter.objects.get(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        voter_we_vote_id=voter_we_vote_id)
                campaignx_supporter_found = True
                status += 'CAMPAIGNX_SUPPORTER_FOUND_WITH_WE_VOTE_ID '
                success = True
            else:
                status += 'CAMPAIGNX_SUPPORTER_NOT_FOUND-MISSING_VARIABLES '
                success = False
        except CampaignXSupporter.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            exception_multiple_object_returned = True
            status += 'CAMPAIGNX_SUPPORTER_NOT_FOUND_MultipleObjectsReturned '
            success = False
        except CampaignXSupporter.DoesNotExist:
            exception_does_not_exist = True
            status += 'CAMPAIGNX_SUPPORTER_NOT_FOUND_DoesNotExist '
            success = True

        results = {
            'status':                       status,
            'success':                      success,
            'campaignx_supporter':          campaignx_supporter,
            'campaignx_supporter_found':    campaignx_supporter_found,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results

    def retrieve_campaignx_supporter_list(
            self,
            campaignx_we_vote_id=None,
            require_supporter_endorsement=False,
            limit=10,
            read_only=True):
        supporter_list = []
        supporter_list_found = False
        success = True
        status = ""

        try:
            if read_only:
                campaignx_queryset = CampaignXSupporter.objects.using('readonly').all()
            else:
                campaignx_queryset = CampaignXSupporter.objects.all()

            campaignx_queryset = campaignx_queryset.filter(campaignx_we_vote_id=campaignx_we_vote_id)
            campaignx_queryset = campaignx_queryset.filter(visible_to_public=True)
            if positive_value_exists(require_supporter_endorsement):
                campaignx_queryset = campaignx_queryset.exclude(
                    Q(supporter_endorsement__isnull=True) |
                    Q(supporter_endorsement__exact='')
                )
            campaignx_queryset = campaignx_queryset.order_by('-date_supported')

            supporter_list = campaignx_queryset[:limit]
            supporter_list_found = positive_value_exists(len(supporter_list))
            status += "RETRIEVE_CAMPAIGNX_SUPPORTER_LIST_SUCCEEDED "
        except Exception as e:
            success = False
            status += "RETRIEVE_CAMPAIGNX_SUPPORTER_LIST_FAILED: " + str(e) + " "
            supporter_list_found = False

        results = {
            'success':                                  success,
            'status':                                   status,
            'supporter_list_found':                     supporter_list_found,
            'supporter_list':                           supporter_list,
        }
        return results

    def retrieve_seo_friendly_path_list(self, campaignx_we_vote_id=''):
        seo_friendly_path_list_found = False
        seo_friendly_path_list = []
        try:
            query = CampaignXSEOFriendlyPath.objects.all()
            query = query.filter(campaignx_we_vote_id=campaignx_we_vote_id)
            seo_friendly_path_list = list(query)
            if len(seo_friendly_path_list):
                seo_friendly_path_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if seo_friendly_path_list_found:
            return seo_friendly_path_list
        else:
            seo_friendly_path_list = []
            return seo_friendly_path_list

    def retrieve_seo_friendly_path_simple_list(self, campaignx_we_vote_id=''):
        seo_friendly_path_list = \
            self.retrieve_seo_friendly_path_list(campaignx_we_vote_id=campaignx_we_vote_id)
        simple_list = []
        for one_path in seo_friendly_path_list:
            simple_list.append(one_path.final_pathname_string)
        return simple_list

    def update_campaignx_owners_with_organization_change(
            self,
            organization_we_vote_id,
            organization_name,
            we_vote_hosted_profile_image_url_tiny):
        status = ''
        success = True
        campaignx_owner_entries_updated = 0

        try:
            campaignx_owner_entries_updated = CampaignXOwner.objects \
                .filter(organization_we_vote_id__iexact=organization_we_vote_id) \
                .update(organization_name=organization_name,
                        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_OWNER_UPDATE_WITH_ORGANIZATION_CHANGE: " + str(e) + " "
            success = False

        results = {
            'success': success,
            'status': status,
            'campaignx_owner_entries_updated': campaignx_owner_entries_updated,
        }
        return results

    def update_campaignx_supporters_with_organization_change(
            self,
            organization_we_vote_id,
            supporter_name,
            we_vote_hosted_profile_image_url_tiny):
        status = ''
        success = True
        campaignx_supporter_entries_updated = 0

        try:
            campaignx_supporter_entries_updated = CampaignXSupporter.objects \
                .filter(organization_we_vote_id__iexact=organization_we_vote_id) \
                .update(supporter_name=supporter_name,
                        we_vote_hosted_profile_image_url_tiny=we_vote_hosted_profile_image_url_tiny)
        except Exception as e:
            status += "FAILED-CAMPAIGNX_SUPPORTER_UPDATE_WITH_ORGANIZATION_CHANGE: " + str(e) + " "
            success = False

        results = {
            'success': success,
            'status': status,
            'campaignx_supporter_entries_updated': campaignx_supporter_entries_updated,
        }
        return results

    def update_campaignx_supporters_count(self, campaignx_we_vote_id):
        status = ''
        supporters_count = 0
        try:
            count_query = CampaignXSupporter.objects.using('readonly').all()
            count_query = count_query.filter(campaignx_we_vote_id__iexact=campaignx_we_vote_id)
            count_query = count_query.filter(campaign_supported=True)
            supporters_count = count_query.count()
        except Exception as e:
            status += "FAILED_RETRIEVING_SUPPORTER_COUNT: " + str(e) + ' '
            results = {
                'success': False,
                'status': status,
                'supporters_count': supporters_count,
            }
            return results

        update_values = {
            'supporters_count': supporters_count,
        }
        update_results = self.update_or_create_campaignx(
            campaignx_we_vote_id=campaignx_we_vote_id,
            update_values=update_values,
        )
        status = update_results['status']
        success = update_results['success']

        results = {
            'success':          success,
            'status':           status,
            'supporters_count': supporters_count,
        }
        return results

    def update_or_create_campaignx(
            self,
            campaignx_we_vote_id='',
            voter_we_vote_id='',
            organization_we_vote_id='',
            update_values={}):
        status = ""
        campaignx = None
        campaignx_changed = False
        campaignx_created = False
        campaignx_manager = CampaignXManager()

        create_variables_exist = \
            positive_value_exists(voter_we_vote_id) and positive_value_exists(organization_we_vote_id)
        update_variables_exist = campaignx_we_vote_id
        if not create_variables_exist and not update_variables_exist:
            if not create_variables_exist:
                status += "CREATE_CAMPAIGNX_VARIABLES_MISSING "
            if not update_variables_exist:
                status += "UPDATE_CAMPAIGNX_VARIABLES_MISSING "
            status += "COULD_NOT_UPDATE_OR_CREATE: "
            results = {
                'success':             False,
                'status':              status,
                'campaignx':           None,
                'campaignx_changed':   False,
                'campaignx_created':   False,
                'campaignx_found':     False,
                'campaignx_we_vote_id': '',
            }
            return results

        if positive_value_exists(campaignx_we_vote_id):
            results = campaignx_manager.retrieve_campaignx_as_owner(
                campaignx_we_vote_id=campaignx_we_vote_id,
                read_only=False)
            campaignx_found = results['campaignx_found']
            if campaignx_found:
                campaignx = results['campaignx']
                campaignx_we_vote_id = campaignx.we_vote_id
            success = results['success']
            status += results['status']
        else:
            results = campaignx_manager.retrieve_campaignx_as_owner(
                voter_we_vote_id=voter_we_vote_id,
                read_only=False)
            campaignx_found = results['campaignx_found']
            if campaignx_found:
                campaignx = results['campaignx']
                campaignx_we_vote_id = campaignx.we_vote_id
            success = results['success']
            status += results['status']

        if not positive_value_exists(success):
            results = {
                'success':              success,
                'status':               status,
                'campaignx':            campaignx,
                'campaignx_changed':    campaignx_changed,
                'campaignx_created':    campaignx_created,
                'campaignx_found':      campaignx_found,
                'campaignx_we_vote_id': campaignx_we_vote_id,
            }
            return results

        if campaignx_found:
            # Update existing campaignx
            try:
                campaignx_changed = False
                if 'campaign_description_changed' in update_values \
                        and positive_value_exists(update_values['campaign_description_changed']):
                    campaignx.campaign_description = update_values['campaign_description']
                    campaignx_changed = True
                if 'campaign_photo_changed' in update_values \
                        and positive_value_exists(update_values['campaign_photo_changed']):
                    if 'we_vote_hosted_campaign_photo_original_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_campaign_photo_original_url']):
                        campaignx.we_vote_hosted_campaign_photo_original_url = \
                            update_values['we_vote_hosted_campaign_photo_original_url']
                        campaignx_changed = True
                    if 'we_vote_hosted_campaign_photo_large_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_campaign_photo_large_url']):
                        campaignx.we_vote_hosted_campaign_photo_large_url = \
                            update_values['we_vote_hosted_campaign_photo_large_url']
                        campaignx_changed = True
                    if 'we_vote_hosted_campaign_photo_medium_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_campaign_photo_medium_url']):
                        campaignx.we_vote_hosted_campaign_photo_medium_url = \
                            update_values['we_vote_hosted_campaign_photo_medium_url']
                        campaignx_changed = True
                    if 'we_vote_hosted_campaign_photo_small_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_campaign_photo_small_url']):
                        campaignx.we_vote_hosted_campaign_photo_large_url = \
                            update_values['we_vote_hosted_campaign_photo_small_url']
                        campaignx_changed = True
                if 'campaign_title_changed' in update_values \
                        and positive_value_exists(update_values['campaign_title_changed']):
                    campaignx.campaign_title = update_values['campaign_title']
                    campaignx_changed = True
                if 'in_draft_mode_changed' in update_values \
                        and positive_value_exists(update_values['in_draft_mode_changed']):
                    in_draft_mode_may_be_updated = True
                    if positive_value_exists(campaignx.campaign_title):
                        # An SEO friendly path is not created when we first create the campaign in draft mode
                        if not positive_value_exists(update_values['in_draft_mode']):
                            # If changing from in_draft_mode to published...
                            path_results = campaignx_manager.generate_seo_friendly_path(
                                campaignx_we_vote_id=campaignx.we_vote_id,
                                campaignx_title=campaignx.campaign_title)
                            if path_results['seo_friendly_path_found']:
                                campaignx.seo_friendly_path = path_results['seo_friendly_path']
                            else:
                                status += path_results['status']
                                in_draft_mode_may_be_updated = False
                    if in_draft_mode_may_be_updated:
                        campaignx.in_draft_mode = positive_value_exists(update_values['in_draft_mode'])
                        campaignx_changed = True
                if 'politician_delete_list_serialized' in update_values \
                        and positive_value_exists(update_values['politician_delete_list_serialized']):
                    # Delete from politician_delete_list
                    if update_values['politician_delete_list_serialized']:
                        politician_delete_list = \
                            json.loads(update_values['politician_delete_list_serialized'])
                    else:
                        politician_delete_list = []
                    results = campaignx_manager.remove_campaignx_politicians_from_delete_list(
                        campaignx_we_vote_id=campaignx.we_vote_id,
                        politician_delete_list=politician_delete_list,
                    )
                    status += results['status']
                if 'politician_starter_list_changed' in update_values \
                        and positive_value_exists(update_values['politician_starter_list_changed']):
                    # Save to politician list
                    if update_values['politician_starter_list_serialized']:
                        campaignx_politician_starter_list = \
                            json.loads(update_values['politician_starter_list_serialized'])
                    else:
                        campaignx_politician_starter_list = []
                    results = campaignx_manager.update_or_create_campaignx_politicians_from_starter(
                        campaignx_we_vote_id=campaignx.we_vote_id,
                        politician_starter_list=campaignx_politician_starter_list,
                    )
                    if results['success']:
                        campaignx.politician_starter_list_serialized = None
                        campaignx_changed = True
                    else:
                        # If save to politician list fails, save starter_list
                        campaignx.politician_starter_list_serialized = \
                            update_values['politician_starter_list_serialized']
                        campaignx_changed = True
                if 'supporters_count' in update_values \
                        and positive_value_exists(update_values['supporters_count']):
                    campaignx.supporters_count = update_values['supporters_count']
                    campaignx_changed = True
                if campaignx_changed:
                    campaignx.save()
                    status += "CAMPAIGNX_UPDATED "
                else:
                    status += "CAMPAIGNX_NOT_UPDATED-NO_CHANGES_FOUND "
                success = True
            except Exception as e:
                campaignx = None
                success = False
                status += "CAMPAIGNX_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                campaignx = CampaignX.objects.create(
                    campaign_description=update_values['campaign_description'],
                    campaign_title=update_values['campaign_title'],
                    in_draft_mode=True,
                    started_by_voter_we_vote_id=voter_we_vote_id,
                    supporters_count=1,
                )
                campaignx_we_vote_id = campaignx.we_vote_id
                if 'campaign_photo_changed' in update_values \
                        and positive_value_exists(update_values['campaign_photo_changed']):
                    if 'we_vote_hosted_campaign_photo_original_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_campaign_photo_original_url']):
                        campaignx.we_vote_hosted_campaign_photo_original_url = \
                            update_values['we_vote_hosted_campaign_photo_original_url']
                        campaignx_changed = True
                    if 'we_vote_hosted_campaign_photo_large_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_campaign_photo_large_url']):
                        campaignx.we_vote_hosted_campaign_photo_large_url = \
                            update_values['we_vote_hosted_campaign_photo_large_url']
                        campaignx_changed = True
                    if 'we_vote_hosted_campaign_photo_medium_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_campaign_photo_medium_url']):
                        campaignx.we_vote_hosted_campaign_photo_medium_url = \
                            update_values['we_vote_hosted_campaign_photo_medium_url']
                        campaignx_changed = True
                    if 'we_vote_hosted_campaign_photo_small_url' in update_values \
                            and positive_value_exists(update_values['we_vote_hosted_campaign_photo_small_url']):
                        campaignx.we_vote_hosted_campaign_photo_large_url = \
                            update_values['we_vote_hosted_campaign_photo_small_url']
                        campaignx_changed = True
                if 'politician_starter_list_changed' in update_values \
                        and positive_value_exists(update_values['politician_starter_list_changed']):
                    # Save to politician list
                    if update_values['politician_starter_list_serialized']:
                        campaignx_politician_starter_list = \
                            json.loads(update_values['politician_starter_list_serialized'])
                    else:
                        campaignx_politician_starter_list = []
                    results = campaignx_manager.update_or_create_campaignx_politicians_from_starter(
                        campaignx_we_vote_id=campaignx.we_vote_id,
                        politician_starter_list=campaignx_politician_starter_list,
                    )
                    if results['success']:
                        campaignx.politician_starter_list_serialized = None
                        campaignx_changed = True
                    else:
                        # If save to politician list fails, save starter_list
                        campaignx.politician_starter_list_serialized = \
                            update_values['politician_starter_list_serialized']
                        campaignx_changed = True
                if campaignx_changed:
                    campaignx.save()
                    status += "CAMPAIGNX_CREATED_AND_THEN_CHANGED "
                else:
                    status += "CAMPAIGNX_CREATED "
                campaignx_created = True
                campaignx_found = True
                success = True
            except Exception as e:
                campaignx_created = False
                campaignx = CampaignX()
                success = False
                status += "CAMPAIGNX_NOT_CREATED: " + str(e) + " "

        if success:
            if 'politician_starter_list_changed' in update_values \
                    and positive_value_exists(update_values['politician_starter_list_changed']):
                campaignx.politician_starter_list_serialized = update_values['politician_starter_list_serialized']
                campaignx_changed = True

        results = {
            'success':              success,
            'status':               status,
            'campaignx':            campaignx,
            'campaignx_changed':    campaignx_changed,
            'campaignx_created':    campaignx_created,
            'campaignx_found':      campaignx_found,
            'campaignx_we_vote_id': campaignx_we_vote_id,
        }
        return results

    def update_or_create_campaignx_owner(
            self,
            campaignx_we_vote_id='',
            voter_we_vote_id='',
            organization_we_vote_id=None,
            organization_name=None,
            visible_to_public=None,
            we_vote_hosted_profile_image_url_tiny=None):
        status = ""
        if not positive_value_exists(campaignx_we_vote_id) or not positive_value_exists(voter_we_vote_id):
            status += "MISSING_REQUIRED_VALUE_FOR_CAMPAIGNX_OWNER "
            results = {
                'success':                  False,
                'status':                   status,
                'campaignx_owner_created':  False,
                'campaignx_owner_found':    False,
                'campaignx_owner_updated':  False,
                'campaignx_owner':          None,
            }
            return results

        campaignx_manager = CampaignXManager()
        campaignx_owner_created = False
        campaignx_owner_updated = False

        results = campaignx_manager.retrieve_campaignx_owner(
            campaignx_we_vote_id=campaignx_we_vote_id, voter_we_vote_id=voter_we_vote_id, read_only=False)
        campaignx_owner_found = results['campaignx_owner_found']
        campaignx_owner = results['campaignx_owner']
        success = results['success']
        status += results['status']

        if organization_name is None and positive_value_exists(organization_we_vote_id):
            from organization.models import OrganizationManager
            organization_manager = OrganizationManager()
            organization_results = \
                organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
            if organization_results['organization_found']:
                organization = organization_results['organization']
                organization_name = organization.organization_name

        if campaignx_owner_found:
            if organization_name is not None \
                    or organization_we_vote_id is not None \
                    or visible_to_public is not None \
                    or we_vote_hosted_profile_image_url_tiny is not None:
                try:
                    if organization_name is not None:
                        campaignx_owner.organization_name = organization_name
                    if organization_we_vote_id is not None:
                        campaignx_owner.organization_we_vote_id = organization_we_vote_id
                    if visible_to_public is not None:
                        campaignx_owner.visible_to_public = positive_value_exists(visible_to_public)
                    if we_vote_hosted_profile_image_url_tiny is not None:
                        campaignx_owner.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                    campaignx_owner.save()
                    campaignx_owner_updated = True
                    success = True
                    status += "CAMPAIGNX_OWNER_UPDATED "
                except Exception as e:
                    campaignx_owner = CampaignXOwner()
                    success = False
                    status += "CAMPAIGNX_OWNER_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                campaignx_owner = CampaignXOwner.objects.create(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                    visible_to_public=True,
                )
                if organization_name is not None:
                    campaignx_owner.organization_name = organization_name
                if organization_we_vote_id is not None:
                    campaignx_owner.organization_we_vote_id = organization_we_vote_id
                if visible_to_public is not None:
                    campaignx_owner.visible_to_public = positive_value_exists(visible_to_public)
                if we_vote_hosted_profile_image_url_tiny is not None:
                    campaignx_owner.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                campaignx_owner.save()
                campaignx_owner_created = True
                success = True
                status += "CAMPAIGNX_OWNER_CREATED "
            except Exception as e:
                campaignx_owner = None
                success = False
                status += "CAMPAIGNX_OWNER_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                  success,
            'status':                   status,
            'campaignx_owner_created':  campaignx_owner_created,
            'campaignx_owner_found':    campaignx_owner_found,
            'campaignx_owner_updated':  campaignx_owner_updated,
            'campaignx_owner':          campaignx_owner,
        }
        return results

    def update_or_create_campaignx_politician(
            self,
            campaignx_we_vote_id='',
            politician_name=None,
            politician_we_vote_id=None,
            state_code='',
            we_vote_hosted_profile_image_url_large=None,
            we_vote_hosted_profile_image_url_medium=None,
            we_vote_hosted_profile_image_url_tiny=None):
        status = ""
        if not positive_value_exists(campaignx_we_vote_id) or not positive_value_exists(politician_name):
            status += "MISSING_REQUIRED_VALUE_FOR_CAMPAIGNX_POLITICIAN "
            results = {
                'success':                      False,
                'status':                       status,
                'campaignx_politician_created': False,
                'campaignx_politician_found':   False,
                'campaignx_politician_updated': False,
                'campaignx_politician':         None,
            }
            return results

        campaignx_manager = CampaignXManager()
        campaignx_politician_created = False
        campaignx_politician_updated = False

        results = campaignx_manager.retrieve_campaignx_politician(
            campaignx_we_vote_id=campaignx_we_vote_id,
            politician_we_vote_id=politician_we_vote_id,
            politician_name=politician_name,
            read_only=False)
        campaignx_politician_found = results['campaignx_politician_found']
        campaignx_politician = results['campaignx_politician']
        success = results['success']
        status += results['status']

        if campaignx_politician_found:
            if politician_name is not None \
                    or politician_we_vote_id is not None \
                    or state_code is not None \
                    or we_vote_hosted_profile_image_url_large is not None \
                    or we_vote_hosted_profile_image_url_medium is not None \
                    or we_vote_hosted_profile_image_url_tiny is not None:
                try:
                    if politician_name is not None:
                        campaignx_politician.politician_name = politician_name
                    if politician_we_vote_id is not None:
                        campaignx_politician.politician_we_vote_id = politician_we_vote_id
                    if state_code is not None:
                        campaignx_politician.state_code = state_code
                    if we_vote_hosted_profile_image_url_large is not None:
                        campaignx_politician.we_vote_hosted_profile_image_url_large = \
                            we_vote_hosted_profile_image_url_large
                    if we_vote_hosted_profile_image_url_medium is not None:
                        campaignx_politician.we_vote_hosted_profile_image_url_medium = \
                            we_vote_hosted_profile_image_url_medium
                    if we_vote_hosted_profile_image_url_tiny is not None:
                        campaignx_politician.we_vote_hosted_profile_image_url_tiny = \
                            we_vote_hosted_profile_image_url_tiny
                    campaignx_politician.save()
                    campaignx_politician_updated = True
                    success = True
                    status += "CAMPAIGNX_POLITICIAN_UPDATED "
                except Exception as e:
                    campaignx_politician = None
                    success = False
                    status += "CAMPAIGNX_POLITICIAN_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                campaignx_politician = CampaignXPolitician.objects.create(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    politician_name=politician_name,
                )
                if politician_we_vote_id is not None:
                    campaignx_politician.politician_we_vote_id = politician_we_vote_id
                if state_code is not None:
                    campaignx_politician.state_code = state_code
                if we_vote_hosted_profile_image_url_large is not None:
                    campaignx_politician.we_vote_hosted_profile_image_url_large = we_vote_hosted_profile_image_url_large
                if we_vote_hosted_profile_image_url_medium is not None:
                    campaignx_politician.we_vote_hosted_profile_image_url_medium = \
                        we_vote_hosted_profile_image_url_medium
                if we_vote_hosted_profile_image_url_tiny is not None:
                    campaignx_politician.we_vote_hosted_profile_image_url_tiny = we_vote_hosted_profile_image_url_tiny
                campaignx_politician.save()
                campaignx_politician_created = True
                success = True
                status += "CAMPAIGNX_POLITICIAN_CREATED "
            except Exception as e:
                campaignx_politician = None
                success = False
                status += "CAMPAIGNX_POLITICIAN_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'campaignx_politician_created': campaignx_politician_created,
            'campaignx_politician_found':   campaignx_politician_found,
            'campaignx_politician_updated': campaignx_politician_updated,
            'campaignx_politician':         campaignx_politician,
        }
        return results

    def update_or_create_campaignx_politicians_from_starter(
            self,
            campaignx_we_vote_id='',
            politician_starter_list=[]):
        success = True
        status = ''

        campaignx_politician_existing_name_list = []
        campaignx_politician_existing_we_vote_id_list = []
        campaignx_politician_list_created = False
        campaignx_politician_list_found = False
        campaignx_politician_list_updated = False
        politician_starter_we_vote_id_list = []
        politician_starter_names_without_we_vote_id_list = []
        for politician_starter in politician_starter_list:
            # When politician_starter['value'] and politician_starter['label'] match, it means there isn't we_vote_id
            if positive_value_exists(politician_starter['value']) and \
                    politician_starter['value'] != politician_starter['label']:
                politician_starter_we_vote_id_list.append(politician_starter['value'])
            elif positive_value_exists(politician_starter['label']):
                politician_starter_names_without_we_vote_id_list.append(politician_starter['label'])

        campaignx_manager = CampaignXManager()
        campaignx_politician_list = campaignx_manager.retrieve_campaignx_politician_list(
            campaignx_we_vote_id=campaignx_we_vote_id,
        )
        for campaignx_politician in campaignx_politician_list:
            campaignx_politician_existing_we_vote_id_list.append(campaignx_politician.politician_we_vote_id)
            if not positive_value_exists(campaignx_politician.politician_we_vote_id):
                campaignx_politician_existing_name_list.append(campaignx_politician.politician_name)
            if campaignx_politician.politician_we_vote_id not in politician_starter_we_vote_id_list:
                # NOTE: For now we won't delete any names -- only add them
                if len(politician_starter_names_without_we_vote_id_list) == 0:
                    # Delete this campaignx_politician
                    pass
                else:
                    # Make sure this politician isn't in the politician_starter_names_without_we_vote_id_list
                    pass

        from politician.models import PoliticianManager
        politician_manager = PoliticianManager()
        for campaignx_politician_we_vote_id in politician_starter_we_vote_id_list:
            if campaignx_politician_we_vote_id not in campaignx_politician_existing_we_vote_id_list:
                results = politician_manager.retrieve_politician(
                    we_vote_id=campaignx_politician_we_vote_id,
                    read_only=True)
                if results['politician_found']:
                    # Create campaignx_politician
                    create_results = campaignx_manager.update_or_create_campaignx_politician(
                        campaignx_we_vote_id=campaignx_we_vote_id,
                        politician_name=results['politician'].politician_name,
                        politician_we_vote_id=campaignx_politician_we_vote_id,
                        state_code=results['politician'].state_code,
                        we_vote_hosted_profile_image_url_large=
                        results['politician'].we_vote_hosted_profile_image_url_large,
                        we_vote_hosted_profile_image_url_medium=
                        results['politician'].we_vote_hosted_profile_image_url_medium,
                        we_vote_hosted_profile_image_url_tiny=
                        results['politician'].we_vote_hosted_profile_image_url_tiny,
                    )
                    if campaignx_politician_we_vote_id not in campaignx_politician_existing_we_vote_id_list and \
                            create_results['campaignx_politician_found'] or \
                            create_results['campaignx_politician_created']:
                        campaignx_politician_existing_we_vote_id_list.append(campaignx_politician_we_vote_id)
        for campaignx_politician_name in politician_starter_names_without_we_vote_id_list:
            if campaignx_politician_name not in campaignx_politician_existing_name_list:
                # Create campaignx_politician
                create_results = campaignx_manager.update_or_create_campaignx_politician(
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    politician_name=campaignx_politician_name,
                    politician_we_vote_id=None,
                )
                if campaignx_politician_name not in campaignx_politician_existing_name_list and \
                        create_results['campaignx_politician_found'] or \
                        create_results['campaignx_politician_created']:
                    campaignx_politician_existing_name_list.append(campaignx_politician_name)

        results = {
            'success': success,
            'status': status,
            'campaignx_politician_list_created':    campaignx_politician_list_created,
            'campaignx_politician_list_found':      campaignx_politician_list_found,
            'campaignx_politician_list_updated':    campaignx_politician_list_updated,
            'campaignx_politician_list':            campaignx_politician_list,
        }
        return results

    def update_or_create_campaignx_supporter(
            self,
            campaignx_we_vote_id='',
            voter_we_vote_id='',
            organization_we_vote_id='',
            update_values={}):
        status = ""
        campaignx_supporter = None
        campaignx_supporter_changed = False
        campaignx_supporter_created = False
        campaignx_manager = CampaignXManager()

        create_variables_exist = positive_value_exists(campaignx_we_vote_id) \
            and positive_value_exists(voter_we_vote_id) \
            and positive_value_exists(organization_we_vote_id)
        update_variables_exist = positive_value_exists(campaignx_we_vote_id) \
            and positive_value_exists(voter_we_vote_id)
        if not create_variables_exist and not update_variables_exist:
            status += "COULD_NOT_UPDATE_OR_CREATE: "
            if not create_variables_exist:
                status += "CREATE_CAMPAIGNX_SUPPORTER_VARIABLES_MISSING "
            if not update_variables_exist:
                status += "UPDATE_CAMPAIGNX_SUPPORTER_VARIABLES_MISSING "
            results = {
                'success':                      False,
                'status':                       status,
                'campaignx_supporter':          None,
                'campaignx_supporter_changed':  False,
                'campaignx_supporter_created':  False,
                'campaignx_supporter_found':    False,
                'campaignx_we_vote_id':         '',
                'voter_we_vote_id':             '',
            }
            return results

        results = campaignx_manager.retrieve_campaignx_supporter(
            campaignx_we_vote_id=campaignx_we_vote_id,
            voter_we_vote_id=voter_we_vote_id,
            read_only=False)
        campaignx_supporter_found = results['campaignx_supporter_found']
        if campaignx_supporter_found:
            campaignx_supporter = results['campaignx_supporter']
        success = results['success']
        status += results['status']

        if not positive_value_exists(success):
            results = {
                'success':                      success,
                'status':                       status,
                'campaignx_supporter':          campaignx_supporter,
                'campaignx_supporter_changed':  campaignx_supporter_changed,
                'campaignx_supporter_created':  campaignx_supporter_created,
                'campaignx_supporter_found':    campaignx_supporter_found,
                'campaignx_we_vote_id':         campaignx_we_vote_id,
                'voter_we_vote_id':             voter_we_vote_id,
            }
            return results

        if campaignx_supporter_found:
            # Update existing campaignx_supporter with changes
            try:
                campaignx_supporter_changed = False
                if 'campaign_supported_changed' in update_values \
                        and positive_value_exists(update_values['campaign_supported_changed']):
                    campaignx_supporter.campaign_supported = update_values['campaign_supported']
                    campaignx_supporter_changed = True
                if 'supporter_endorsement_changed' in update_values \
                        and positive_value_exists(update_values['supporter_endorsement_changed']):
                    campaignx_supporter.supporter_endorsement = \
                        update_values['supporter_endorsement']
                    campaignx_supporter_changed = True
                if 'visible_to_public_changed' in update_values \
                        and positive_value_exists(update_values['visible_to_public_changed']):
                    campaignx_supporter.visible_to_public = update_values['visible_to_public']
                    campaignx_supporter_changed = True
                if campaignx_supporter_changed:
                    campaignx_supporter.save()
                    status += "CAMPAIGNX_SUPPORTER_UPDATED "
                else:
                    status += "CAMPAIGNX_SUPPORTER_NOT_UPDATED-NO_CHANGES_FOUND "
                success = True
            except Exception as e:
                campaignx_supporter = None
                success = False
                status += "CAMPAIGNX_SUPPORTER_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                campaignx_supporter = CampaignXSupporter.objects.create(
                    campaign_supported=True,
                    campaignx_we_vote_id=campaignx_we_vote_id,
                    organization_we_vote_id=organization_we_vote_id,
                    voter_we_vote_id=voter_we_vote_id,
                )
                status += "CAMPAIGNX_SUPPORTER_CREATED "
                # Retrieve the supporter_name and we_vote_hosted_profile_image_url_tiny from the organization entry
                from organization.models import OrganizationManager
                organization_manager = OrganizationManager()
                organization_results = \
                    organization_manager.retrieve_organization_from_we_vote_id(organization_we_vote_id)
                if organization_results['organization_found']:
                    organization = organization_results['organization']
                    if positive_value_exists(organization.organization_name):
                        campaignx_supporter.supporter_name = organization.organization_name
                        campaignx_supporter_changed = True
                    if positive_value_exists(organization.we_vote_hosted_profile_image_url_tiny):
                        campaignx_supporter.we_vote_hosted_profile_image_url_tiny = \
                            organization.we_vote_hosted_profile_image_url_tiny
                        campaignx_supporter_changed = True

                if 'supporter_endorsement_changed' in update_values \
                        and positive_value_exists(update_values['supporter_endorsement_changed']):
                    campaignx_supporter.supporter_endorsement = update_values['supporter_endorsement']
                    campaignx_supporter_changed = True
                if 'visible_to_public_changed' in update_values \
                        and positive_value_exists(update_values['visible_to_public_changed']):
                    campaignx_supporter.visible_to_public = update_values['visible_to_public']
                    campaignx_supporter_changed = True
                if campaignx_supporter_changed:
                    campaignx_supporter.save()
                    status += "CAMPAIGNX_SUPPORTER_SAVED "
                campaignx_supporter_created = True
                campaignx_supporter_found = True
                success = True
            except Exception as e:
                campaignx_supporter_created = False
                campaignx_supporter = None
                success = False
                status += "CAMPAIGNX_SUPPORTER_NOT_CREATED: " + str(e) + " "

        results = {
            'success':                      success,
            'status':                       status,
            'campaignx_supporter':          campaignx_supporter,
            'campaignx_supporter_changed':  campaignx_supporter_changed,
            'campaignx_supporter_created':  campaignx_supporter_created,
            'campaignx_supporter_found':    campaignx_supporter_found,
            'campaignx_we_vote_id':         campaignx_we_vote_id,
        }
        return results


class CampaignXOwner(models.Model):
    def __unicode__(self):
        return "CampaignXOwner"

    campaignx_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    voter_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    organization_name = models.CharField(max_length=255, null=False, blank=False)
    feature_this_profile_image = models.BooleanField(default=True)
    visible_to_public = models.BooleanField(default=False)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)


class CampaignXPolitician(models.Model):
    def __unicode__(self):
        return "CampaignXPolitician"

    campaignx_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    politician_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    politician_name = models.CharField(max_length=255, null=False, blank=False)
    state_code = models.CharField(verbose_name="politician home state", max_length=2, null=True)
    we_vote_hosted_profile_image_url_large = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_medium = models.TextField(blank=True, null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)


class CampaignXSEOFriendlyPath(models.Model):
    def __unicode__(self):
        return "CampaignXSEOFriendlyPath"

    campaignx_we_vote_id = models.CharField(max_length=255, null=True)
    campaign_title = models.CharField(max_length=255, null=False)
    base_pathname_string = models.CharField(max_length=255, null=True)
    pathname_modifier = models.CharField(max_length=10, null=True)
    final_pathname_string = models.CharField(max_length=255, null=True, unique=True, db_index=True)


class CampaignXSupporter(models.Model):
    def __unicode__(self):
        return "CampaignXSupporter"

    campaign_supported = models.BooleanField(default=True, db_index=True)
    campaignx_we_vote_id = models.CharField(max_length=255, db_index=True)
    voter_we_vote_id = models.CharField(max_length=255, db_index=True)
    organization_we_vote_id = models.CharField(max_length=255, null=True)
    supporter_name = models.CharField(max_length=255, null=True)
    supporter_endorsement = models.TextField(null=True)
    we_vote_hosted_profile_image_url_tiny = models.TextField(null=True)
    visible_to_public = models.BooleanField(default=False)
    date_last_changed = models.DateTimeField(null=True, auto_now=True, db_index=True)
    date_supported = models.DateTimeField(null=True, auto_now_add=True, db_index=True)
