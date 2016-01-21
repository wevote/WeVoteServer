# follow/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_record_found_more_than_one_exception,\
    handle_record_not_found_exception, handle_record_not_saved_exception
from organization.models import OrganizationManager
import wevote_functions.admin
from wevote_functions.models import positive_value_exists
from voter.models import VoterManager


FOLLOWING = 'FOLLOWING'
STOP_FOLLOWING = 'STOP_FOLLOWING'
FOLLOW_IGNORE = 'FOLLOW_IGNORE'
FOLLOWING_CHOICES = (
    (FOLLOWING,         'Following'),
    (STOP_FOLLOWING,    'Not Following'),
    (FOLLOW_IGNORE,     'Ignoring'),
)

logger = wevote_functions.admin.get_logger(__name__)


class FollowOrganization(models.Model):
    # We are relying on built-in Python id field
    # The voter following the organization
    voter_id = models.BigIntegerField(null=True, blank=True)
    # The organization being followed
    organization_id = models.BigIntegerField(null=True, blank=True)

    # Is this person following or ignoring this organization?
    following_status = models.CharField(max_length=15, choices=FOLLOWING_CHOICES, default=FOLLOWING)

    # The date the voter followed or stopped following this organization
    date_last_changed = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    # This is used when we want to export the organizations that a voter is following
    def voter_we_vote_id(self):
        voter_manager = VoterManager()
        return voter_manager.fetch_we_vote_id_from_local_id(self.voter_id)

    # # This is used when we want to export the organizations that a voter is following
    # def organization_we_vote_id(self):
    #     organization_manager = OrganizationManager()
    #     return organization_manager.fetch_we_vote_id_from_local_id(self.organization_id)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    def __unicode__(self):
        return self.organization_id

    def is_following(self):
        if self.following_status == FOLLOWING:
            return True
        return False

    def is_not_following(self):
        if self.following_status == STOP_FOLLOWING:
            return True
        return False

    def is_ignoring(self):
        if self.following_status == FOLLOW_IGNORE:
            return True
        return False


class FollowOrganizationManager(models.Model):

    def __unicode__(self):
        return "FollowOrganizationManager"

    def toggle_on_voter_following_organization(self, voter_id, organization_id):
        following_status = FOLLOWING
        follow_organization_manager = FollowOrganizationManager()
        return follow_organization_manager.toggle_voter_following_organization(
            voter_id, organization_id, following_status)

    def toggle_off_voter_following_organization(self, voter_id, organization_id):
        following_status = STOP_FOLLOWING
        follow_organization_manager = FollowOrganizationManager()
        return follow_organization_manager.toggle_voter_following_organization(
            voter_id, organization_id, following_status)

    def toggle_ignore_voter_following_organization(self, voter_id, organization_id):
        following_status = FOLLOW_IGNORE
        follow_organization_manager = FollowOrganizationManager()
        return follow_organization_manager.toggle_voter_following_organization(
            voter_id, organization_id, following_status)

    def toggle_voter_following_organization(self, voter_id, organization_id, following_status):
        # Does a follow_organization entry exist from this voter already exist?
        follow_organization_manager = FollowOrganizationManager()
        results = follow_organization_manager.retrieve_follow_organization(0, voter_id, organization_id)

        follow_organization_on_stage_found = False
        follow_organization_on_stage_id = 0
        follow_organization_on_stage = FollowOrganization()
        if results['follow_organization_found']:
            follow_organization_on_stage = results['follow_organization']

            # Update this follow_organization entry with new values - we do not delete because we might be able to use
            try:
                follow_organization_on_stage.following_status = following_status
                # We don't need to update here because set set auto_now=True in the field
                # follow_organization_on_stage.date_last_changed =
                follow_organization_on_stage.save()
                follow_organization_on_stage_id = follow_organization_on_stage.id
                follow_organization_on_stage_found = True
                status = 'UPDATE ' + following_status
            except Exception as e:
                status = 'FAILED_TO_UPDATE ' + following_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        elif results['MultipleObjectsReturned']:
            logger.warn("follow_organization: delete all but one and take it over?")
            status = 'TOGGLE_FOLLOWING MultipleObjectsReturned ' + following_status
        elif results['DoesNotExist']:
            try:
                # Create new follow_organization entry
                # First make sure that organization_id is for a valid organization
                organization_manager = OrganizationManager()
                results = organization_manager.retrieve_organization(organization_id)
                if results['organization_found']:
                    organization = results['organization']
                    follow_organization_on_stage = FollowOrganization(
                        voter_id=voter_id,
                        organization_id=organization_id,
                        organization_we_vote_id=organization.we_vote_id,
                        following_status=following_status,
                        # We don't need to update here because set set auto_now=True in the field
                        # date_last_changed =
                    )
                    follow_organization_on_stage.save()
                    follow_organization_on_stage_id = follow_organization_on_stage.id
                    follow_organization_on_stage_found = True
                    status = 'CREATE ' + following_status
                else:
                    status = 'ORGANIZATION_NOT_FOUND_ON_CREATE ' + following_status
            except Exception as e:
                status = 'FAILED_TO_UPDATE ' + following_status
                handle_record_not_saved_exception(e, logger=logger, exception_message_optional=status)
        else:
            status = results['status']

        results = {
            'success':                      True if follow_organization_on_stage_found else False,
            'status':                       status,
            'follow_organization_found':    follow_organization_on_stage_found,
            'follow_organization_id':       follow_organization_on_stage_id,
            'follow_organization':          follow_organization_on_stage,
        }
        return results

    def retrieve_follow_organization(self, follow_organization_id, voter_id, organization_id):
        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        follow_organization_on_stage = FollowOrganization()
        follow_organization_on_stage_id = 0

        try:
            if positive_value_exists(follow_organization_id):
                follow_organization_on_stage = FollowOrganization.objects.get(id=follow_organization_id)
                follow_organization_on_stage_id = organization_id.id
                status = 'FOLLOW_ORGANIZATION_FOUND_WITH_ID'
            elif voter_id > 0 and organization_id > 0:
                follow_organization_on_stage = FollowOrganization.objects.get(
                    voter_id=voter_id, organization_id=organization_id)
                follow_organization_on_stage_id = follow_organization_on_stage.id
                status = 'FOLLOW_ORGANIZATION_FOUND_WITH_VOTER_ID_AND_ORGANIZATION_ID'
        except FollowOrganization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            error_result = True
            exception_multiple_object_returned = True
            status = 'FOLLOW_ORGANIZATION_NOT_FOUND_MultipleObjectsReturned'
        except FollowOrganization.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status = 'FOLLOW_ORGANIZATION_NOT_FOUND_DoesNotExist'

        follow_organization_on_stage_found = True if follow_organization_on_stage_id > 0 else False
        results = {
            'status':                       status,
            'success':                      True if follow_organization_on_stage_found else False,
            'follow_organization_found':    follow_organization_on_stage_found,
            'follow_organization_id':       follow_organization_on_stage_id,
            'follow_organization':          follow_organization_on_stage,
            'is_following':                 follow_organization_on_stage.is_following(),
            'is_not_following':             follow_organization_on_stage.is_not_following(),
            'is_ignoring':                  follow_organization_on_stage.is_ignoring(),
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
        }
        return results


