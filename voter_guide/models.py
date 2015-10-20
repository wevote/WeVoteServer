# voter_guide/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from exception.models import handle_exception, handle_record_not_found_exception, \
    handle_record_found_more_than_one_exception, handle_record_not_saved_exception
from organization.models import Organization
import wevote_functions.admin
from wevote_functions.models import convert_to_int, convert_to_str, positive_value_exists

logger = wevote_functions.admin.get_logger(__name__)


class VoterGuideManager(models.Manager):
    """
    A class for working with the VoterGuide model
    """
    def update_or_create_organization_voter_guide(self, google_civic_election_id, organization_we_vote_id):
        google_civic_election_id = convert_to_int(google_civic_election_id)
        new_voter_guide = VoterGuide()
        voter_guide_owner_type = new_voter_guide.ORGANIZATION
        exception_multiple_object_returned = False
        status = ''
        if not google_civic_election_id or not organization_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_ORGANIZATION_VOTER_GUIDE'
        else:
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'voter_guide_owner_type': voter_guide_owner_type,
                    'organization_we_vote_id': organization_we_vote_id,
                    # The rest of the values
                }
                voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_guide_owner_type__exact=voter_guide_owner_type,
                    organization_we_vote_id__exact=organization_we_vote_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status = 'VOTER_GUIDE_CREATED_FOR_ORGANIZATION'
                else:
                    status = 'VOTER_GUIDE_UPDATED_FOR_ORGANIZATION'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_ORGANIZATION'
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def update_or_create_public_figure_voter_guide(self, google_civic_election_id, public_figure_we_vote_id):
        new_voter_guide = VoterGuide()
        voter_guide_owner_type = new_voter_guide.PUBLIC_FIGURE
        exception_multiple_object_returned = False
        status = ''
        if not google_civic_election_id or not public_figure_we_vote_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_PUBLIC_FIGURE_VOTER_GUIDE'
        else:
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'voter_guide_owner_type': voter_guide_owner_type,
                    'public_figure_we_vote_id': public_figure_we_vote_id,
                    # The rest of the values
                }
                voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_guide_owner_type__exact=voter_guide_owner_type,
                    public_figure_we_vote_id__exact=public_figure_we_vote_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status = 'VOTER_GUIDE_CREATED_FOR_PUBLIC_FIGURE'
                else:
                    status = 'VOTER_GUIDE_UPDATED_FOR_PUBLIC_FIGURE'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_PUBLIC_FIGURE'
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def update_or_create_voter_voter_guide(self, google_civic_election_id, owner_voter_id):
        new_voter_guide = VoterGuide()
        voter_guide_owner_type = new_voter_guide.VOTER
        owner_voter_id = convert_to_int(owner_voter_id)
        exception_multiple_object_returned = False
        status = 'ERROR_VARIABLES_MISSING_FOR_VOTER_VOTER_GUIDE'
        if not google_civic_election_id or not owner_voter_id:
            status = 'ERROR_VARIABLES_MISSING_FOR_VOTER_VOTER_GUIDE'
        else:
            try:
                updated_values = {
                    # Values we search against below
                    'google_civic_election_id': google_civic_election_id,
                    'voter_guide_owner_type': voter_guide_owner_type,
                    'owner_voter_id': owner_voter_id,
                    # The rest of the values
                }
                voter_guide_on_stage, new_voter_guide_created = VoterGuide.objects.update_or_create(
                    google_civic_election_id__exact=google_civic_election_id,
                    voter_guide_owner_type__exact=voter_guide_owner_type,
                    owner_voter_id__exact=owner_voter_id,
                    defaults=updated_values)
                success = True
                if new_voter_guide_created:
                    status = 'VOTER_GUIDE_CREATED_FOR_VOTER'
                else:
                    status = 'VOTER_GUIDE_UPDATED_FOR_VOTER'
            except VoterGuide.MultipleObjectsReturned as e:
                handle_record_found_more_than_one_exception(e, logger=logger)
                success = False
                status = 'MULTIPLE_MATCHING_VOTER_GUIDES_FOUND_FOR_VOTER'
                exception_multiple_object_returned = True

        results = {
            'success':                  success,
            'status':                   status,
            'MultipleObjectsReturned':  exception_multiple_object_returned,
            'voter_guide_saved':        success,
            'new_voter_guide_created':  new_voter_guide_created,
        }
        return results

    def retrieve_voter_guide(self, voter_guide_id=0, google_civic_election_id=0,
                             published_about_we_vote_id=None, published_about_voter_id=0):
        voter_guide_id = convert_to_int(voter_guide_id)
        google_civic_election_id = convert_to_int(google_civic_election_id)
        published_about_we_vote_id = convert_to_str(published_about_we_vote_id)
        published_about_voter_id = convert_to_int(published_about_voter_id)

        error_result = False
        exception_does_not_exist = False
        exception_multiple_object_returned = False
        voter_guide_on_stage = VoterGuide()
        voter_guide_on_stage_id = 0
        status = "ERROR_ENTERING_RETRIEVE_VOTER_GUIDE"
        try:
            if positive_value_exists(voter_guide_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_ID"
                voter_guide_on_stage = VoterGuide.objects.get(id=voter_guide_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_ID"
            elif positive_value_exists(published_about_we_vote_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_WE_VOTE_ID"
                voter_guide_on_stage = VoterGuide.objects.get(google_civic_election_id=google_civic_election_id,
                                                              published_about_we_vote_id=published_about_we_vote_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_WE_VOTE_ID"
            elif positive_value_exists(published_about_voter_id) and positive_value_exists(google_civic_election_id):
                status = "ERROR_RETRIEVING_VOTER_GUIDE_WITH_VOTER_ID"
                voter_guide_on_stage = VoterGuide.objects.get(google_civic_election_id=google_civic_election_id,
                                                              published_about_voter_id=published_about_voter_id)
                voter_guide_on_stage_id = voter_guide_on_stage.id
                status = "VOTER_GUIDE_FOUND_WITH_VOTER_ID"
        except VoterGuide.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger)
            error_result = True
            exception_multiple_object_returned = True
            status = "ERROR_MORE_THAN_ONE_VOTER_GUIDE_FOUND"
            # logger.warn("VoterGuide.MultipleObjectsReturned")
        except VoterGuide.DoesNotExist:
            error_result = True
            exception_does_not_exist = True
            status += ", VOTER_GUIDE_NOT_FOUND"
            # logger.warn("VoterGuide.DoesNotExist")

        voter_guide_on_stage_found = True if voter_guide_on_stage_id > 0 else False
        results = {
            'success':                      True if voter_guide_on_stage_found else False,
            'status':                       status,
            'voter_guide_found':            voter_guide_on_stage_found,
            'voter_guide_id':
                voter_guide_on_stage.id if voter_guide_on_stage.id else voter_guide_on_stage_id,
            'published_about_we_vote_id':
                voter_guide_on_stage.published_about_we_vote_id if voter_guide_on_stage.published_about_we_vote_id
                else published_about_we_vote_id,
            'published_about_voter_id':
                voter_guide_on_stage.published_about_voter_id if voter_guide_on_stage.published_about_voter_id
                else published_about_voter_id,
            'voter_guide':                  voter_guide_on_stage,
            'error_result':                 error_result,
            'DoesNotExist':                 exception_does_not_exist,
            'MultipleObjectsReturned':      exception_multiple_object_returned,
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


# This is the class that we use to rapidly show lists of voter guides, regardless of whether they are from an
# organization, public figure, or voter
class VoterGuide(models.Model):
    # We are relying on built-in Python id field

    # The unique id of the organization or public figure
    organization_we_vote_id = models.CharField(
        verbose_name="organization we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the organization or public figure
    public_figure_we_vote_id = models.CharField(
        verbose_name="public figure we vote id", max_length=255, null=True, blank=True, unique=False)

    # The unique id of the voter that owns this guide. May be null if voter_guide owned by an org instead of a voter.
    owner_voter_id = models.PositiveIntegerField(
        verbose_name="the unique voter id of the voter who this guide is about", default=0, null=True, blank=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=False)

    ORGANIZATION = 'O'
    PUBLIC_FIGURE = 'P'
    VOTER = 'V'
    VOTER_GUIDE_TYPE_CHOICES = (
        (ORGANIZATION, 'Organization'),
        (PUBLIC_FIGURE, 'Public Figure or Politician'),
        (VOTER, 'Voter'),
    )

    voter_guide_owner_type = models.CharField(
        verbose_name="is owner org, public figure, or voter?", max_length=1, choices=VOTER_GUIDE_TYPE_CHOICES,
        default=ORGANIZATION)

    # The date of the last change to this voter_guide
    last_updated = models.DateTimeField(verbose_name='date last changed', null=True, auto_now=True)

    def __unicode__(self):
        return self.last_updated

    class Meta:
        ordering = ('last_updated',)

    objects = VoterGuideManager()

    def organization(self):
        try:
            organization = Organization.objects.get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            handle_record_found_more_than_one_exception(e, logger=logger)
            logger.error("voter_guide.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("voter_guide.organization did not find")
            return
        return organization


class VoterGuideList(models.Model):
    """
    A way to retrieve a list of voter_guides
    """

    def retrieve_voter_guides_for_election(self, google_civic_election_id):
        voter_guide_list = []
        voter_guide_list_found = False
        try:
            status = 'ERROR_VOTER_GUIDE_LIST_START'
            voter_guide_queryset = VoterGuide.objects.order_by('last_updated')
            voter_guide_list = voter_guide_queryset.filter(
                google_civic_election_id=google_civic_election_id)

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                      True if voter_guide_list_found else False,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results

    def retrieve_all_voter_guides(self):
        voter_guide_list = []
        voter_guide_list_found = False
        try:
            status = 'ERROR_VOTER_GUIDE_LIST_START'
            voter_guide_queryset = VoterGuide.objects.order_by('last_updated')
            voter_guide_list = voter_guide_queryset

            if len(voter_guide_list):
                voter_guide_list_found = True
                status = 'VOTER_GUIDE_FOUND'
            else:
                status = 'NO_VOTER_GUIDES_FOUND'
        except Exception as e:
            handle_record_not_found_exception(e, logger=logger)
            status = 'voterGuidesToFollowRetrieve: Unable to retrieve voter guides from db. ' \
                     '{error} [type: {error_type}]'.format(error=e.message, error_type=type(e))

        results = {
            'success':                      True if voter_guide_list_found else False,
            'status':                       status,
            'voter_guide_list_found':       voter_guide_list_found,
            'voter_guide_list':             voter_guide_list,
        }
        return results
