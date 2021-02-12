# campaign/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception
import wevote_functions.admin
from wevote_functions.functions import positive_value_exists
from wevote_settings.models import fetch_next_we_vote_id_campaignx_integer, fetch_site_unique_id_prefix

logger = wevote_functions.admin.get_logger(__name__)


class CampaignX(models.Model):
    # We call this "CampaignX" since we have some other data objects in We Vote already with "Campaign" in the name
    # These are campaigns anyone can start to gather support or opposition for one or more items on the ballot.
    # The we_vote_id identifier is unique across all We Vote sites, and allows us to share our data
    # It starts with "wv" then we add on a database specific identifier like "3v" (WeVoteSetting.site_unique_id_prefix)
    # then the string "camp", and then a sequential integer like "123".
    # We keep the last value in WeVoteSetting.we_vote_id_last_campaign_integer
    we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True,
        blank=True, unique=True, db_index=True)
    campaign_title = models.CharField(verbose_name="title of campaign", max_length=255, null=False, blank=False)
    # Has not been released for view
    in_draft_mode = models.BooleanField(default=True, db_index=True)
    started_by_voter_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)

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


class CampaignXManager(models.Manager):

    def __unicode__(self):
        return "CampaignXManager"

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

    def retrieve_campaignx_as_owner(
            self, campaignx_we_vote_id='', voter_we_vote_id='', read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        campaignx = None
        campaignx_manager = CampaignXManager()
        campaignx_owner_list = []
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
                    'we_vote_hosted_profile_image_url_tiny':    campaignx_owner_we_vote_hosted_profile_image_url_tiny,
                    'visible_to_public':                        campaignx_owner.visible_to_public,
                }
                campaignx_owner_list.append(campaign_owner_dict)

        results = {
            'status':                   status,
            'success':                  success,
            'campaignx':                campaignx,
            'campaignx_found':          campaignx_found,
            'campaignx_we_vote_id':     campaignx_we_vote_id,
            'campaignx_owner_list':     campaignx_owner_list,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
        }
        return results

    def retrieve_campaignx(self, campaignx_we_vote_id='', read_only=False):
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        campaignx = None
        campaignx_found = False
        campaignx_manager = CampaignXManager()
        campaignx_owner_list = []
        status = ''
        viewer_is_owner = False

        try:
            if positive_value_exists(campaignx_we_vote_id):
                if positive_value_exists(read_only):
                    campaignx = CampaignX.objects.using('readonly').get(we_vote_id=campaignx_we_vote_id)
                else:
                    campaignx = CampaignX.objects.get(we_vote_id=campaignx_we_vote_id)
                campaignx_found = True
                status += 'CAMPAIGNX_FOUND_WITH_WE_VOTE_ID '
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
                    'we_vote_hosted_profile_image_url_tiny':    campaignx_owner.we_vote_hosted_profile_image_url_tiny,
                    'visible_to_public':                        campaignx_owner.visible_to_public,
                }
                campaignx_owner_list.append(campaign_owner_dict)

        results = {
            'status':                   status,
            'success':                  success,
            'campaignx':                campaignx,
            'campaignx_found':          campaignx_found,
            'campaignx_we_vote_id':     campaignx_we_vote_id,
            'campaignx_owner_list':     campaignx_owner_list,
            'DoesNotExist':             exception_does_not_exist,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
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

    def retrieve_campaignx_owner_list(self, campaignx_we_vote_id='', viewer_is_owner=False):
        campaignx_owner_list_found = False
        campaignx_owner_list = []
        try:
            campaignx_owner_query = CampaignXOwner.objects.all()
            if not positive_value_exists(viewer_is_owner):
                # If not already an owner, limit to owners who are visible to public
                campaignx_owner_query = campaignx_owner_query.filter(visible_to_public=True)
            campaignx_owner_query = campaignx_owner_query.filter(campaignx_we_vote_id=campaignx_we_vote_id)
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
                if 'campaign_title_changed' in update_values \
                        and positive_value_exists(update_values['campaign_title_changed']):
                    campaignx.campaign_title = update_values['campaign_title']
                    campaignx_changed = True
                if campaignx_changed:
                    campaignx.save()
                    campaignx_created = True
                    status += "CAMPAIGNX_UPDATED "
                else:
                    status += "CAMPAIGNX_NOT_UPDATED-NO_CHANGES_FOUND "
                success = True
            except Exception as e:
                campaignx = CampaignX()
                success = False
                status += "CAMPAIGNX_NOT_UPDATED: " + str(e) + " "
        else:
            try:
                campaignx = CampaignX.objects.create(
                    campaign_title=update_values['campaign_title'],
                    in_draft_mode=True,
                    started_by_voter_we_vote_id=voter_we_vote_id,
                )
                campaignx_created = True
                success = True
                status += "CAMPAIGNX_CREATED "
            except Exception as e:
                campaignx_created = False
                campaignx = CampaignX()
                success = False
                status += "CAMPAIGNX_NOT_CREATED " + str(e) + " "

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


class CampaignXOwner(models.Model):
    campaignx_id = models.PositiveIntegerField(null=True, blank=True)
    campaignx_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    voter_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False, db_index=True)
    organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    organization_name = models.CharField(max_length=255, null=False, blank=False)
    we_vote_hosted_profile_image_url_tiny = models.TextField(blank=True, null=True)
    visible_to_public = models.BooleanField(default=False)
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True, db_index=True)