class FollowOrganizationList(models.Model):
    """
    A way to retrieve all of the follow_organization information
    """
    def retrieve_follow_organization_by_voter_id(self, voter_id):
        # Retrieve a list of follow_organization entries for this voter
        follow_organization_list_found = False
        following_status = FOLLOWING
        follow_organization_list = {}
        try:
            follow_organization_list = FollowOrganization.objects.all()
            follow_organization_list = follow_organization_list.filter(voter_id=voter_id)
            follow_organization_list = follow_organization_list.filter(following_status=following_status)
            if len(follow_organization_list):
                follow_organization_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if follow_organization_list_found:
            return follow_organization_list
        else:
            follow_organization_list = {}
            return follow_organization_list

    def retrieve_follow_organization_by_voter_id_simple_id_array(self, voter_id):
        follow_organization_list_manager = FollowOrganizationList()
        follow_organization_list = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id(voter_id)
        follow_organization_list_simple_array = []
        if len(follow_organization_list):
            for follow_organization in follow_organization_list:
                follow_organization_list_simple_array.append(follow_organization.organization_id)
        return follow_organization_list_simple_array

    def retrieve_follow_organization_by_voter_id_simple_we_vote_id_array(self, voter_id):
        follow_organization_list_manager = FollowOrganizationList()
        follow_organization_list = \
            follow_organization_list_manager.retrieve_follow_organization_by_voter_id(voter_id)
        follow_organization_list_simple_array = []
        if len(follow_organization_list):
            for follow_organization in follow_organization_list:
                follow_organization_list_simple_array.append(follow_organization.organization_we_vote_id)
        return follow_organization_list_simple_array

    def retrieve_follow_organization_by_organization_id(self, organization_id):
        # Retrieve a list of follow_organization entries for this organization
        follow_organization_list_found = False
        following_status = FOLLOWING
        follow_organization_list = {}
        try:
            follow_organization_list = FollowOrganization.objects.all()
            follow_organization_list = follow_organization_list.filter(organization_id=organization_id)
            follow_organization_list = follow_organization_list.filter(following_status=following_status)
            if len(follow_organization_list):
                follow_organization_list_found = True
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)

        if follow_organization_list_found:
            return follow_organization_list
        else:
            follow_organization_list = {}
            return follow_organization_list
